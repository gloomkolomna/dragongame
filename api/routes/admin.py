import json
import os
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from db import get_db
from auth import get_current_admin
from models import Dragon, DragonStep, User, UserDragon, CollectionGrid, UserProgress, Family, ErrorLog, ServiceHeartbeat, ApiRequestLog
from config import API_ERROR_LOG
from services.dragon_service import (
    get_dragons, get_dragon, create_dragon, update_dragon, delete_dragon, sync_steps_count,
)

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])


# ─── Stats ───

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    return {
        "dragons_total": db.query(Dragon).count(),
        "dragons_active": db.query(Dragon).filter(Dragon.is_active == True).count(),
        "pins_total": db.query(Dragon).filter(Dragon.pin_code != None).count(),
        "pins_active": db.query(Dragon).filter(Dragon.pin_code != None, Dragon.is_active == True).count(),
        "pins_used": 0,
        "users_total": db.query(User).count(),
        "dragons_collected_total": db.query(UserDragon).count(),
    }


# ─── Dragons CRUD ───

@router.get("/dragons")
def list_dragons(db: Session = Depends(get_db)):
    return get_dragons(db)


@router.get("/dragons/{dragon_id}")
def get_dragon_by_id(dragon_id: int, db: Session = Depends(get_db)):
    dragon = get_dragon(db, dragon_id)
    if not dragon:
        raise HTTPException(status_code=404, detail="Dragon not found")
    return dragon


