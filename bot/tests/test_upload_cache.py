import os
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _cache_state(monkeypatch, tmp_path):
    import config
    from services import vk_upload
    from bot.services import upload_cache
    monkeypatch.setattr(config, "UPLOAD_CACHE_ENABLED", True)
    monkeypatch.setattr(vk_upload, "DISK_CACHE_PATH", str(tmp_path / "upload_cache.json"))
    upload_cache.clear()
    yield
    upload_cache.clear()


class _FakeUploadResponse:
    status_code = 200
    text = '{"photo":"x","server":1,"hash":"h"}'

    def raise_for_status(self):
        pass

    def json(self):
        return {"photo": "x", "server": 1, "hash": "h"}


def _make_vk(owner_id=-5, photo_id=7):
    vk = MagicMock()
    vk.photos.getMessagesUploadServer.return_value = {"upload_url": "http://upload"}
    vk.photos.saveMessagesPhoto.return_value = [{"owner_id": owner_id, "id": photo_id}]
    return vk


def test_get_empty_for_missing_file(tmp_path):
    from bot.services import upload_cache
    assert upload_cache.get(str(tmp_path / "no.jpg")) == ""


def test_store_and_get_roundtrip(tmp_path):
    from bot.services import upload_cache
    f = tmp_path / "egg.jpg"
    f.write_bytes(b"data")
    upload_cache.store(str(f), "photo-1_2")
    assert upload_cache.get(str(f)) == "photo-1_2"


def test_get_normalizes_path(tmp_path):
    from bot.services import upload_cache
    f = tmp_path / "sub" / "egg.jpg"
    f.parent.mkdir()
    f.write_bytes(b"data")
    upload_cache.store(str(f), "photo-1_2")
    dotted = os.path.join(str(tmp_path), "sub", "..", "sub", "egg.jpg")
    assert upload_cache.get(dotted) == "photo-1_2"


def test_invalidated_when_mtime_changes(tmp_path):
    from bot.services import upload_cache
    f = tmp_path / "egg.jpg"
    f.write_bytes(b"data")
    upload_cache.store(str(f), "photo-1_2")
    os.utime(f, (12345, 12345))
    assert upload_cache.get(str(f)) == ""


def test_invalidated_when_size_changes(tmp_path):
    from bot.services import upload_cache
    f = tmp_path / "egg.jpg"
    f.write_bytes(b"data")
    upload_cache.store(str(f), "photo-1_2")
    f.write_bytes(b"data more data")
    assert upload_cache.get(str(f)) == ""


def test_invalidate_by_attachment(tmp_path):
    from bot.services import upload_cache
    f = tmp_path / "egg.jpg"
    f.write_bytes(b"data")
    upload_cache.store(str(f), "photo-1_2")
    assert upload_cache.invalidate_by_attachment("photo-1_2") == os.path.normpath(str(f))
    assert upload_cache.get(str(f)) == ""
    assert upload_cache.invalidate_by_attachment("photo-1_2") is None


def test_invalidate_by_attachment_unknown_returns_none():
    from bot.services import upload_cache
    assert upload_cache.invalidate_by_attachment("photo-9_9") is None


def test_disabled_flag_disables_cache(tmp_path, monkeypatch):
    import config
    from bot.services import upload_cache
    monkeypatch.setattr(config, "UPLOAD_CACHE_ENABLED", False)
    f = tmp_path / "egg.jpg"
    f.write_bytes(b"data")
    upload_cache.store(str(f), "photo-1_2")
    assert upload_cache.get(str(f)) == ""
    assert upload_cache.invalidate_by_attachment("photo-1_2") is None


def test_scheduler_upload_uses_cache(tmp_path, monkeypatch):
    from bot import scheduler
    from services import vk_upload
    monkeypatch.setattr(vk_upload, "_http_post", lambda url, fp, timeout: _FakeUploadResponse())
    f = tmp_path / "d.jpg"
    f.write_bytes(b"x" * 100)
    vk = _make_vk()
    att1 = scheduler._upload_image(vk, str(f), peer_id=1)
    att2 = scheduler._upload_image(vk, str(f), peer_id=2)
    assert att1 == "photo-5_7"
    assert att2 == "photo-5_7"
    assert vk.photos.getMessagesUploadServer.call_count == 1


def test_scheduler_upload_ignores_cache_when_disabled(tmp_path, monkeypatch):
    import config
    from bot import scheduler
    from services import vk_upload
    monkeypatch.setattr(config, "UPLOAD_CACHE_ENABLED", False)
    monkeypatch.setattr(vk_upload, "_http_post", lambda url, fp, timeout: _FakeUploadResponse())
    f = tmp_path / "d.jpg"
    f.write_bytes(b"x" * 100)
    vk = _make_vk()
    att1 = scheduler._upload_image(vk, str(f), peer_id=1)
    att2 = scheduler._upload_image(vk, str(f), peer_id=1)
    assert att1 == "photo-5_7"
    assert att2 == "photo-5_7"
    assert vk.photos.getMessagesUploadServer.call_count == 2


def test_scheduler_failed_upload_not_cached(tmp_path, monkeypatch):
    from bot import scheduler
    from bot.services import upload_cache
    from services import vk_upload

    def _fail(url, fp, timeout):
        raise RuntimeError("boom")

    monkeypatch.setattr(vk_upload, "_http_post", _fail)
    f = tmp_path / "d.jpg"
    f.write_bytes(b"x" * 100)
    vk = _make_vk()
    assert scheduler._upload_image(vk, str(f), peer_id=1) == ""
    assert upload_cache.get(str(f)) == ""


def test_scheduler_reupload_after_invalidation(tmp_path, monkeypatch):
    from bot import scheduler
    from bot.services import upload_cache
    from services import vk_upload
    monkeypatch.setattr(vk_upload, "_http_post", lambda url, fp, timeout: _FakeUploadResponse())
    f = tmp_path / "d.jpg"
    f.write_bytes(b"x" * 100)
    vk = _make_vk()
    att = scheduler._upload_image(vk, str(f), peer_id=1)
    assert upload_cache.invalidate_by_attachment(att) is not None
    att2 = scheduler._upload_image(vk, str(f), peer_id=1)
    assert att2 == "photo-5_7"
    assert vk.photos.getMessagesUploadServer.call_count == 2
