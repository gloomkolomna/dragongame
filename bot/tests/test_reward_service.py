import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../api"))

from datetime import datetime, timedelta

import logging

import config
from models import User, Dragon, DonorCache, RewardConfig, UserRewardPin, DragonReservation
from bot.services.reward_service import _process_rewards


class FakeMessages:

    def __init__(self):
        self.sent = []

    def send(self, **kwargs):
        self.sent.append(kwargs)


class FakeVK:

    def __init__(self):
        self.messages = FakeMessages()


def _setup(db, first_don_since, registered_at, don_since=None):
    config.DONUT_API_URL = ""
    config.DONUT_API_KEY = ""
    config.VK_GROUP_TOKEN = ""
    db.add(RewardConfig(id=1, user_type="donor", eggs_per_period=1, period_days=30, is_active=True, rarity_filter=""))
    db.add(Dragon(name="Дракон", egg_type="белое", rarity=1, steps_count=3, pin_code="11111", is_active=True, is_epic=False))
    db.add(User(vk_id=111, state="idle", registered_at=registered_at))
    db.add(DonorCache(vk_id=111, is_don=True, don_since=don_since or first_don_since, first_don_since=first_don_since))
    db.commit()


def _run(db):
    vk = FakeVK()
    _process_rewards(db, vk, logging.getLogger("test_reward"))
    return vk


def test_donor_gets_pin_after_30_days_from_first_don(db):
    now = datetime.now()
    _setup(db, first_don_since=(now - timedelta(days=40)).isoformat(), registered_at=(now - timedelta(days=45)).isoformat())

    vk = _run(db)

    pin = db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).first()
    assert pin is not None
    assert pin.config_id == 1
    assert pin.notified is True
    assert len(vk.messages.sent) == 1

    reservation = db.query(DragonReservation).filter(DragonReservation.vk_user_id == 111).first()
    assert reservation is not None


def test_prolonged_don_since_does_not_block(db):
    now = datetime.now()
    _setup(
        db,
        first_don_since=(now - timedelta(days=40)).isoformat(),
        registered_at=(now - timedelta(days=45)).isoformat(),
        don_since=(now - timedelta(days=1)).isoformat(),
    )

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 1
    assert len(vk.messages.sent) == 1


def test_anchor_uses_registration_if_later(db):
    now = datetime.now()
    _setup(db, first_don_since=(now - timedelta(days=40)).isoformat(), registered_at=(now - timedelta(days=10)).isoformat())

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 0
    assert vk.messages.sent == []


def test_donor_within_30_days_skipped(db):
    now = datetime.now()
    _setup(db, first_don_since=(now - timedelta(days=10)).isoformat(), registered_at=(now - timedelta(days=12)).isoformat())

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 0
    assert vk.messages.sent == []


def test_recent_pin_blocks_new_egg(db):
    now = datetime.now()
    _setup(db, first_don_since=(now - timedelta(days=40)).isoformat(), registered_at=(now - timedelta(days=45)).isoformat())
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
    _setup(db, first_don_since=(now - timedelta(days=80)).isoformat(), registered_at=(now - timedelta(days=85)).isoformat())
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


def test_no_first_don_since_skipped(db):
    now = datetime.now()
    _setup(db, first_don_since=None, registered_at=(now - timedelta(days=45)).isoformat())
    donor = db.query(DonorCache).filter(DonorCache.vk_id == 111).first()
    donor.first_don_since = None
    db.commit()

    vk = _run(db)

    assert db.query(UserRewardPin).filter(UserRewardPin.user_id == 111).count() == 0
    assert vk.messages.sent == []
