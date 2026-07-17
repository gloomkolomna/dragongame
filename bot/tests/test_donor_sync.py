import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../api"))

import config
from models import User, DonorCache
from bot.services.donor_sync import _sync_all


class FakeResponse:

    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def _make_user(db, vk_id):
    db.add(User(vk_id=vk_id, state="idle"))
    db.commit()


def test_sync_creates_cache_row(db, monkeypatch):
    config.DONUT_API_URL = "http://donut"
    config.DONUT_API_KEY = "key"
    _make_user(db, 111)

    import httpx
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse(200, {"vk_id": 111, "is_don": True, "don_since": "2026-01-01"}))

    _sync_all(db)

    donor = db.query(DonorCache).filter(DonorCache.vk_id == 111).first()
    assert donor is not None
    assert donor.is_don is True
    assert donor.don_since == "2026-01-01"


def test_sync_updates_existing(db, monkeypatch):
    config.DONUT_API_URL = "http://donut"
    config.DONUT_API_KEY = "key"
    _make_user(db, 111)
    db.add(DonorCache(vk_id=111, is_don=False, updated_at="old", last_synced_at="old"))
    db.commit()

    import httpx
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse(200, {"vk_id": 111, "is_don": True, "don_since": None}))

    _sync_all(db)

    donor = db.query(DonorCache).filter(DonorCache.vk_id == 111).first()
    assert donor.is_don is True
    assert donor.updated_at != "old"


def test_sync_sets_is_don_false(db, monkeypatch):
    config.DONUT_API_URL = "http://donut"
    config.DONUT_API_KEY = "key"
    _make_user(db, 111)

    import httpx
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse(200, {"vk_id": 111, "is_don": False, "don_since": None}))

    _sync_all(db)

    donor = db.query(DonorCache).filter(DonorCache.vk_id == 111).first()
    assert donor.is_don is False


def test_sync_handles_http_error(db, monkeypatch):
    config.DONUT_API_URL = "http://donut"
    config.DONUT_API_KEY = "key"
    _make_user(db, 111)

    import httpx

    def _boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "get", _boom)

    _sync_all(db)

    assert db.query(DonorCache).count() == 0


def test_sync_handles_user_not_found(db, monkeypatch):
    config.DONUT_API_URL = "http://donut"
    config.DONUT_API_KEY = "key"
    _make_user(db, 111)

    import httpx
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse(404, {}))

    _sync_all(db)

    assert db.query(DonorCache).count() == 0


def test_sync_no_users(db, monkeypatch):
    config.DONUT_API_URL = "http://donut"
    config.DONUT_API_KEY = "key"

    import httpx
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse(200, {"is_don": True}))

    _sync_all(db)

    assert db.query(DonorCache).count() == 0


def test_sync_interval_default_is_8_hours():
    import inspect
    from bot.services.donor_sync import run_donor_sync

    sig = inspect.signature(run_donor_sync)
    assert sig.parameters["interval_hours"].default == 8
    assert config.DONOR_SYNC_INTERVAL_HOURS == 8


def test_run_syncs_immediately_before_sleep(db, monkeypatch):
    from bot.services import donor_sync

    calls = []

    monkeypatch.setattr(donor_sync, "_sync_all", lambda *a, **k: calls.append("sync"))

    def fake_sleep(seconds):
        calls.append(("sleep", seconds))
        raise SystemExit

    monkeypatch.setattr(donor_sync.time, "sleep", fake_sleep)

    try:
        donor_sync.run_donor_sync(lambda: db, interval_hours=8)
    except SystemExit:
        pass

    assert calls == ["sync", ("sleep", 8 * 3600)]


def test_new_user_gets_donor_status(db, monkeypatch):
    config.DONUT_API_URL = "http://donut"
    config.DONUT_API_KEY = "key"

    import httpx
    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse(200, {"vk_id": 555, "is_don": True, "don_since": "2026-01-01"}))

    from bot.services.user_service import get_or_create_user
    user = get_or_create_user(db, 555)

    assert user.vk_id == 555
    donor = db.query(DonorCache).filter(DonorCache.vk_id == 555).first()
    assert donor is not None
    assert donor.is_don is True


def test_existing_user_no_extra_sync(db, monkeypatch):
    config.DONUT_API_URL = "http://donut"
    config.DONUT_API_KEY = "key"
    _make_user(db, 556)

    calls = []
    from bot.services import donor_sync
    monkeypatch.setattr(donor_sync, "sync_user", lambda *a, **k: calls.append("sync"))

    from bot.services.user_service import get_or_create_user
    get_or_create_user(db, 556)

    assert calls == []


def test_new_user_created_when_sync_fails(db, monkeypatch):
    config.DONUT_API_URL = "http://donut"
    config.DONUT_API_KEY = "key"

    import httpx

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(httpx, "get", boom)

    from bot.services.user_service import get_or_create_user
    user = get_or_create_user(db, 557)

    assert user.vk_id == 557
    assert db.query(DonorCache).count() == 0
