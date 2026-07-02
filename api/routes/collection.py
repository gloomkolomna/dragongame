from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from db import get_db
from models import CollectionGrid, UserDragon, UserProgress, Dragon, Family

router = APIRouter(prefix="/api", tags=["collection"])


@router.get("/collection/{vk_id}/families")
def get_collection_families(vk_id: int, db: Session = Depends(get_db)):
    families = db.query(Family).order_by(Family.sort_order, Family.id).all()
    result = []
    for fam in families:
        total = db.query(Dragon).filter(Dragon.family_id == fam.id, Dragon.is_active == True).count()
        collected = db.query(UserDragon).join(Dragon).filter(
            UserDragon.user_id == vk_id,
            Dragon.family_id == fam.id,
            Dragon.is_active == True,
        ).count()
        result.append({
            "id": fam.id,
            "name": fam.name,
            "total_dragons": total,
            "collected": collected,
        })
    return result


@router.get("/collection/{vk_id}")
def get_collection(vk_id: int, family_id: int = Query(...), db: Session = Depends(get_db)):
    grid = db.query(CollectionGrid).filter(CollectionGrid.family_id == family_id).order_by(CollectionGrid.cell_y, CollectionGrid.cell_x).all()

    # Get user's completed dragons
    completed_ids = {
        row.dragon_id
        for row in db.query(UserDragon.dragon_id)
        .filter(UserDragon.user_id == vk_id)
        .all()
    }

    # Get user's in-progress dragons
    progress_map = {}
    progress_rows = (
        db.query(UserProgress.dragon_id, UserProgress.step_number)
        .filter(UserProgress.user_id == vk_id, UserProgress.completed == True)
        .all()
    )
    for dragon_id, step in progress_rows:
        progress_map[dragon_id] = max(progress_map.get(dragon_id, 0), step)

    result = []
    for cell in grid:
        dragon = db.query(Dragon).filter(Dragon.id == cell.dragon_id).first()
        status = "locked"
        progress_pct = 0

        if cell.dragon_id and cell.dragon_id in completed_ids:
            status = "completed"
            progress_pct = 100
        elif cell.dragon_id and cell.dragon_id in progress_map:
            status = "growing"
            steps_count = dragon.steps_count if dragon else 5
            progress_pct = min(100, round((progress_map[cell.dragon_id] / steps_count) * 100))

        result.append({
            "x": cell.cell_x,
            "y": cell.cell_y,
            "dragon_id": cell.dragon_id,
            "status": status,
            "progress_pct": progress_pct,
            "name": dragon.name if status == "completed" else None,
            "rarity": dragon.rarity if dragon else None,
            "silhouette_url": f"/api/static/images/dragons/{cell.dragon_id}_silhouette.png" if cell.dragon_id and status != "completed" else None,
            "image_url": f"/api/static/images/dragons/{cell.dragon_id}.png" if cell.dragon_id and status == "completed" else None,
        })

    return {
        "grid": result,
        "total_collected": len(completed_ids),
        "total_dragons": db.query(Dragon).filter(Dragon.is_active == True).count(),
    }


@router.get("/dragon/{dragon_id}")
def get_dragon(
    dragon_id: int,
    vk_id: int = Query(...),
    db: Session = Depends(get_db),
):
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    if not dragon:
        return {"error": "not found"}

    # Check if completed
    completed = (
        db.query(UserDragon)
        .filter(UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon_id)
        .first()
    )

    # Get progress steps
    steps = (
        db.query(UserProgress)
        .filter(UserProgress.user_id == vk_id, UserProgress.dragon_id == dragon_id)
        .order_by(UserProgress.step_number)
        .all()
    )

    completed_steps = sum(1 for s in steps if s.completed)
    all_completed = completed_steps >= dragon.steps_count

    # Get step definitions from DB
    from models import DragonStep
    step_defs = (
        db.query(DragonStep)
        .filter(DragonStep.dragon_id == dragon_id)
        .order_by(DragonStep.step_number)
        .all()
    )

    step_info = []
    for sd in step_defs:
        user_step = next((s for s in steps if s.step_number == sd.step_number), None)
        step_info.append({
            "number": sd.step_number,
            "task": sd.task_description or sd.magic_action or "",
            "completed": user_step.completed if user_step else False,
        })

    return {
        "is_revealed": bool(completed) or all_completed,
        "name": dragon.name if (completed or all_completed) else None,
        "rarity": dragon.rarity,
        "egg_type": dragon.egg_type,
        "steps_count": dragon.steps_count,
        "description": dragon.description if (completed or all_completed) else None,
        "image_url": f"/api/static/images/dragons/{dragon_id}.png" if (completed or all_completed) else None,
        "user_progress": {
            "status": "completed" if bool(completed) or all_completed else ("growing" if completed_steps > 0 else "locked"),
            "completed_steps": completed_steps,
            "steps": step_info,
        },
    }
