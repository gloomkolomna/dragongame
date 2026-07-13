import os
import secrets
import string
from time import time
from sqlalchemy.orm import Session
from fastapi import UploadFile
from models import Dragon, DragonStep

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "images", "dragons")

def _generate_pin_code(db: Session) -> str:
    chars = string.ascii_uppercase + string.digits
    for _ in range(1000):
        code = "".join(secrets.choice(chars) for _ in range(5))
        exists = db.query(Dragon).filter(Dragon.pin_code == code).first()
        if not exists:
            return code
    raise RuntimeError("Cannot generate unique PIN code after 1000 attempts")

def _save_upload(file: UploadFile, folder: str, prefix: str) -> str:
    os.makedirs(folder, exist_ok=True)
    ext = os.path.splitext(file.filename or ".png")[1].lower() or ".png"
    ts = int(time())
    filename = f"{prefix}_{ts}{ext}"
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return filename

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
    is_epic: bool = False,
    epic_cost_stitches: int | None = None,
) -> Dragon:
    dragon = Dragon(
        name=name, rarity=rarity, egg_type=egg_type,
        description=description, steps_count=0, is_active=True,
        pin_code=_generate_pin_code(db),
        family_id=family_id,
        is_epic=is_epic,
        epic_cost_stitches=epic_cost_stitches,
    )
    db.add(dragon)
    db.flush()

    if image and image.filename:
        filename = _save_upload(image, IMAGES_DIR, str(dragon.id))
        dragon.egg_path = f"dragons/{filename}"
    if silhouette and silhouette.filename:
        filename = _save_upload(silhouette, IMAGES_DIR, f"{dragon.id}_silhouette")
        dragon.dragon_path = f"dragons/{filename}"

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
    is_epic: bool | None = None,
    epic_cost_stitches: int | None = None,
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
    if is_epic is not None: dragon.is_epic = is_epic
    if epic_cost_stitches is not None: dragon.epic_cost_stitches = epic_cost_stitches

    if image and image.filename:
        _cleanup_old(IMAGES_DIR, str(dragon.id), dragon.egg_path)
        filename = _save_upload(image, IMAGES_DIR, str(dragon.id))
        dragon.egg_path = f"dragons/{filename}"
    if silhouette and silhouette.filename:
        _cleanup_old(IMAGES_DIR, f"{dragon.id}_silhouette", dragon.dragon_path)
        filename = _save_upload(silhouette, IMAGES_DIR, f"{dragon.id}_silhouette")
        dragon.dragon_path = f"dragons/{filename}"

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
    """Обновляет dragon.steps_count по реальному числу шагов ЯЙЦА (phase=0)."""
    count = db.query(DragonStep).filter(
        DragonStep.dragon_id == dragon_id, DragonStep.phase == 0
    ).count()
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    if dragon:
        dragon.steps_count = count
        db.commit()
