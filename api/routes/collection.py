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
            "description": fam.description,
            "color": fam.color,
            "total_dragons": total,
            "collected": collected,
        })
    return result


@router.get("/collection/{vk_id}")
def get_collection(vk_id: int, family_id: int = Query(...), db: Session = Depends(get_db)):
    grid = db.query(CollectionGrid).filter(CollectionGrid.family_id == family_id).order_by(CollectionGrid.cell_y, CollectionGrid.cell_x).all()

    # Все драконы пользователя: добавленные по PIN или завершённые.
    # completed — у которых completed_at заполнен; growing — добавлены, но не выращены.
    user_dragons = db.query(UserDragon).filter(UserDragon.user_id == vk_id).all()
    completed_ids = {ud.dragon_id for ud in user_dragons if ud.completed_at != ""}
    growing_ids = {ud.dragon_id for ud in user_dragons if ud.completed_at == ""}

    # Прогресс по завершённым шагам (максимальный завершённый номер шага на дракона)
    progress_map = {}
    progress_rows = (
        db.query(UserProgress.dragon_id, UserProgress.step_number)
        .filter(UserProgress.user_id == vk_id, UserProgress.completed == True)
        .all()
    )
    for dragon_id, step in progress_rows:
        progress_map[dragon_id] = max(progress_map.get(dragon_id, 0), step)

    # Таймауты для растущих драконов
    timeout_map = {ud.dragon_id: ud.next_step_available_at for ud in user_dragons if ud.next_step_available_at is not None}

    # Предзагружаем драконов для ячеек, чтобы не дёргать БД в цикле
    dragon_ids = {c.dragon_id for c in grid if c.dragon_id}
    dragons_map = {
        d.id: d
        for d in db.query(Dragon).filter(Dragon.id.in_(dragon_ids)).all()
    } if dragon_ids else {}

    result = []
    for cell in grid:
        dragon = dragons_map.get(cell.dragon_id) if cell.dragon_id else None
        status = "locked"
        progress_pct = 0

        if cell.dragon_id and cell.dragon_id in completed_ids:
            status = "completed"
            progress_pct = 100
        elif cell.dragon_id and (cell.dragon_id in growing_ids or cell.dragon_id in progress_map):
            # БАГ2: добавлен (UserDragon) или уже есть прогресс шагов -> growing, не locked
            status = "growing"
            steps_count = dragon.steps_count if dragon and dragon.steps_count else 5
            done = progress_map.get(cell.dragon_id, 0)
            progress_pct = min(100, round((done / steps_count) * 100))

        # egg_url — картинка яйца (для growing); dragon_url — взрослый дракон (для completed)
        egg_url = (
            f"/api/static/images/{dragon.egg_path}"
            if status == "growing" and dragon and dragon.egg_path else None
        )
        dragon_url = (
            f"/api/static/images/{dragon.dragon_path}"
            if status == "completed" and dragon and dragon.dragon_path else None
        )

        result.append({
            "x": cell.cell_x,
            "y": cell.cell_y,
            "dragon_id": cell.dragon_id,
            "status": status,
            "progress_pct": progress_pct,
            "name": dragon.name if status == "completed" else None,
            "egg_type": dragon.egg_type if (status == "growing" and dragon) else None,
            "rarity": dragon.rarity if dragon else None,
            "egg_url": egg_url,
            "dragon_url": dragon_url,
            "next_step_available_at": timeout_map.get(cell.dragon_id) if status == "growing" else None,
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
        .filter(UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon_id, UserDragon.completed_at != "")
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

    revealed = bool(completed)

    ud = db.query(UserDragon).filter(UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon_id).first()
    next_step_available_at = ud.next_step_available_at if ud else None

    family = db.query(Family).filter(Family.id == dragon.family_id).first() if dragon.family_id else None

    return {
        "is_revealed": revealed,
        "name": dragon.name if revealed else None,
        "rarity": dragon.rarity,
        "egg_type": dragon.egg_type,
        "steps_count": dragon.steps_count,
        "description": dragon.description if revealed else None,
        "dragon_url": f"/api/static/images/{dragon.dragon_path}" if revealed and dragon.dragon_path else None,
        "egg_url": f"/api/static/images/{dragon.egg_path}" if not revealed and dragon.egg_path else None,
        "next_step_available_at": next_step_available_at,
        "family_color": family.color if family else None,
        "user_progress": {
            "status": "completed" if revealed else ("growing" if completed_steps > 0 else "locked"),
            "completed_steps": completed_steps,
            "steps": step_info,
        },
    }