@router.post("/dragons")
def create_dragon_route(
    name: str = Form(...),
    rarity: int = Form(...),
    egg_type: str = Form(""),
    description: str = Form(""),
    family_id: int = Form(...),
    image: Optional[UploadFile] = File(None),
    silhouette: Optional[UploadFile] = File(None),
    steps: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    dragon = create_dragon(db, name, rarity, egg_type, description, family_id, image, silhouette)

    if steps:
        try:
            steps_data = json.loads(steps)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid steps JSON")
        for s in steps_data:
            th = max(0, int(s.get("timeout_hours", 0) or 0))
            tm = max(0, min(59, int(s.get("timeout_minutes", 0) or 0)))
            cn = max(1, int(s.get("crosses_norm", 1000) or 1000))
            db.add(DragonStep(
                dragon_id=dragon.id,
                step_number=s.get("step_number", 0),
                magic_action=s.get("magic_action", ""),
                task_description=s.get("task_description", ""),
                hint=s.get("hint", ""),
                keyword="вышито",
                timeout_hours=th,
                timeout_minutes=tm,
                crosses_norm=cn,
            ))
        db.commit()
        sync_steps_count(db, dragon.id)
        logging.getLogger("uvicorn").info(f"[STEPS] Saved {len(steps_data)} steps for dragon {dragon.id}")
    else:
        logging.getLogger("uvicorn").info(f"[STEPS] No steps received for dragon {dragon.id}")

    return dragon


@router.put("/dragons/{dragon_id}")
def update_dragon_route(
    dragon_id: int,
    name: Optional[str] = Form(None),
    rarity: Optional[int] = Form(None),
    egg_type: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    family_id: Optional[int] = Form(None),
    image: Optional[UploadFile] = File(None),
    silhouette: Optional[UploadFile] = File(None),
    steps: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    dragon = update_dragon(db, dragon_id, name, rarity, egg_type, description,
                           is_active, family_id, image, silhouette)
    if not dragon:
        raise HTTPException(status_code=404, detail="Dragon not found")

    if steps:
        try:
            steps_data = json.loads(steps)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid steps JSON")
        submitted_ids = {s.get("id", 0) for s in steps_data if s.get("id", 0) != 0}
        if submitted_ids:
            db.query(DragonStep).filter(
                DragonStep.dragon_id == dragon_id,
                DragonStep.id.notin_(submitted_ids),
            ).delete(synchronize_session=False)
        else:
            db.query(DragonStep).filter(DragonStep.dragon_id == dragon_id).delete(synchronize_session=False)
        for s in steps_data:
            th = max(0, int(s.get("timeout_hours", 0) or 0))
            tm = max(0, min(59, int(s.get("timeout_minutes", 0) or 0)))
            cn = max(1, int(s.get("crosses_norm", 1000) or 1000))
            sid = s.get("id", 0)
            if sid == 0:
                step = DragonStep(dragon_id=dragon_id, step_number=s.get("step_number", 0),
                                  magic_action=s.get("magic_action", ""),
                                  task_description=s.get("task_description", ""),
                                  hint=s.get("hint", ""), keyword="вышито",
                                  timeout_hours=th, timeout_minutes=tm,
                                  crosses_norm=cn)
                db.add(step)
            else:
                step = db.query(DragonStep).filter(DragonStep.id == sid, DragonStep.dragon_id == dragon_id).first()
                if step:
                    step.step_number = s.get("step_number", step.step_number)
                    step.magic_action = s.get("magic_action", step.magic_action)
                    step.task_description = s.get("task_description", step.task_description)
                    step.hint = s.get("hint", step.hint)
                    step.keyword = "вышито"
                    step.timeout_hours = th
                    step.timeout_minutes = tm
                    step.crosses_norm = cn
        db.commit()
        sync_steps_count(db, dragon_id)

    return dragon


@router.delete("/dragons/{dragon_id}")
def delete_dragon_route(dragon_id: int, db: Session = Depends(get_db)):
    ok = delete_dragon(db, dragon_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Dragon not found")
    return {"ok": True}


# ─── Steps ───

@router.get("/dragons/{dragon_id}/steps")
def get_steps(dragon_id: int, db: Session = Depends(get_db)):
    return (
        db.query(DragonStep)
        .filter(DragonStep.dragon_id == dragon_id)
        .order_by(DragonStep.step_number)
        .all()
    )


@router.put("/dragons/{dragon_id}/steps")
async def save_steps(dragon_id: int, request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    steps_data = data.get("steps", [])
    submitted_ids = {s.get("id", 0) for s in steps_data if s.get("id", 0) != 0}
    if submitted_ids:
        db.query(DragonStep).filter(
            DragonStep.dragon_id == dragon_id,
            DragonStep.id.notin_(submitted_ids),
        ).delete(synchronize_session=False)
    else:
        db.query(DragonStep).filter(DragonStep.dragon_id == dragon_id).delete(synchronize_session=False)
    for s in steps_data:
        th = max(0, int(s.get("timeout_hours", 0) or 0))
        tm = max(0, min(59, int(s.get("timeout_minutes", 0) or 0)))
        cn = max(1, int(s.get("crosses_norm", 1000) or 1000))
        sid = s.get("id", 0)
        if sid == 0:
            step = DragonStep(dragon_id=dragon_id, step_number=s.get("step_number", 0),
                              magic_action=s.get("magic_action", ""),
                              task_description=s.get("task_description", ""),
                              hint=s.get("hint", ""), keyword="вышито",
                              timeout_hours=th, timeout_minutes=tm,
                              crosses_norm=cn)
            db.add(step)
        else:
            step = db.query(DragonStep).filter(DragonStep.id == sid, DragonStep.dragon_id == dragon_id).first()
            if step:
                step.step_number = s.get("step_number", step.step_number)
                step.magic_action = s.get("magic_action", step.magic_action)
                step.task_description = s.get("task_description", step.task_description)
                step.hint = s.get("hint", step.hint)
                step.keyword = "вышито"
                step.timeout_hours = th
                step.timeout_minutes = tm
                step.crosses_norm = cn
    db.commit()
    sync_steps_count(db, dragon_id)
    return {"ok": True, "saved": len(steps_data)}


@router.post("/dragons/{dragon_id}/steps")
def add_step(dragon_id: int, db: Session = Depends(get_db)):
    dragon = get_dragon(db, dragon_id)
    if not dragon:
        raise HTTPException(status_code=404, detail="Dragon not found")
    max_number = db.query(DragonStep).filter(DragonStep.dragon_id == dragon_id).count()
    step = DragonStep(dragon_id=dragon_id, step_number=max_number + 1, magic_action="", task_description="", hint="", timeout_hours=0, timeout_minutes=0, crosses_norm=1000)
    db.add(step)
    db.commit()
    sync_steps_count(db, dragon_id)
    db.refresh(step)
    return step


@router.delete("/dragons/{dragon_id}/steps/{step_id}")
def delete_step(dragon_id: int, step_id: int, db: Session = Depends(get_db)):
    step = db.query(DragonStep).filter(DragonStep.id == step_id, DragonStep.dragon_id == dragon_id).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    db.delete(step)
    db.commit()
    # Re-number remaining steps
    remaining = db.query(DragonStep).filter(DragonStep.dragon_id == dragon_id).order_by(DragonStep.step_number).all()
    for i, s in enumerate(remaining):
        s.step_number = i + 1
    db.commit()
    sync_steps_count(db, dragon_id)
    return {"ok": True}


# ─── Grid ───

@router.get("/grid")
def get_grid(family_id: int = Query(...), db: Session = Depends(get_db)):
    return db.query(CollectionGrid).filter(CollectionGrid.family_id == family_id).order_by(CollectionGrid.cell_y, CollectionGrid.cell_x).all()


@router.post("/grid/create")
def create_grid(family_id: int = Query(...), columns: int = Query(...), rows: int = Query(...), db: Session = Depends(get_db)):
    db.query(CollectionGrid).filter(CollectionGrid.family_id == family_id).delete(synchronize_session=False)
    for y in range(rows):
        for x in range(columns):
            cell = CollectionGrid(family_id=family_id, cell_x=x, cell_y=y)
            db.add(cell)
    db.commit()
    return {"columns": columns, "rows": rows, "cells": columns * rows}


@router.post("/grid/resize")
def resize_grid(family_id: int = Query(...), columns: int = Query(...), rows: int = Query(...), db: Session = Depends(get_db)):
    cells = db.query(CollectionGrid).filter(CollectionGrid.family_id == family_id).order_by(CollectionGrid.cell_y, CollectionGrid.cell_x).all()
    if columns < 1 or rows < 1:
        raise HTTPException(status_code=400, detail="Min size is 1×1")

    for c in cells:
        if (c.cell_x >= columns or c.cell_y >= rows) and c.dragon_id is not None:
            raise HTTPException(status_code=400,
                detail=f"Нельзя удалить ячейку ({c.cell_x},{c.cell_y}) — в ней дракон. Уберите его сначала.")

    db.query(CollectionGrid).filter(
        CollectionGrid.family_id == family_id,
        (CollectionGrid.cell_x >= columns) | (CollectionGrid.cell_y >= rows)
    ).delete(synchronize_session=False)

    for y in range(rows):
        for x in range(columns):
            exists = db.query(CollectionGrid).filter(
                CollectionGrid.family_id == family_id,
                CollectionGrid.cell_x == x, CollectionGrid.cell_y == y
            ).first()
            if not exists:
                db.add(CollectionGrid(family_id=family_id, cell_x=x, cell_y=y))

    db.commit()
    return {"columns": columns, "rows": rows, "cells": columns * rows}


@router.put("/grid/cell/{cell_id}")
def update_cell(cell_id: int, dragon_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    cell = db.query(CollectionGrid).filter(CollectionGrid.id == cell_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")
    if dragon_id is not None:
        existing = db.query(CollectionGrid).filter(CollectionGrid.dragon_id == dragon_id).first()
        if existing and existing.id != cell_id:
            existing.dragon_id = None
    cell.dragon_id = dragon_id
    db.commit()
    return cell


@router.delete("/grid/cell/{cell_id}")
def clear_cell(cell_id: int, db: Session = Depends(get_db)):
    cell = db.query(CollectionGrid).filter(CollectionGrid.id == cell_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Cell not found")
    cell.dragon_id = None
    db.commit()
    return {"ok": True}



# ─── Families ───

@router.get("/families")
def list_families(db: Session = Depends(get_db)):
    families = db.query(Family).order_by(Family.sort_order, Family.id).all()
    result = []
    for f in families:
        dragon_count = db.query(Dragon).filter(Dragon.family_id == f.id).count()
        result.append({"id": f.id, "name": f.name, "description": f.description, "sort_order": f.sort_order, "color": f.color, "dragon_count": dragon_count})
    return result


@router.post("/families")
async def create_family(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    fam = Family(name=data.get("name", ""), description=data.get("description", ""), sort_order=data.get("sort_order", 0), color=data.get("color", "#9b6fc7"))
    if not fam.name:
        raise HTTPException(status_code=400, detail="Name is required")
    db.add(fam)
    db.commit()
    db.refresh(fam)
    return fam


@router.put("/families/{family_id}")
async def update_family(family_id: int, request: Request, db: Session = Depends(get_db)):
    fam = db.query(Family).filter(Family.id == family_id).first()
    if not fam:
        raise HTTPException(status_code=404, detail="Family not found")
    raw = await request.body()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    if "name" in data: fam.name = data["name"]
    if "description" in data: fam.description = data["description"]
    if "sort_order" in data: fam.sort_order = data["sort_order"]
    if "color" in data: fam.color = data["color"]
    db.commit()
    db.refresh(fam)
    return fam


@router.delete("/families/{family_id}")
def delete_family(family_id: int, db: Session = Depends(get_db)):
    fam = db.query(Family).filter(Family.id == family_id).first()
    if not fam:
        raise HTTPException(status_code=404, detail="Family not found")
    db.delete(fam)
    db.commit()
    return {"ok": True}


# ─── Pins (per-dragon summary) ───

@router.get("/pins")
def list_pins(dragon_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Dragon).filter(Dragon.pin_code != None)
    if dragon_id:
        q = q.filter(Dragon.id == dragon_id)
    return q.order_by(Dragon.id).all()


# ─── Users ───

def _resolve_vk_names(vk_ids: list[int]) -> dict[int, dict]:
    """Batch-resolve VK user names using group token. Returns {vk_id: {first_name, last_name}}."""
    import config
    if not config.VK_GROUP_TOKEN or not vk_ids:
        return {}
    try:
        import vk_api
        vk = vk_api.VkApi(token=config.VK_GROUP_TOKEN, api_version="5.199").get_api()
        ids_str = ",".join(str(x) for x in vk_ids[:1000])
        users = vk.users.get(user_ids=ids_str, fields="first_name,last_name")
        return {
            u["id"]: {
                "first_name": u.get("first_name", ""),
                "last_name": u.get("last_name", ""),
            }
            for u in users
        }
    except Exception:
        return {}


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.registered_at.desc()).limit(200).all()
    vk_names = _resolve_vk_names([u.vk_id for u in users])
    result = []
    for u in users:
        collected = db.query(UserDragon).filter(UserDragon.user_id == u.vk_id).count()
        nm = vk_names.get(u.vk_id, {})
        result.append({
            "vk_id": u.vk_id,
            "first_name": nm.get("first_name", ""),
            "last_name": nm.get("last_name", ""),
            "state": u.state,
            "registered_at": u.registered_at,
            "pins_activated": 0,
            "last_pin_code": None,
            "dragons_collected": collected,
            "current_dragon_id": u.current_dragon_id,
            "current_step": u.current_step,
        })
    return result


@router.get("/users/{vk_id}")
def get_user_detail(vk_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    pins = []

    dragons_list = []
    for d in db.query(Dragon).filter(Dragon.is_active == True).all():
        collected = db.query(UserDragon).filter(UserDragon.user_id == vk_id, UserDragon.dragon_id == d.id).first()
        progress = db.query(UserProgress).filter(
            UserProgress.user_id == vk_id, UserProgress.dragon_id == d.id, UserProgress.completed == True
        ).count()
        if not collected and progress == 0:
            continue
        if collected:
            if collected.completed_at:
                status = "completed"
                pct = 100
            else:
                status = "growing"
                pct = round((progress / max(d.steps_count, 1)) * 100)
        elif progress > 0:
            status = "growing"
            pct = round((progress / max(d.steps_count, 1)) * 100)
        else:
            status = "locked"
            pct = 0
        dragons_list.append({
            "dragon_id": d.id,
            "name": d.name if status == "completed" else None,
            "egg_type": d.egg_type,
            "status": status,
            "progress_pct": pct,
            "completed_at": collected.completed_at if collected else None,
        })

    collected_count = db.query(UserDragon).filter(UserDragon.user_id == vk_id).count()
    vk_nm = _resolve_vk_names([vk_id]).get(vk_id, {})

    return {
        "vk_id": user.vk_id,
        "first_name": vk_nm.get("first_name", ""),
        "last_name": vk_nm.get("last_name", ""),
        "registered_at": user.registered_at,
        "pins_activated": len(pins),
        "pins": pins,
        "dragons": dragons_list,
        "dragons_collected": collected_count,
        "dragons_total": db.query(Dragon).filter(Dragon.is_active == True).count(),
    }


@router.get("/users/{vk_id}/steps")
def get_user_steps(vk_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user or not user.current_dragon_id:
        return {"dragon_name": "", "total": 0, "current_step": 0, "steps": []}

    dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()
    if not dragon:
        return {"dragon_name": "", "total": 0, "current_step": 0, "steps": []}

    steps = db.query(DragonStep).filter(DragonStep.dragon_id == dragon.id).order_by(DragonStep.step_number).all()
    result = []
    for s in steps:
        progress = db.query(UserProgress).filter(
            UserProgress.user_id == vk_id,
            UserProgress.dragon_id == dragon.id,
            UserProgress.step_number == s.step_number,
        ).first()
        result.append({
            "step_number": s.step_number,
            "task_description": s.task_description,
            "magic_action": s.magic_action,
            "hint": s.hint,
            "completed": progress.completed if progress else False,
            "current": s.step_number == user.current_step,
        })
    return {"dragon_name": dragon.name, "total": dragon.steps_count, "current_step": user.current_step, "steps": result}


@router.post("/users/{vk_id}/steps/{step_number}/toggle")
def toggle_user_step(vk_id: int, step_number: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user or not user.current_dragon_id:
        raise HTTPException(status_code=400, detail="No active dragon")

    progress = db.query(UserProgress).filter(
        UserProgress.user_id == vk_id,
        UserProgress.dragon_id == user.current_dragon_id,
        UserProgress.step_number == step_number,
    ).first()

    dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()
    total = dragon.steps_count

    if progress:
        was_completed = progress.completed
        progress.completed = not progress.completed
        if not progress.completed:
            progress.completed_at = ""
    else:
        was_completed = False
        progress = UserProgress(
            user_id=vk_id,
            dragon_id=user.current_dragon_id,
            step_number=step_number,
            completed=True,
            completed_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        )
        db.add(progress)

    # Cascade: marking step N as completed → mark all < N as completed too
    # Cascade: marking step N as incomplete → mark all > N as incomplete too
    db.flush()
    now_ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    if progress.completed and not was_completed:
        for s in range(1, step_number):
            existing = db.query(UserProgress).filter(
                UserProgress.user_id == vk_id,
                UserProgress.dragon_id == user.current_dragon_id,
                UserProgress.step_number == s,
            ).first()
            if existing:
                if not existing.completed:
                    existing.completed = True
                    existing.completed_at = existing.completed_at or now_ts
            else:
                db.add(UserProgress(
                    user_id=vk_id, dragon_id=user.current_dragon_id, step_number=s,
                    completed=True, completed_at=now_ts,
                ))

    elif not progress.completed and was_completed:
        for s in range(step_number + 1, total + 1):
            existing = db.query(UserProgress).filter(
                UserProgress.user_id == vk_id,
                UserProgress.dragon_id == user.current_dragon_id,
                UserProgress.step_number == s,
            ).first()
            if existing and existing.completed:
                existing.completed = False
                existing.completed_at = ""

    db.flush()

    # Сброс таймаута при ручном изменении шага админом
    ud_toggle = db.query(UserDragon).filter(
        UserDragon.user_id == vk_id, UserDragon.dragon_id == user.current_dragon_id
    ).first()
    if ud_toggle:
        ud_toggle.next_step_available_at = None
        ud_toggle.timeout_notified = False

    completed_count = db.query(UserProgress).filter(
        UserProgress.user_id == vk_id,
        UserProgress.dragon_id == user.current_dragon_id,
        UserProgress.completed == True,
    ).count()

    if completed_count >= total:
        ud = db.query(UserDragon).filter(UserDragon.user_id == vk_id, UserDragon.dragon_id == user.current_dragon_id).first()
        if ud and not ud.completed_at:
            ud.completed_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        user.state = "idle"
        user.current_dragon_id = None
        user.current_step = 0

        msg = (
            f"🎉 Поздравляю! Ты вырастил дракона!\n\n"
            f"⭐ {dragon.name} ⭐\n"
            f"Редкость: {'⭐' * dragon.rarity}\n"
        )
        if dragon.description:
            msg += f"\n{dragon.description}\n"
        msg += "\nЗагляни в мини-приложение, чтобы увидеть его в своей коллекции!"

        attachment = ""
        if dragon.dragon_path:
            img_path = os.path.join(os.path.dirname(__file__), "..", "..", "images", "dragons", os.path.basename(dragon.dragon_path))
            attachment = _upload_vk_image(os.path.abspath(img_path))

        _notify_user(vk_id, msg, attachment)
    else:
        user.current_step = completed_count + 1
        user.state = f"grow_step_{user.current_step}"
        step_def = db.query(DragonStep).filter(
            DragonStep.dragon_id == user.current_dragon_id,
            DragonStep.step_number == user.current_step,
        ).first()
        steps_msg = _format_step_text(step_def, user.current_step, total)
        header = f"🥚 {dragon.name}\n"
        instruction = "\nПришли 2 фото (до и после) и напиши «вышито» когда выполнишь."
        if progress.completed:
            _notify_user(vk_id, f"{header}✅ Администратор отметил шаг {step_number} как выполненный.\n\n{steps_msg}{instruction}")
        else:
            _notify_user(vk_id, f"{header}↩ Администратор отменил шаг {step_number}.\n\n{steps_msg}{instruction}")

    db.commit()
    return {"ok": True, "completed": progress.completed, "current_step": user.current_step}


def _notify_user(vk_id: int, message: str, attachment: str = ""):
    """Send a notification message to user via VK bot."""
    try:
        import config
        import random
        if not config.VK_GROUP_TOKEN:
            return
        import vk_api
        vk = vk_api.VkApi(token=config.VK_GROUP_TOKEN, api_version="5.199").get_api()
        kwargs = {
            "user_id": vk_id,
            "message": message,
            "random_id": random.randint(1, 2**31 - 1),
        }
        if attachment:
            kwargs["attachment"] = attachment
        vk.messages.send(**kwargs)
    except Exception:
        pass


def _upload_vk_image(filepath: str) -> str:
    """Upload local image to VK and return attachment string."""
    import config
    if not config.VK_GROUP_TOKEN or not filepath or not os.path.isfile(filepath):
        return ""
    try:
        import importlib
        import vk_api
        import requests
        vk = vk_api.VkApi(token=config.VK_GROUP_TOKEN, api_version="5.199").get_api()
        upload_url = vk.photos.getMessagesUploadServer(peer_id=0)["upload_url"]
        with open(filepath, "rb") as f:
            resp = requests.post(upload_url, files={"photo": ("image.jpg", f, "image/jpeg")}).json()
        saved = vk.photos.saveMessagesPhoto(photo=resp["photo"], server=resp["server"], hash=resp["hash"])[0]
        return f"photo{saved['owner_id']}_{saved['id']}"
    except Exception:
        return ""


def _format_step_text(step_def, step_num: int, total: int) -> str:
    if not step_def:
        return f"📋 Шаг {step_num} из {total}"
    lines = [f"📋 Шаг {step_num} из {total}"]
    if step_def.magic_action:
        lines.append(f"✨ {step_def.magic_action}")
    if step_def.task_description:
        lines.append(f"📝 {step_def.task_description}")
    if step_def.hint:
        lines.append(f"💡 {step_def.hint}")
    return "\n".join(lines)


@router.post("/users/{vk_id}/skip-step")
def skip_step(vk_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.current_dragon_id:
        raise HTTPException(status_code=400, detail="No active dragon — игрок сейчас не выращивает дракона")

    dragon = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first()
    if not dragon:
        raise HTTPException(status_code=400, detail="Dragon not found")

    total = dragon.steps_count

    existing = db.query(UserProgress).filter(
        UserProgress.user_id == vk_id,
        UserProgress.dragon_id == user.current_dragon_id,
        UserProgress.step_number == user.current_step,
    ).first()
    if not existing:
        up = UserProgress(user_id=vk_id, dragon_id=user.current_dragon_id, step_number=user.current_step, completed=True)
        db.add(up)

    ud = db.query(UserDragon).filter(UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon.id).first()
    if ud:
        ud.next_step_available_at = None
        ud.timeout_notified = False

    if user.current_step >= total:
        if ud and not ud.completed_at:
            ud.completed_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        user.state = "idle"
        user.current_dragon_id = None
        user.current_step = 0
    else:
        user.current_step += 1
        user.state = f"grow_step_{user.current_step}"

    db.commit()
    return {"ok": True, "new_step": user.current_step}


@router.post("/users/{vk_id}/reset-dragon")
def reset_dragon(vk_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.current_dragon_id:
        raise HTTPException(status_code=400, detail="No active dragon — игрок сейчас не выращивает дракона")

    dragon_name = db.query(Dragon).filter(Dragon.id == user.current_dragon_id).first().name
    ud = db.query(UserDragon).filter(
        UserDragon.user_id == vk_id, UserDragon.dragon_id == user.current_dragon_id
    ).first()
    if ud:
        ud.next_step_available_at = None
        ud.timeout_notified = False
    db.query(UserProgress).filter(
        UserProgress.user_id == vk_id, UserProgress.dragon_id == user.current_dragon_id
    ).delete()
    user.current_dragon_id = None
    user.current_step = 0
    user.state = "idle"
    user.state_data = "{}"
    db.commit()
    _notify_user(vk_id, f"🔄 Администратор сбросил прогресс выращивания дракона «{dragon_name}». Дракон остался в твоём бестиарии — нажми «🔄 Сменить дракона» чтобы переключиться на него и начать заново.")
    return {"ok": True}


@router.post("/users/{vk_id}/dragons/{dragon_id}/restart")
def restart_dragon(vk_id: int, dragon_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    dragon = db.query(Dragon).filter(Dragon.id == dragon_id).first()
    if not dragon:
        raise HTTPException(status_code=404, detail="Dragon not found")

    ud = db.query(UserDragon).filter(UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon_id).first()
    if not ud:
        raise HTTPException(status_code=400, detail="У игрока нет этого дракона")

    db.query(UserProgress).filter(
        UserProgress.user_id == vk_id, UserProgress.dragon_id == dragon_id
    ).delete()

    ud.next_step_available_at = None
    ud.timeout_notified = False

    if ud.completed_at:
        ud.completed_at = ""

    user.current_dragon_id = dragon_id
    user.current_step = 1
    user.state = "grow_step_1"
    user.state_data = "{}"
    db.commit()

    total = dragon.steps_count
    first_step = db.query(DragonStep).filter(DragonStep.dragon_id == dragon_id, DragonStep.step_number == 1).first()
    steps_msg = _format_step_text(first_step, 1, total)
    _notify_user(vk_id, f"🔄 Администратор возобновил выращивание дракона «{dragon.name}»!\n\n{steps_msg}\n\nПришли 2 фото (до и после) и напиши «вышито» когда выполнишь.")
    return {"ok": True}


@router.delete("/users/{vk_id}/dragons/{dragon_id}")
def delete_user_dragon(vk_id: int, dragon_id: int, db: Session = Depends(get_db)):
    ud = db.query(UserDragon).filter(UserDragon.user_id == vk_id, UserDragon.dragon_id == dragon_id).first()
    if not ud:
        raise HTTPException(status_code=404, detail="Dragon not found for this user")

    db.query(UserProgress).filter(
        UserProgress.user_id == vk_id, UserProgress.dragon_id == dragon_id
    ).delete(synchronize_session=False)

    user = db.query(User).filter(User.vk_id == vk_id).first()
    if user and user.current_dragon_id == dragon_id:
        user.current_dragon_id = None
        user.current_step = 0
        user.state = "idle"

    db.delete(ud)
    db.commit()
    return {"ok": True}


@router.get("/logs")
def list_logs(page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    offset = (page - 1) * per_page
    total = db.query(ErrorLog).count()
    logs = db.query(ErrorLog).order_by(ErrorLog.id.desc()).offset(offset).limit(per_page).all()
    return {"logs": logs, "total": total, "page": page, "per_page": per_page}


@router.get("/logs/api")
def list_api_logs(page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200)):
    if not os.path.isfile(API_ERROR_LOG):
        return {"lines": [], "total": 0, "page": page, "per_page": per_page}
    try:
        with open(API_ERROR_LOG, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
    except Exception:
        return {"lines": [], "total": 0, "page": page, "per_page": per_page}
    all_lines.reverse()
    total = len(all_lines)
    offset = (page - 1) * per_page
    chunk = all_lines[offset:offset + per_page]
    return {"lines": chunk, "total": total, "page": page, "per_page": per_page}


@router.get("/logs/api-requests")
def list_api_requests(page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    offset = (page - 1) * per_page
    total = db.query(ApiRequestLog).count()
    items = db.query(ApiRequestLog).order_by(ApiRequestLog.id.desc()).offset(offset).limit(per_page).all()
    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/health")
def get_health(db: Session = Depends(get_db)):
    now = datetime.now()
    services = {}

    for name in ("bot",):
        hb = db.query(ServiceHeartbeat).filter(ServiceHeartbeat.service_name == name).first()
        if hb and hb.last_seen:
            try:
                last = datetime.fromisoformat(hb.last_seen)
                online = (now - last).total_seconds() < 90
                services[name] = {"status": "online" if online else "offline", "last_seen": hb.last_seen}
            except ValueError:
                services[name] = {"status": "unknown", "last_seen": hb.last_seen}
        else:
            services[name] = {"status": "unknown", "last_seen": None}

    return {"services": services, "checked_at": now.isoformat()}
