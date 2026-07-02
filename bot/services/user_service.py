"""Service functions shared between API and bot."""

from datetime import datetime


def get_or_create_user(db, vk_id: int):
    from models import User
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user:
        user = User(
            vk_id=vk_id,
            state="idle",
            registered_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
