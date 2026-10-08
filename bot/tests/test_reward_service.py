import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../api"))

from datetime import datetime, timedelta

import logging

import config
from models import User, Dragon, DonorCache, DonorEventLog, RewardConfig, UserRewardPin, DragonReservation
from bot.services.reward_service import _process_rewards


class FakeMessages:

    def __init__(self):
        self.sent = []

    def send(self, **kwargs):
        self.sent.append(kwargs)


class FakeVK:

    def __init__(self):
        self.messages = FakeMessages()


def _setup(db, registered_at, events=None):
    config.DONUT_API_URL = ""
    config.DONUT_API_KEY = ""
    config.VK_GROUP_TOKEN = ""
    db.add(RewardConfig(id=1, user_type="donor", eggs_per_period=1, period_days=30, is_active=True, rarity_filter=""))
    db.add(Dragon(name="Дракон", egg_type="белое", rarity=1, steps_count=3, pin_code="11111", is_active=True, is_epic=False))
    db.add(User(vk_id=111, state="idle", registered_at=registered_at))
    db.add(DonorCache(vk_id=111, is_don=True, don_since=registered_at, first_don_since=registered_at))
    for event_type, created_at in (events or []):
        db.add(DonorEventLog(vk_id=111, event_type=event_type, created_at=created_at))
    db.commit()


def _run(db):
    vk = FakeVK()
    _process_rewards(db, vk, logging.getLogger("test_reward"))
    return vk


def test_donor_gets_pin_after_30_days_from_create(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=45)).isoformat(),
        events=[("donut_subscription_create", (now - timedelta(days=40)).isoformat())],
    )

    vk = _run(db)

    pin = db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).first()
    assert pin is not None
    assert pin.config_id == 1
    assert pin.notified is True
    assert len(vk.messages.sent) == 1

    reservation = db.query(DragonReservation).filter(DragonReservation.vk_user_id == 111).first()
    assert reservation is not None


def test_became_donor_before_registration_anchor_from_registration(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=35)).isoformat(),
        events=[("donut_subscription_create", (now - timedelta(days=50)).isoformat())],
    )

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 1
    assert len(vk.messages.sent) == 1


def test_became_donor_before_registration_within_30_days_skipped(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=10)).isoformat(),
        events=[("donut_subscription_create", (now - timedelta(days=50)).isoformat())],
    )

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 0
    assert vk.messages.sent == []


def test_prolonged_only_anchor_from_registration(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=32)).isoformat(),
        events=[("donut_subscription_prolonged", (now - timedelta(days=13)).isoformat())],
    )

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 1
    assert len(vk.messages.sent) == 1


def test_prolonged_does_not_shift_anchor(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=10)).isoformat(),
        events=[("donut_subscription_prolonged", (now - timedelta(days=1)).isoformat())],
    )

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 0
    assert vk.messages.sent == []


def test_no_events_anchor_from_registration(db):
    now = datetime.now()
    _setup(db, registered_at=(now - timedelta(days=45)).isoformat())

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 1
    assert len(vk.messages.sent) == 1


def test_no_events_no_registration_skipped(db):
    _setup(db, registered_at=None)

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 0
    assert vk.messages.sent == []


def test_cancelled_after_create_no_egg(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=45)).isoformat(),
        events=[
            ("donut_subscription_create", (now - timedelta(days=40)).isoformat()),
            ("donut_subscription_cancelled", (now - timedelta(days=5)).isoformat()),
        ],
    )

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 0
    assert vk.messages.sent == []


def test_prolonged_after_cancelled_without_create_gets_egg(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=45)).isoformat(),
        events=[
            ("donut_subscription_cancelled", (now - timedelta(days=28)).isoformat()),
            ("donut_subscription_prolonged", (now - timedelta(days=24)).isoformat()),
        ],
    )

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 1
    assert len(vk.messages.sent) == 1


def test_cancelled_last_event_without_create_no_egg(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=45)).isoformat(),
        events=[
            ("donut_subscription_prolonged", (now - timedelta(days=40)).isoformat()),
            ("donut_subscription_cancelled", (now - timedelta(days=5)).isoformat()),
        ],
    )

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 0
    assert vk.messages.sent == []


def test_backfill_add_after_cancelled_without_create_gets_egg(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=45)).isoformat(),
        events=[
            ("donut_subscription_cancelled", (now - timedelta(days=28)).isoformat()),
            ("backfill_add", (now - timedelta(days=24)).isoformat()),
        ],
    )

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 1
    assert len(vk.messages.sent) == 1


def test_prolonged_after_cancelled_with_create_gets_egg(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=45)).isoformat(),
        events=[
            ("donut_subscription_create", (now - timedelta(days=40)).isoformat()),
            ("donut_subscription_cancelled", (now - timedelta(days=10)).isoformat()),
            ("donut_subscription_prolonged", (now - timedelta(days=5)).isoformat()),
        ],
    )

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 1
    assert len(vk.messages.sent) == 1


def test_create_after_cancelled_dates_from_new_create(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=70)).isoformat(),
        events=[
            ("donut_subscription_cancelled", (now - timedelta(days=60)).isoformat()),
            ("donut_subscription_create", (now - timedelta(days=35)).isoformat()),
        ],
    )

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 1
    assert len(vk.messages.sent) == 1


def test_donor_within_30_days_skipped(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=12)).isoformat(),
        events=[("donut_subscription_create", (now - timedelta(days=10)).isoformat())],
    )

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 0
    assert vk.messages.sent == []


def test_recent_pin_blocks_new_egg(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=45)).isoformat(),
        events=[("donut_subscription_create", (now - timedelta(days=40)).isoformat())],
    )
    db.add(UserRewardPin(
        user_id=111,
        dragon_id=None,
        pin_code="00000",
        config_id=1,
        issued_at=(now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S"),
        activated=False,
        notified=True,
    ))
    db.commit()

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 1
    assert vk.messages.sent == []


def test_old_pin_allows_new_egg(db):
    now = datetime.now()
    _setup(
        db,
        registered_at=(now - timedelta(days=85)).isoformat(),
        events=[("donut_subscription_create", (now - timedelta(days=80)).isoformat())],
    )
    db.add(UserRewardPin(
        user_id=111,
        dragon_id=None,
        pin_code="00000",
        config_id=1,
        issued_at=(now - timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%S"),
        activated=False,
        notified=True,
    ))
    db.commit()

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 2
    assert len(vk.messages.sent) == 1
