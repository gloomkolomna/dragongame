from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from db import get_db
from models import CollectionGrid, UserDragon, UserProgress, Dragon, Family, User

router = APIRouter(prefix="/api", tags=["collection"])


@router.get("/collection/{vk_id}/balance")
def get_balance(vk_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    return {"stitches_balance": user.stitches_balance if user else 0}


@router.get("/collection/{vk_id}/shop")
def get_shop(vk_id: int, db: Session = Depends(get_db)):
    from services.shop_service import get_current_stage_key, get_stage_items, get_inventory
    stage_key = get_current_stage_key(db, vk_id)
    items = get_stage_items(db, stage_key)
    owned = {it.id for it, _ in get_inventory(db, vk_id)}
    return {
        "stage_key": stage_key,
        "items": [
            {
                "id": it.id,
                "name": it.name,
                "description": it.description,
                "cost_stitches": it.cost_stitches,
                "image_path": f"/api/static/images/{it.image_path}" if it.image_path else "",
                "is_consumable": it.is_consumable,
                "is_optional": it.is_optional,
                "owned": it.id in owned,
            }
            for it in items
        ],
    }


@router.get("/collection/{vk_id}/inventory")
def get_inventory_route(vk_id: int, db: Session = Depends(get_db)):
    from services.shop_service import get_inventory
    return [
        {
            "id": it.id,
            "name": it.name,
            "description": it.description,
            "image_path": f"/api/static/images/{it.image_path}" if it.image_path else "",
            "is_consumable": it.is_consumable,
            "quantity": qty,
        }
        for it, qty in get_inventory(db, vk_id)
    ]


@router.get("/collection/{vk_id}/legend/{dragon_id}")
def get_legend_view(vk_id: int, dragon_id: int, db: Session = Depends(get_db)):
    from models import DragonStep, UserLegendProgress
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    if not dragon:
        return {"has_legend": False, "fragments": []}
    frags = (
        db.query(DragonStep)
        .filter(DragonStep.dragon_id == dragon_id, DragonStep.phase == 1)
        .order_by(DragonStep.step_number)
        .all()
    )
    done = {
        r.fragment_number
        for r in db.query(UserLegendProgress).filter(
            UserLegendProgress.user_id == vk_id,
            UserLegendProgress.dragon_id == dragon_id,
            UserLegendProgress.completed == True,
        ).all()
    }
    all_completed = len(frags) > 0 and len(done) >= len(frags)
    return {
        "has_legend": len(frags) > 0,
        "dragon_id": dragon.id,
        "cover": f"/api/static/images/{dragon.legend_image_path}" if dragon.legend_image_path else "",
        "name": dragon.legend_title or dragon.name,
        "all_completed": all_completed,
        "full_text": dragon.legend_full_text if all_completed else "",
        "fragments": (
            []
            if all_completed
            else [
                {
                    "number": f.step_number,
                    "opened": f.step_number in done,
                    "task": f.task_description if f.step_number in done else "",
                    "assignment": f.magic_action if f.step_number in done else "",
                    "image": f"/api/static/images/{f.image_path}" if (f.step_number in done and f.image_path) else "",
                }
                for f in frags
            ]
        ),
    }


@router.get("/collection/{vk_id}/treasures")
def get_treasures(vk_id: int, db: Session = Depends(get_db)):
    from models import Treasure, UserTreasure, Dragon
    treasures = db.query(Treasure).filter(Treasure.is_active == True).order_by(Treasure.id).all()
    owned_ids = {
        ut.treasure_id
        for ut in db.query(UserTreasure).filter(UserTreasure.user_id == vk_id).all()
    }
    dragon_map = {}
    family_map = {}
    dragon_ids = {t.dragon_id for t in treasures if t.dragon_id}
    family_ids = {t.family_id for t in treasures if t.family_id}
    if dragon_ids:
        dragon_map = {d.id: d.name for d in db.query(Dragon).filter(Dragon.id.in_(dragon_ids)).all()}
    if family_ids:
        family_map = {f.id: f.name for f in db.query(Family).filter(Family.id.in_(family_ids)).all()}

    dragon_collected = []
    dragon_uncollected = []
    family_collected = []
    family_uncollected = []

    for t in treasures:
        image = f"/api/static/images/{t.image_path}" if t.image_path else ""
        base = {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "image": image,
        }
        if t.dragon_id:
            base["dragon_id"] = t.dragon_id
            base["dragon_name"] = dragon_map.get(t.dragon_id, "")
            base["source"] = "dragon"
            if t.id in owned_ids:
                dragon_collected.append(base)
            else:
                dragon_uncollected.append({"id": t.id, "silhouette": image, "source": "dragon"})
        elif t.family_id:
            base["family_id"] = t.family_id
            base["family_name"] = family_map.get(t.family_id, "")
            base["source"] = "family"
            if t.id in owned_ids:
                family_collected.append(base)
            else:
                family_uncollected.append({"id": t.id, "silhouette": image, "source": "family"})

    return {
        "dragon": {"collected": dragon_collected, "uncollected": dragon_uncollected},
        "family": {"collected": family_collected, "uncollected": family_uncollected},
        "total": len(treasures),
    }


@router.get("/collection/{vk_id}/legends")
def get_legends(vk_id: int, db: Session = Depends(get_db)):
    from models import DragonStep, UserLegendProgress
    completed_dragon_ids = {
        ud.dragon_id
        for ud in db.query(UserDragon).filter(
            UserDragon.user_id == vk_id,
            UserDragon.completed_at != "",
        ).all()
    }
    dragons = (
        db.query(Dragon)
        .filter(Dragon.rarity == 3, Dragon.is_active == True)
        .order_by(Dragon.id)
        .all()
    )
    result = []
    for d in dragons:
        if d.id not in completed_dragon_ids:
            continue
        total = db.query(DragonStep).filter(
            DragonStep.dragon_id == d.id, DragonStep.phase == 1
        ).count()
        if total == 0:
            continue
        opened = db.query(UserLegendProgress).filter(
            UserLegendProgress.user_id == vk_id,
            UserLegendProgress.dragon_id == d.id,
            UserLegendProgress.completed == True,
        ).count()
        result.append({
            "dragon_id": d.id,
            "name": d.legend_title or d.name,
            "cover": f"/api/static/images/{d.legend_image_path}" if d.legend_image_path else "",
            "fragments_opened": opened,
            "fragments_total": total,
        })
    return result


@router.get("/collection/{vk_id}/epic")
def get_epic_view(vk_id: int, db: Session = Depends(get_db)):
    from services import epic_service
    from services.character_service import character_summary
    dragon = epic_service.get_epic_dragon(db, vk_id)
    if not dragon:
        return {"has_epic": False}

    name = epic_service.get_epic_name(db, vk_id)
    care = epic_service.get_care(db, vk_id)
    moodlets = [
        {"key": m.key, "title": m.title, "polarity": m.polarity, "text": m.text}
        for m in epic_service.get_moodlets(db, vk_id)
    ]
    character = character_summary(db, care.user_dragon_id) if care else []
    base = {
        "has_epic": True,
        "name": name,
        "egg_type": dragon.egg_type,
        "egg_url": f"/api/static/images/{dragon.egg_path}" if dragon.egg_path else "",
        "dragon_url": f"/api/static/images/{dragon.dragon_path}" if dragon.dragon_path else "",
        "moodlets": moodlets,
        "character": character,
    }

    if not care:
        base["phase"] = "egg"
        base["egg_progress"] = {
            "completed": epic_service.egg_completed_count(db, vk_id),
            "total": epic_service.egg_total(db, vk_id),
        }
        base["hatched"] = epic_service.is_egg_hatched(db, vk_id)
        return base

    stage = epic_service.get_stage(db, care.stage_id)
    action = epic_service.get_current_action(db, care)
    remaining = epic_service.get_care_remaining(db, care)
    owned_missing = {m.id for m in epic_service.missing_action_items(db, vk_id, action.id)} if action else set()
    base["phase"] = "care"
    base["stage"] = {
        "number": stage.stage_number if stage else 0,
        "name": stage.name if stage else "",
        "description": stage.description if stage else "",
        "image_start": f"/api/static/images/{stage.image_start}" if stage and stage.image_start else "",
        "image_end": f"/api/static/images/{stage.image_end}" if stage and stage.image_end else "",
        "cycle_completed": care.cycles_completed or 0,
        "cycle_total": stage.cycles_count if stage else 0,
    }
    if action:
        base["action"] = {
            "label": action.action_label,
            "task": action.task,
            "hint": action.hint,
            "crosses_norm": action.crosses_norm,
            "timeout_hours": action.timeout_hours,
            "timeout_minutes": action.timeout_minutes,
            "items": [
                {"id": it.id, "name": it.name, "owned": it.id not in owned_missing}
                for it in epic_service.action_items(db, action.id)
            ],
        }
    else:
        base["action"] = None
    base["care_remaining_seconds"] = int(remaining.total_seconds()) if remaining else 0
    return base


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
            "image_path": f"/api/static/images/{fam.image_path}" if fam.image_path else "",
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
            "completed_steps": done if status == "growing" else (dragon.steps_count if status == "completed" and dragon else 0),
            "steps_count": dragon.steps_count if dragon else 5,
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

    from models import Treasure, UserTreasure
    treasure_info = None
    if revealed:
        t = db.query(Treasure).filter(
            Treasure.dragon_id == dragon_id, Treasure.is_active == True
        ).first()
        if t:
            owned = db.query(UserTreasure).filter(
                UserTreasure.user_id == vk_id, UserTreasure.treasure_id == t.id
            ).first()
            if owned:
                treasure_info = {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "image": f"/api/static/images/{t.image_path}" if t.image_path else "",
                }

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
        "treasure": treasure_info,
        "user_progress": {
            "status": "completed" if revealed else ("growing" if completed_steps > 0 else "locked"),
            "completed_steps": completed_steps,
            "steps": step_info,
        },
    }
