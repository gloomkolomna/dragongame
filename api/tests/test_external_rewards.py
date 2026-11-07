import pytest

from models import Dragon, DragonReservation, User, UserRewardPin


@pytest.fixture
def integration_key(monkeypatch):
    import config
    monkeypatch.setattr(config, "HOLIDAYS_INTEGRATION_KEY", "test-integration-key")
    return {"X-Integration-Key": "test-integration-key"}


def _dragon(db, pin="EGG01", name="Огненный"):
    dragon = Dragon(name=name, rarity=1, steps_count=1, pin_code=pin, is_active=True, is_epic=False)
    db.add(dragon)
    db.commit()
    db.refresh(dragon)
    return dragon


def _grant(client, vk_id=100, external_id="holidays:purchase:1", headers=None):
    return client.post(
        "/api/internal/rewards/dragon-egg",
        json={"vk_id": vk_id, "external_reward_id": external_id},
        headers=headers or {},
    )


def test_internal_reward_requires_key(client, db, integration_key):
    _dragon(db)
    response = _grant(client)
    assert response.status_code == 403


def test_grant_existing_user_creates_reservation_and_pin(client, db, integration_key):
    dragon = _dragon(db)
    db.add(User(vk_id=100))
    db.commit()

    response = _grant(client, headers=integration_key)

    assert response.status_code == 200, response.text
    assert response.json()["user_registered"] is True
    assert response.json()["dragon_id"] == dragon.id
    reservation = db.query(DragonReservation).filter_by(external_reward_id="holidays:purchase:1").one()
    assert reservation.vk_user_id == 100
    assert reservation.source == "holidays"
    assert reservation.revoked_at is None
    pin = db.query(UserRewardPin).filter_by(external_reward_id="holidays:purchase:1").one()
    assert pin.dragon_id == dragon.id
    assert pin.activated is False


def test_grant_is_idempotent(client, db, integration_key):
    _dragon(db)
    first = _grant(client, headers=integration_key)
    second = _grant(client, headers=integration_key)

    assert first.status_code == second.status_code == 200
    assert first.json()["reservation_id"] == second.json()["reservation_id"]
    assert db.query(DragonReservation).count() == 1


def test_future_user_gets_pin_on_bot_and_miniapp_registration(client, db, integration_key):
    _dragon(db, "EGG01", "Первый")
    _dragon(db, "EGG02", "Второй")
    assert _grant(client, vk_id=201, external_id="holidays:purchase:201", headers=integration_key).status_code == 200
    assert _grant(client, vk_id=202, external_id="holidays:purchase:202", headers=integration_key).status_code == 200
    assert db.query(UserRewardPin).count() == 0

    from bot.services.user_service import get_or_create_user as bot_get_or_create
    from auth import get_or_create_user as api_get_or_create
    bot_get_or_create(db, 201)
    api_get_or_create(db, 202, "", "")

    assert db.query(UserRewardPin).count() == 2
    assert {pin.user_id for pin in db.query(UserRewardPin).all()} == {201, 202}


def test_grant_without_available_dragons_does_not_create_reservation(client, db, integration_key):
    response = _grant(client, headers=integration_key)
    assert response.status_code == 409
    assert db.query(DragonReservation).count() == 0


def test_revoke_pending_reward_and_reject_activated(client, db, integration_key):
    _dragon(db)
    reservation_id = _grant(client, headers=integration_key).json()["reservation_id"]
    db.add(User(vk_id=100))
    db.commit()
    from services.external_rewards import ensure_external_reward_pins
    ensure_external_reward_pins(db, 100)

    revoked = client.post(
        "/api/internal/rewards/dragon-egg/revoke",
        json={"external_reward_id": "holidays:purchase:1"},
        headers=integration_key,
    )
    assert revoked.status_code == 200
    reservation = db.get(DragonReservation, reservation_id)
    assert reservation.revoked_at is not None
    assert db.query(UserRewardPin).count() == 0

    repeated = client.post(
        "/api/internal/rewards/dragon-egg/revoke",
        json={"external_reward_id": "holidays:purchase:1"},
        headers=integration_key,
    )
    assert repeated.status_code == 200

    reservation.revoked_at = None
    reservation.is_activated = True
    db.commit()
    conflict = client.post(
        "/api/internal/rewards/dragon-egg/revoke",
        json={"external_reward_id": "holidays:purchase:1"},
        headers=integration_key,
    )
    assert conflict.status_code == 409
