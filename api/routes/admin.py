import json
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from db import get_db
from auth import get_current_admin
from models import Dragon, DragonStep, User, UserDragon, CollectionGrid, UserProgress, Family
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
    family_id: Optional[int] = Form(None),
    image: Optional[UploadFile] = File(None),
    silhouette: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    return create_dragon(db, name, rarity, egg_type, description, family_id, image, silhouette)


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
    db: Session = Depends(get_db),
):
    dragon = update_dragon(db, dragon_id, name, rarity, egg_type, description,
                           is_active, family_id, image, silhouette)
    if not dragon:
        raise HTTPException(status_code=404, detail="Dragon not found")
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
    for s in steps_data:
        sid = s.get("id", 0)
        if sid == 0:
            step = DragonStep(dragon_id=dragon_id, step_number=s.get("step_number", 0),
                              magic_action=s.get("magic_action", ""),
                              task_description=s.get("task_description", ""),
                              hint=s.get("hint", ""), keyword="вышито")
            db.add(step)
        else:
            step = db.query(DragonStep).filter(DragonStep.id == sid, DragonStep.dragon_id == dragon_id).first()
            if step:
                step.step_number = s.get("step_number", step.step_number)
                step.magic_action = s.get("magic_action", step.magic_action)
                step.task_description = s.get("task_description", step.task_description)
                step.hint = s.get("hint", step.hint)
                step.keyword = "вышито"
    db.commit()
    sync_steps_count(db, dragon_id)
    return {"ok": True, "saved": len(steps_data)}


@router.post("/dragons/{dragon_id}/steps")
def add_step(dragon_id: int, db: Session = Depends(get_db)):
    dragon = get_dragon(db, dragon_id)
    if not dragon:
        raise HTTPException(status_code=404, detail="Dragon not found")
    max_number = db.query(DragonStep).filter(DragonStep.dragon_id == dragon_id).count()
    step = DragonStep(dragon_id=dragon_id, step_number=max_number + 1, magic_action="", task_description="", hint="")
    db.add(step)
    db.commit()
    db.refresh(step)
    sync_steps_count(db, dragon_id)
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
    db.query(CollectionGrid).filter(CollectionGrid.family_id == family_id).delete()
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
        result.append({"id": f.id, "name": f.name, "description": f.description, "sort_order": f.sort_order, "dragon_count": dragon_count})
    return result


@router.post("/families")
async def create_family(request: Request, db: Session = Depends(get_db)):
    raw = await request.body()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    fam = Family(name=data.get("name", ""), description=data.get("description", ""), sort_order=data.get("sort_order", 0))
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

@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.registered_at.desc()).limit(200).all()
    result = []
    for u in users:
        collected = db.query(UserDragon).filter(UserDragon.user_id == u.vk_id).count()
        result.append({
            "vk_id": u.vk_id,
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
        if collected:
            status = "completed"
            pct = 100
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

    return {
        "vk_id": user.vk_id,
        "registered_at": user.registered_at,
        "pins_activated": len(pins),
        "pins": pins,
        "dragons": dragons_list,
        "dragons_collected": collected_count,
        "dragons_total": db.query(Dragon).filter(Dragon.is_active == True).count(),
    }


@router.post("/users/{vk_id}/skip-step")
def skip_step(vk_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user or not user.current_dragon_id:
        raise HTTPException(status_code=400, detail="No active dragon")
    user.current_step += 1
    db.commit()
    return {"ok": True}


@router.post("/users/{vk_id}/reset-dragon")
def reset_dragon(vk_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.vk_id == vk_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.current_dragon_id:
        db.query(UserProgress).filter(
            UserProgress.user_id == vk_id, UserProgress.dragon_id == user.current_dragon_id
        ).delete()
    user.current_dragon_id = None
    user.current_step = 0
    user.state = "idle"
    db.commit()
    return {"ok": True}
