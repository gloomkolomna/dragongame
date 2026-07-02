import os
import secrets
from sqlalchemy.orm import Session
from fastapi import UploadFile
from models import Dragon, DragonStep

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "images", "dragons")

def _generate_pin_code(db: Session) -> str:
    for _ in range(1000):
        code = f"{secrets.randbelow(10000):04d}"
        exists = db.query(Dragon).filter(Dragon.pin_code == code).first()
        if not exists:
            return code
    raise RuntimeError("Cannot generate unique PIN code after 1000 attempts")

def _save_upload(file: UploadFile, folder: str, prefix: str) -> str:
    os.makedirs(folder, exist_ok=True)
    ext = os.path.splitext(file.filename or ".png")[1].lower() or ".png"
    filename = f"{prefix}{ext}"
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return ext

def get_dragons(db: Session) -> list[Dragon]:
    return db.query(Dragon).order_by(Dragon.id).all()

def get_dragon(db: Session, dragon_id: int) -> Dragon | None:
    return db.query(Dragon).filter(Dragon.id == dragon_id).first()

def create_dragon(
    db: Session,
    name: str,
    rarity: int,
    egg_type: str,
    description: str,
    family_id: int,
    image: UploadFile | None = None,
    silhouette: UploadFile | None = None,
) -> Dragon:
    dragon = Dragon(
        name=name, rarity=rarity, egg_type=egg_type,
        description=description, steps_count=0, is_active=True,
        pin_code=_generate_pin_code(db),
        family_id=family_id,
    )
    db.add(dragon)
    db.flush()

    if image and image.filename:
        ext = _save_upload(image, IMAGES_DIR, str(dragon.id))
        dragon.egg_path = f"dragons/{dragon.id}{ext}"
    if silhouette and silhouette.filename:
        ext = _save_upload(silhouette, IMAGES_DIR, f"{dragon.id}_silhouette")
        dragon.dragon_path = f"dragons/{dragon.id}_silhouette{ext}"

    db.commit()
    db.refresh(dragon)
    return dragon

def update_dragon(
    db: Session,
    dragon_id: int,
    name: str | None = None,
    rarity: int | None = None,
    egg_type: str | None = None,
    description: str | None = None,
    is_active: bool | None = None,
    family_id: int | None = None,
    image: UploadFile | None = None,
    silhouette: UploadFile | None = None,
) -> Dragon | None:
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    if not dragon:
        return None

    if name is not None: dragon.name = name
    if rarity is not None: dragon.rarity = rarity
    if egg_type is not None: dragon.egg_type = egg_type
    if description is not None: dragon.description = description
    if is_active is not None: dragon.is_active = is_active
    if family_id is not None: dragon.family_id = family_id

    if image and image.filename:
        _cleanup_old(IMAGES_DIR, str(dragon.id), dragon.egg_path)
        ext = _save_upload(image, IMAGES_DIR, str(dragon.id))
        dragon.egg_path = f"dragons/{dragon.id}{ext}"
    if silhouette and silhouette.filename:
        _cleanup_old(IMAGES_DIR, f"{dragon.id}_silhouette", dragon.dragon_path)
        ext = _save_upload(silhouette, IMAGES_DIR, f"{dragon.id}_silhouette")
        dragon.dragon_path = f"dragons/{dragon.id}_silhouette{ext}"

    db.commit()
    db.refresh(dragon)
    return dragon


def _cleanup_old(folder: str, prefix: str, old_path: str):
    if not old_path:
        return
    old_file = os.path.join(folder, os.path.basename(old_path))
    if os.path.isfile(old_file):
        os.remove(old_file)


def delete_dragon(db: Session, dragon_id: int) -> bool:
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    if not dragon:
        return False
    db.delete(dragon)
    db.commit()
    return True

def sync_steps_count(db: Session, dragon_id: int):
    """Обновляет dragon.steps_count по реальному числу шагов в dragon_steps."""
    count = db.query(DragonStep).filter(DragonStep.dragon_id == dragon_id).count()
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    if dragon:
        dragon.steps_count = count
        db.commit()
