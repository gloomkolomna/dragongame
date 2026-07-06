import json
from datetime import datetime, timedelta
from models import Dragon, DragonStep, User, UserDragon, UserProgress


def _create_dragon(client, name="TestDragon"):
    return client.post(
        "/api/admin/dragons",
        data={
            "name": name, "rarity": 2, "egg_type": "blue",
            "description": "A test dragon", "family_id": 1,
        },
    )


def _create_family(client):
    return client.post(
        "/api/admin/families",
        data={"name": "TestFamily", "color": "#ff0000"},
    )


def test_health(client):
    resp = client.get("/api/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_dragons_empty(client):
    resp = client.get("/api/admin/dragons")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_dragon_with_steps_timeout(client):
    fam = _create_family(client)
    family_id = fam.json()["id"]

    steps_data = [
        {"step_number": 1, "magic_action": "Step 1", "timeout_hours": 2, "timeout_minutes": 30},
        {"step_number": 2, "magic_action": "Step 2", "timeout_hours": 0, "timeout_minutes": 0},
        {"step_number": 3, "magic_action": "Step 3", "timeout_hours": 0, "timeout_minutes": 15},
    ]
    resp = client.post(
        "/api/admin/dragons",
        data={
            "name": "TimeoutDragon", "rarity": 3, "egg_type": "ice",
            "description": "", "family_id": family_id,
            "steps": json.dumps(steps_data),
        },
    )
    assert resp.status_code == 200
    dragon_id = resp.json()["id"]

    steps_resp = client.get(f"/api/admin/dragons/{dragon_id}/steps")
    assert steps_resp.status_code == 200
    steps = steps_resp.json()
    assert len(steps) == 3

    step1 = next(s for s in steps if s["step_number"] == 1)
    assert step1["timeout_hours"] == 2
    assert step1["timeout_minutes"] == 30

    step2 = next(s for s in steps if s["step_number"] == 2)
    assert step2["timeout_hours"] == 0
    assert step2["timeout_minutes"] == 0

    step3 = next(s for s in steps if s["step_number"] == 3)
    assert step3["timeout_hours"] == 0
    assert step3["timeout_minutes"] == 15


def test_save_steps_with_timeout(client):
    fam = _create_family(client)
    dragon_resp = client.post(
        "/api/admin/dragons",
        data={"name": "D", "rarity": 1, "egg_type": "e", "description": "", "family_id": fam.json()["id"]},
    )
    dragon_id = dragon_resp.json()["id"]

    resp = client.put(
        f"/api/admin/dragons/{dragon_id}/steps",
        json={
            "steps": [
                {"id": 0, "step_number": 1, "magic_action": "M1", "timeout_hours": 5, "timeout_minutes": 0},
                {"id": 0, "step_number": 2, "magic_action": "M2", "timeout_hours": 1, "timeout_minutes": 15},
            ],
        },
    )
    assert resp.status_code == 200

    steps_resp = client.get(f"/api/admin/dragons/{dragon_id}/steps")
    steps = steps_resp.json()
    assert len(steps) == 2
    assert steps[0]["timeout_hours"] == 5
    assert steps[0]["timeout_minutes"] == 0
    assert steps[1]["timeout_hours"] == 1
    assert steps[1]["timeout_minutes"] == 15


def test_add_step_with_default_timeout(client):
    fam = _create_family(client)
    dragon_resp = client.post(
        "/api/admin/dragons",
        data={"name": "D", "rarity": 1, "egg_type": "e", "description": "", "family_id": fam.json()["id"]},
    )
    dragon_id = dragon_resp.json()["id"]

    # First add a step via PUT to have at least one step
    put_resp = client.put(
        f"/api/admin/dragons/{dragon_id}/steps",
        json={"steps": [{"id": 0, "step_number": 1, "magic_action": "M1", "timeout_hours": 2, "timeout_minutes": 30}]},
    )
    assert put_resp.status_code == 200

    # Now add another step via POST
    resp = client.post(f"/api/admin/dragons/{dragon_id}/steps")
    assert resp.status_code == 200

    steps_resp = client.get(f"/api/admin/dragons/{dragon_id}/steps")
    steps = steps_resp.json()
    assert len(steps) == 2
    assert steps[0]["timeout_hours"] == 2
    assert steps[0]["timeout_minutes"] == 30
    assert steps[1]["timeout_hours"] == 1
    assert steps[1]["timeout_minutes"] == 0


def test_skip_step_clears_timeout(client, db):
    fam = _create_family(client)
    dragon_resp = client.post(
        "/api/admin/dragons",
        data={"name": "D", "rarity": 1, "egg_type": "e", "description": "", "family_id": fam.json()["id"]},
    )
    dragon_id = dragon_resp.json()["id"]

    client.put(
        f"/api/admin/dragons/{dragon_id}/steps",
        json={"steps": [{"id": 0, "step_number": 1, "magic_action": "M1"}]},
    )

    user = User(vk_id=100, state="grow_step_1", current_dragon_id=dragon_id, current_step=1)
    db.add(user)
    ud = UserDragon(
        user_id=100, dragon_id=dragon_id,
        next_step_available_at="2026-07-04T12:00:00",
        timeout_notified=True,
    )
    db.add(ud)
    db.commit()

    resp = client.post(f"/api/admin/users/100/skip-step")
    assert resp.status_code == 200

    db.refresh(ud)
    assert ud.next_step_available_at is None
    assert ud.timeout_notified is False


def test_reset_dragon_clears_timeout(client, db):
    fam = _create_family(client)
    dragon_resp = client.post(
        "/api/admin/dragons",
        data={"name": "D", "rarity": 1, "egg_type": "e", "description": "", "family_id": fam.json()["id"]},
    )
    dragon_id = dragon_resp.json()["id"]

    client.put(
        f"/api/admin/dragons/{dragon_id}/steps",
        json={"steps": [{"id": 0, "step_number": 1, "magic_action": "M1"}]},
    )

    user = User(vk_id=101, state="grow_step_1", current_dragon_id=dragon_id, current_step=1)
    db.add(user)
    ud = UserDragon(
        user_id=101, dragon_id=dragon_id,
        next_step_available_at="2026-07-04T12:00:00",
        timeout_notified=True,
    )
    db.add(ud)
    db.commit()

    resp = client.post("/api/admin/users/101/reset-dragon")
    assert resp.status_code == 200

    db.refresh(ud)
    assert ud.next_step_available_at is None
    assert ud.timeout_notified is False


def test_restart_dragon_clears_timeout(client, db):
    fam = _create_family(client)
    dragon_resp = client.post(
        "/api/admin/dragons",
        data={"name": "D", "rarity": 1, "egg_type": "e", "description": "", "family_id": fam.json()["id"]},
    )
    dragon_id = dragon_resp.json()["id"]

    client.put(
        f"/api/admin/dragons/{dragon_id}/steps",
        json={"steps": [{"id": 0, "step_number": 1, "magic_action": "M1"}]},
    )

    user = User(vk_id=102, state="grow_step_1", current_dragon_id=dragon_id, current_step=1)
    db.add(user)
    ud = UserDragon(
        user_id=102, dragon_id=dragon_id,
        next_step_available_at="2026-07-04T12:00:00",
        timeout_notified=True,
    )
    db.add(ud)
    db.commit()

    resp = client.post(f"/api/admin/users/102/dragons/{dragon_id}/restart")
    assert resp.status_code == 200

    db.refresh(ud)
    assert ud.next_step_available_at is None
    assert ud.timeout_notified is False


def test_toggle_step_clears_timeout(client, db):
    fam = _create_family(client)
    dragon_resp = client.post(
        "/api/admin/dragons",
        data={"name": "D", "rarity": 1, "egg_type": "e", "description": "", "family_id": fam.json()["id"]},
    )
    dragon_id = dragon_resp.json()["id"]

    client.put(
        f"/api/admin/dragons/{dragon_id}/steps",
        json={"steps": [{"id": 0, "step_number": 1, "magic_action": "M1"}]},
    )

    user = User(vk_id=103, state="grow_step_1", current_dragon_id=dragon_id, current_step=1)
    db.add(user)
    ud = UserDragon(
        user_id=103, dragon_id=dragon_id,
        next_step_available_at="2026-07-04T12:00:00",
        timeout_notified=True,
    )
    db.add(ud)
    db.commit()

    resp = client.post("/api/admin/users/103/steps/1/toggle")
    assert resp.status_code == 200

    db.refresh(ud)
    assert ud.next_step_available_at is None
    assert ud.timeout_notified is False


def test_get_user_steps_shows_timeout(client, db):
    fam = _create_family(client)
    dragon_resp = client.post(
        "/api/admin/dragons",
        data={"name": "D", "rarity": 1, "egg_type": "e", "description": "", "family_id": fam.json()["id"]},
    )
    dragon_id = dragon_resp.json()["id"]

    client.put(
        f"/api/admin/dragons/{dragon_id}/steps",
        json={"steps": [
            {"id": 0, "step_number": 1, "magic_action": "M1", "timeout_hours": 3, "timeout_minutes": 0},
        ]},
    )

    user = User(vk_id=104, state="grow_step_1", current_dragon_id=dragon_id, current_step=1)
    db.add(user)
    db.commit()

    resp = client.get(f"/api/admin/users/104/steps")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1


def test_get_user_detail_empty(client, db):
    user = User(vk_id=201, state="idle")
    db.add(user)
    db.commit()
    resp = client.get("/api/admin/users/201")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dragons"] == []


def test_get_user_detail_growing(client, db):
    fam = _create_family(client)
    steps_data = [
        {"step_number": 1, "magic_action": "S1", "timeout_hours": 0, "timeout_minutes": 0},
        {"step_number": 2, "magic_action": "S2", "timeout_hours": 0, "timeout_minutes": 0},
    ]
    dragon_resp = client.post(
        "/api/admin/dragons",
        data={
            "name": "D", "rarity": 1, "egg_type": "e", "description": "",
            "family_id": fam.json()["id"], "steps": json.dumps(steps_data),
        },
    )
    dragon_id = dragon_resp.json()["id"]

    user = User(vk_id=202, state="grow_step_2", current_dragon_id=dragon_id, current_step=2)
    db.add(user)
    ud = UserDragon(user_id=202, dragon_id=dragon_id, completed_at="")
    db.add(ud)
    up = UserProgress(user_id=202, dragon_id=dragon_id, step_number=1, completed=True)
    db.add(up)
    db.commit()

    resp = client.get("/api/admin/users/202")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["dragons"]) == 1
    d = data["dragons"][0]
    assert d["status"] == "growing"
    assert d["progress_pct"] == 50


def test_get_user_detail_completed(client, db):
    fam = _create_family(client)
    dragon_resp = client.post(
        "/api/admin/dragons",
        data={"name": "D", "rarity": 1, "egg_type": "e", "description": "", "family_id": fam.json()["id"]},
    )
    dragon_id = dragon_resp.json()["id"]

    user = User(vk_id=203, state="idle")
    db.add(user)
    ud = UserDragon(user_id=203, dragon_id=dragon_id, completed_at="2026-01-01T00:00:00")
    db.add(ud)
    db.commit()

    resp = client.get("/api/admin/users/203")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["dragons"]) == 1
    d = data["dragons"][0]
    assert d["status"] == "completed"
    assert d["progress_pct"] == 100


def test_get_user_detail_excludes_locked(client, db):
    fam = _create_family(client)
    dragon_resp = client.post(
        "/api/admin/dragons",
        data={"name": "D", "rarity": 1, "egg_type": "e", "description": "", "family_id": fam.json()["id"]},
    )
    dragon_id = dragon_resp.json()["id"]

    user = User(vk_id=204, state="idle")
    db.add(user)
    db.commit()

    resp = client.get("/api/admin/users/204")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["dragons"]) == 0
