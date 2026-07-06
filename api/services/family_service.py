import os
from time import time
from sqlalchemy.orm import Session
from fastapi import UploadFile
from models import Family

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "images", "families")


def _save_upload(file: UploadFile, folder: str, prefix: str) -> str:
    os.makedirs(folder, exist_ok=True)
    ext = os.path.splitext(file.filename or ".png")[1].lower() or ".png"
    ts = int(time())
    filename = f"{prefix}_{ts}{ext}"
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return filename


def _cleanup_old(folder: str, old_path: str):
    if not old_path:
        return
    old_file = os.path.join(folder, os.path.basename(old_path))
    if os.path.isfile(old_file):
        os.remove(old_file)


def create_family(
    db: Session,
    name: str,
    description: str = "",
    sort_order: int = 0,
    color: str = "#9b6fc7",
    image: UploadFile | None = None,
) -> Family:
    fam = Family(name=name, description=description, sort_order=sort_order, color=color)
    db.add(fam)
    db.flush()

    if image and image.filename:
        filename = _save_upload(image, IMAGES_DIR, str(fam.id))
        fam.image_path = f"families/{filename}"

    db.commit()
    db.refresh(fam)
    return fam


def update_family(
    db: Session,
    family_id: int,
    name: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
    color: str | None = None,
    image: UploadFile | None = None,
) -> Family | None:
    fam = db.query(Family).filter(Family.id == family_id).first()
    if not fam:
        return None

    if name is not None: fam.name = name
    if description is not None: fam.description = description
    if sort_order is not None: fam.sort_order = sort_order
    if color is not None: fam.color = color

    if image and image.filename:
        _cleanup_old(IMAGES_DIR, fam.image_path)
        filename = _save_upload(image, IMAGES_DIR, str(fam.id))
        fam.image_path = f"families/{filename}"

    db.commit()
    db.refresh(fam)
    return fam
