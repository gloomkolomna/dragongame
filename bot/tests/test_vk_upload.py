import os
import threading
from unittest.mock import MagicMock

import pytest
import requests


@pytest.fixture(autouse=True)
def _state(monkeypatch, tmp_path):
    import config
    from services import vk_upload
    monkeypatch.setattr(config, "UPLOAD_CACHE_ENABLED", True)
    monkeypatch.setattr(vk_upload, "DISK_CACHE_PATH", str(tmp_path / "upload_cache.json"))
    monkeypatch.setattr(vk_upload, "INTERACTIVE_DELAYS", [0.0, 0.0, 0.0])
    monkeypatch.setattr(vk_upload, "BACKGROUND_DELAYS", [0.0, 0.0, 0.0, 0.0])
    vk_upload.clear()
    yield
    vk_upload.clear()


class _FakeUploadResponse:
    status_code = 200
    text = '{"photo":"x","server":1,"hash":"h"}'

    def raise_for_status(self):
        pass

    def json(self):
        return {"photo": "x", "server": 1, "hash": "h"}


class _EmptyPhotoResponse:
    status_code = 200
    text = '{"photo":"","server":1,"hash":"h"}'

    def raise_for_status(self):
        pass

    def json(self):
        return {"photo": "", "server": 1, "hash": "h"}


def _make_vk(owner_id=-5, photo_id=7):
    vk = MagicMock()
    vk.photos.getMessagesUploadServer.return_value = {"upload_url": "http://upload"}
    vk.photos.saveMessagesPhoto.return_value = [{"owner_id": owner_id, "id": photo_id}]
    return vk


def _http_error(status, body="gateway error"):
    resp = MagicMock()
    resp.status_code = status
    resp.text = body
    return requests.exceptions.HTTPError(f"{status} Error", response=resp)


def _img(tmp_path, name, magic):
    f = tmp_path / name
    f.write_bytes(magic + b"x" * 10)
    return str(f)


