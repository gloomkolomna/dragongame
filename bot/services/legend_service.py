"""Legend service — fragment progress tracking for rarity-3 dragons."""

from datetime import datetime


def get_legend_steps(db, dragon_id: int):
    from models import DragonStep
    return (
        db.query(DragonStep)
        .filter(DragonStep.dragon_id == dragon_id, DragonStep.phase == 1)
        .order_by(DragonStep.step_number)
        .all()
    )


def get_legend_total(db, dragon_id: int) -> int:
    return len(get_legend_steps(db, dragon_id))


def is_legend_completed(db, vk_id: int, dragon_id: int) -> bool:
    from models import UserLegendProgress
    total = get_legend_total(db, dragon_id)
    if total == 0:
        return False
    done = (
        db.query(UserLegendProgress)
        .filter(
            UserLegendProgress.user_id == vk_id,
            UserLegendProgress.dragon_id == dragon_id,
            UserLegendProgress.completed == True,
        )
        .count()
    )
    return done >= total


def get_next_legend_fragment(db, vk_id: int, dragon_id: int):
    from models import UserLegendProgress
    done_rows = (
        db.query(UserLegendProgress)
        .filter(
            UserLegendProgress.user_id == vk_id,
            UserLegendProgress.dragon_id == dragon_id,
            UserLegendProgress.completed == True,
        )
        .all()
    )
    done = {r.fragment_number for r in done_rows}
    steps = get_legend_steps(db, dragon_id)
    for s in steps:
        if s.step_number not in done:
            return s
    return None


def complete_legend_fragment(db, vk_id, dragon_id, fragment_number,
                             photo_before_id="", photo_after_id=""):
    from models import UserLegendProgress
    row = db.query(UserLegendProgress).filter(
        UserLegendProgress.user_id == vk_id,
        UserLegendProgress.dragon_id == dragon_id,
        UserLegendProgress.fragment_number == fragment_number,
    ).first()
    if row:
        row.completed = True
        row.completed_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if photo_before_id:
            row.photo_before_id = photo_before_id
        if photo_after_id:
            row.photo_after_id = photo_after_id
    else:
        db.add(UserLegendProgress(
            user_id=vk_id, dragon_id=dragon_id, fragment_number=fragment_number,
            completed=True, completed_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            photo_before_id=photo_before_id, photo_after_id=photo_after_id,
        ))
    db.commit()



