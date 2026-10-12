import os
import time

ALLOWED_EXTENSIONS = (".jpg", ".jpeg", ".png")
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

_JPEG_MAGIC = b"\xff\xd8\xff"
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def detect_image_format(data: bytes) -> str:
    if data.startswith(_JPEG_MAGIC):
        return ".jpg"
    if data.startswith(_PNG_MAGIC):
        return ".png"
    return ""


def save_upload(file, folder: str, prefix: str) -> str:
    from fastapi import HTTPException
    data = file.file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Файл больше 5 МБ")
    ext = detect_image_format(data)
    if not ext:
        raise HTTPException(status_code=400, detail="Файл не является JPG или PNG изображением")
    os.makedirs(folder, exist_ok=True)
    ts = int(time.time())
    filename = f"{prefix}_{ts}{ext}"
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        f.write(data)
    return filename