def test_success_after_retryable_502(tmp_path, monkeypatch):
    from services import vk_upload
    calls = {"n": 0}

    def _post(url, fp, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _http_error(502)
        return _FakeUploadResponse()

    monkeypatch.setattr(vk_upload, "_http_post", _post)
    f = _img(tmp_path, "d.jpg", b"\xff\xd8\xff")
    vk = _make_vk()
    assert vk_upload.upload_message_photo(vk, f, peer_id=1) == "photo-5_7"
    assert calls["n"] == 2
    assert vk_upload.get(f) == "photo-5_7"


def test_success_after_retryable_504(tmp_path, monkeypatch):
    from services import vk_upload
    calls = {"n": 0}

    def _post(url, fp, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            raise _http_error(504, "gateway timeout")
        return _FakeUploadResponse()

    monkeypatch.setattr(vk_upload, "_http_post", _post)
    f = _img(tmp_path, "d.jpg", b"\xff\xd8\xff")
    vk = _make_vk()
    assert vk_upload.upload_message_photo(vk, f, peer_id=1) == "photo-5_7"
    assert calls["n"] == 3


def test_no_retry_on_400(tmp_path, monkeypatch):
    from services import vk_upload
    calls = {"n": 0}

    def _post(url, fp, timeout):
        calls["n"] += 1
        raise _http_error(400)

    monkeypatch.setattr(vk_upload, "_http_post", _post)
    f = _img(tmp_path, "d.jpg", b"\xff\xd8\xff")
    vk = _make_vk()
    assert vk_upload.upload_message_photo(vk, f, peer_id=1) == ""
    assert calls["n"] == 1


def test_negative_cache_blocks_repeat_attempts(tmp_path, monkeypatch):
    from services import vk_upload
    calls = {"n": 0}

    def _post(url, fp, timeout):
        calls["n"] += 1
        raise _http_error(502)

    monkeypatch.setattr(vk_upload, "_http_post", _post)
    f = _img(tmp_path, "d.jpg", b"\xff\xd8\xff")
    vk = _make_vk()
    assert vk_upload.upload_message_photo(vk, f, peer_id=1) == ""
    first = calls["n"]
    assert first == len(vk_upload.INTERACTIVE_DELAYS) + 1
    assert vk_upload.upload_message_photo(vk, f, peer_id=2) == ""
    assert calls["n"] == first


def test_negative_cache_expires(tmp_path, monkeypatch):
    from services import vk_upload
    calls = {"n": 0}

    def _post(url, fp, timeout):
        calls["n"] += 1
        raise _http_error(502)

    monkeypatch.setattr(vk_upload, "_http_post", _post)
    f = _img(tmp_path, "d.jpg", b"\xff\xd8\xff")
    vk = _make_vk()
    vk_upload.upload_message_photo(vk, f, peer_id=1)
    monkeypatch.setattr(vk_upload, "NEGATIVE_TTL_SECONDS", 0)
    vk_upload._negative[f] = 0.0
    vk_upload.upload_message_photo(vk, f, peer_id=1)
    assert calls["n"] > 1


def test_empty_photo_response_not_retried(tmp_path, monkeypatch):
    from services import vk_upload
    calls = {"n": 0}

    def _post(url, fp, timeout):
        calls["n"] += 1
        return _EmptyPhotoResponse()

    monkeypatch.setattr(vk_upload, "_http_post", _post)
    f = _img(tmp_path, "d.jpg", b"\xff\xd8\xff")
    vk = _make_vk()
    assert vk_upload.upload_message_photo(vk, f, peer_id=1) == ""
    assert calls["n"] == 1


def test_missing_file_returns_empty(tmp_path):
    from services import vk_upload
    assert vk_upload.upload_message_photo(_make_vk(), str(tmp_path / "no.jpg")) == ""


def test_sniff_image_jpeg_png_unknown(tmp_path):
    from services import vk_upload
    jpg = _img(tmp_path, "photo.txt", b"\xff\xd8\xff")
    assert vk_upload.sniff_image(jpg) == ("image.jpg", "image/jpeg")
    png = _img(tmp_path, "photo.exe", b"\x89PNG\r\n\x1a\n")
    assert vk_upload.sniff_image(png) == ("image.png", "image/png")
    gif = _img(tmp_path, "anim.gif", b"GIF89a")
    assert vk_upload.sniff_image(gif) == ("anim.gif", "application/octet-stream")


def test_http_post_uses_sniffed_filename_and_mime(tmp_path, monkeypatch):
    from services import vk_upload
    session = MagicMock()
    session.post.return_value = _FakeUploadResponse()
    monkeypatch.setattr(vk_upload, "_http_session", lambda: session)
    png = _img(tmp_path, "asset_1.png", b"\x89PNG\r\n\x1a\n")
    vk_upload._http_post("http://upload", png, (5, 30))
    files = session.post.call_args.kwargs["files"]
    filename, fileobj, mime = files["photo"]
    assert filename == "image.png"
    assert mime == "image/png"


def test_disk_cache_survives_memory_reset(tmp_path):
    from services import vk_upload
    f = _img(tmp_path, "d.jpg", b"\xff\xd8\xff")
    vk_upload.store(f, "photo-9_9")
    vk_upload._cache.clear()
    vk_upload._reverse.clear()
    vk_upload._disk_loaded = False
    assert vk_upload.get(f) == "photo-9_9"


def test_attachment_rejected_detection():
    from services import vk_upload

    class _Err(Exception):
        def __init__(self, code, msg):
            super().__init__(msg)
            self.code = code

    assert vk_upload.attachment_rejected(_Err(100, "One of the parameters specified was missing or invalid: photo is invalid")) is True
    assert vk_upload.attachment_rejected(_Err(13, "Runtime error: invalid attachment")) is True
    assert vk_upload.attachment_rejected(_Err(100, "keyboard is invalid")) is False
    assert vk_upload.attachment_rejected(_Err(6, "Too many requests")) is False
    assert vk_upload.attachment_rejected(RuntimeError("network down")) is False


def test_inflight_single_flight(tmp_path, monkeypatch):
    from services import vk_upload
    calls = {"n": 0}
    entered = threading.Event()

    def _post(url, fp, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            entered.set()
            import time
            time.sleep(0.3)
        return _FakeUploadResponse()

    monkeypatch.setattr(vk_upload, "_http_post", _post)
    f = _img(tmp_path, "d.jpg", b"\xff\xd8\xff")
    vk = _make_vk()
    results = []

    def worker():
        results.append(vk_upload.upload_message_photo(vk, f, peer_id=1))

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    entered.wait(2)
    t2.start()
    t1.join(5)
    t2.join(5)
    assert sorted(results) == ["photo-5_7", "photo-5_7"]
    assert calls["n"] == 1
