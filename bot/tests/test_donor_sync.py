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
