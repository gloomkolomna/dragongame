import io

import pytest
from fastapi import HTTPException, UploadFile


def _upload_file(data: bytes, filename: str) -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(data))


def test_save_jpeg_with_real_extension(tmp_path):
    from services.image_store import save_upload
    f = _upload_file(b"\xff\xd8\xff\xe0" + b"x" * 10, "photo.png")
    name = save_upload(f, str(tmp_path), "drag")
    assert name.startswith("drag_")
    assert name.endswith(".jpg")
    assert (tmp_path / name).read_bytes().startswith(b"\xff\xd8\xff")


def test_save_png(tmp_path):
    from services.image_store import save_upload
    f = _upload_file(b"\x89PNG\r\n\x1a\n" + b"x" * 10, "asset.png")
    name = save_upload(f, str(tmp_path), "fam")
    assert name.startswith("fam_")
    assert name.endswith(".png")
    assert (tmp_path / name).read_bytes().startswith(b"\x89PNG")


def test_save_gif_rejected(tmp_path):
    from services.image_store import save_upload
    f = _upload_file(b"GIF89a" + b"x" * 10, "anim.gif")
    with pytest.raises(HTTPException) as exc:
        save_upload(f, str(tmp_path), "drag")
    assert exc.value.status_code == 400


def test_save_too_large_rejected(tmp_path):
    from services.image_store import save_upload
    data = b"\xff\xd8\xff" + b"x" * (5 * 1024 * 1024)
    f = _upload_file(data, "big.jpg")
    with pytest.raises(HTTPException) as exc:
        save_upload(f, str(tmp_path), "drag")
    assert exc.value.status_code == 413


def test_dragon_service_save_upload_validates(tmp_path):
    from services.dragon_service import _save_upload
    f = _upload_file(b"GIF89a" + b"x" * 10, "anim.gif")
    with pytest.raises(HTTPException):
        _save_upload(f, str(tmp_path), "drag")
