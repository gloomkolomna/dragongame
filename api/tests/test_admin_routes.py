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


# ─── Phase 0: shop items ───

def test_shop_item_crud(client):
    resp = client.post("/api/admin/shop-items", json={"name": "Смесь", "cost_stitches": 500, "category": "food"})
    assert resp.status_code == 200
    item_id = resp.json()["id"]
    assert resp.json()["cost_stitches"] == 500

    lst = client.get("/api/admin/shop-items")
    assert len(lst.json()) == 1

    upd = client.put(f"/api/admin/shop-items/{item_id}", json={"cost_stitches": 700})
    assert upd.json()["cost_stitches"] == 700

    dele = client.delete(f"/api/admin/shop-items/{item_id}")
    assert dele.status_code == 200
    assert client.get("/api/admin/shop-items").json() == []


def test_shop_item_requires_name(client):
    resp = client.post("/api/admin/shop-items", json={"cost_stitches": 100})
    assert resp.status_code == 400


# ─── Phase 0: stage ↔ shop item ───

def test_stage_shop_item_binding(client):
    item = client.post("/api/admin/shop-items", json={"name": "Ванночка", "cost_stitches": 200}).json()
    resp = client.post("/api/admin/stage-shop-items", json={"stage_key": "epic:1", "item_id": item["id"]})
    assert resp.status_code == 200
    link_id = resp.json()["id"]

    lst = client.get("/api/admin/stage-shop-items", params={"stage_key": "epic:1"})
    assert len(lst.json()) == 1

    # duplicate binding rejected
    dup = client.post("/api/admin/stage-shop-items", json={"stage_key": "epic:1", "item_id": item["id"]})
    assert dup.status_code == 400

    dele = client.delete(f"/api/admin/stage-shop-items/{link_id}")
    assert dele.status_code == 200


# ─── Phase 0: epic species + stages (common) ───

def test_epic_species_list(client):
    fam = _create_family(client)
    client.post("/api/admin/dragons", data={"name": "Обычный", "rarity": 1, "family_id": fam.json()["id"]})
    client.post("/api/admin/dragons", data={"name": "Эпик", "rarity": 1, "family_id": fam.json()["id"], "is_epic": True})
    species = client.get("/api/admin/epic/species").json()
    assert len(species) == 1
    assert species[0]["name"] == "Эпик"
    assert species[0]["is_epic"] is True


def test_create_epic_species_without_family(client):
    resp = client.post("/api/admin/dragons", data={"name": "Туманокрыл", "rarity": 1, "is_epic": True})
    assert resp.status_code == 200
    assert resp.json()["is_epic"] is True
    assert resp.json()["family_id"] is None


def test_create_normal_dragon_without_family_ok_on_backend(client):
    resp = client.post("/api/admin/dragons", data={"name": "NoFam", "rarity": 1})
    assert resp.status_code == 200
    assert resp.json()["family_id"] is None


def test_epic_stage_crud(client):
    resp = client.post("/api/admin/epic/stages", json={"stage_number": 1, "name": "Вылупленное чудо", "cycles_count": 3, "image_start": "dragons/s1.png", "image_end": "dragons/s1_end.png"})
    assert resp.status_code == 200
    stage_id = resp.json()["id"]
    assert resp.json()["care_timeout_hours"] == 24
    assert resp.json()["image_start"] == "dragons/s1.png"
    assert resp.json()["image_end"] == "dragons/s1_end.png"

    upd = client.put(f"/api/admin/epic/stages/{stage_id}", json={"care_timeout_hours": 12})
    assert upd.json()["care_timeout_hours"] == 12

    assert len(client.get("/api/admin/epic/stages").json()) == 1
    assert client.delete(f"/api/admin/epic/stages/{stage_id}").status_code == 200


def test_epic_stage_action_crud(client):
    stage = client.post("/api/admin/epic/stages", json={"stage_number": 1, "name": "S1"}).json()
    item = client.post("/api/admin/shop-items", json={"name": "Смесь", "cost_stitches": 100}).json()
    resp = client.post(f"/api/admin/epic/stages/{stage['id']}/actions",
                       json={"action_label": "Кормить", "order_in_cycle": 1, "crosses_norm": 300, "item_ids": [item["id"]]})
    assert resp.status_code == 200
    action_id = resp.json()["id"]
    assert resp.json()["crosses_norm"] == 300
    assert resp.json()["item_ids"] == [item["id"]]

    lst = client.get(f"/api/admin/epic/stages/{stage['id']}/actions")
    assert len(lst.json()) == 1

    upd = client.put(f"/api/admin/epic/actions/{action_id}", json={"action_label": "Покормить", "crosses_norm": 500, "item_ids": []})
    assert upd.json()["action_label"] == "Покормить"
    assert upd.json()["crosses_norm"] == 500
    assert upd.json()["item_ids"] == []
    assert client.delete(f"/api/admin/epic/actions/{action_id}").status_code == 200


def test_shop_item_character_effect(client):
    r = client.post("/api/admin/shop-items", json={"name": "Меч", "cost_stitches": 400, "character_effect": "смелый"})
    assert r.status_code == 200
    item_id = r.json()["id"]
    assert r.json()["character_effect"] == "смелый"
    upd = client.put(f"/api/admin/shop-items/{item_id}", json={"character_effect": "храбрый"})
    assert upd.json()["character_effect"] == "храбрый"


def test_stage_shop_binding_synced_from_care_action(client):
    stage = client.post("/api/admin/epic/stages", json={"stage_number": 2, "name": "S2"}).json()
    item1 = client.post("/api/admin/shop-items", json={"name": "Смесь", "cost_stitches": 100}).json()
    item2 = client.post("/api/admin/shop-items", json={"name": "Ванночка", "cost_stitches": 150}).json()

    # care action with multiple items → bindings auto-created for epic:2
    act = client.post(f"/api/admin/epic/stages/{stage['id']}/actions",
                      json={"action_label": "Кормить", "item_ids": [item1["id"], item2["id"]], "order_in_cycle": 1}).json()
    assert sorted(act["item_ids"]) == sorted([item1["id"], item2["id"]])
    links = client.get("/api/admin/stage-shop-items", params={"stage_key": "epic:2"}).json()
    assert {l["item_id"] for l in links} == {item1["id"], item2["id"]}

    # deleting the action → bindings auto-removed
    client.delete(f"/api/admin/epic/actions/{act['id']}")
    links2 = client.get("/api/admin/stage-shop-items", params={"stage_key": "epic:2"}).json()
    assert len(links2) == 0


# ─── Phase 0: legend fragments (phase=1) ───

def test_legend_fragments_isolated_from_egg_steps(client):
    fam = _create_family(client)
    steps_data = [{"step_number": 1, "magic_action": "Egg step 1"}]
    dragon = client.post("/api/admin/dragons", data={
        "name": "Legendary", "rarity": 3, "family_id": fam.json()["id"],
        "steps": json.dumps(steps_data),
    }).json()
    dragon_id = dragon["id"]

    # save legend fragments (phase=1)
    resp = client.put(f"/api/admin/dragons/{dragon_id}/legend", json={
        "legend_image_path": "dragons/cover.png",
        "fragments": [
            {"id": 0, "task_description": "Отрывок 1", "crosses_norm": 500},
            {"id": 0, "task_description": "Отрывок 2", "crosses_norm": 600},
        ],
    })
    assert resp.status_code == 200

    legend = client.get(f"/api/admin/dragons/{dragon_id}/legend").json()
    assert legend["legend_image_path"] == "dragons/cover.png"
    assert len(legend["fragments"]) == 2

    # egg steps must remain untouched (steps_count still 1, only phase=0)
    egg_steps = client.get(f"/api/admin/dragons/{dragon_id}/steps").json()
    assert len(egg_steps) == 1
    assert egg_steps[0]["magic_action"] == "Egg step 1"


# ─── Phase 0: suspicious reports + balance ───

def test_suspicious_list_and_balance(client, db):
    from models import SuspiciousReport
    user = User(vk_id=777, stitches_balance=1000)
    db.add(user)
    db.add(SuspiciousReport(user_id=777, dragon_id=None, step_number=1,
                            declared_crosses=9000, normal_crosses=500, mode="norm", status="pending"))
    db.commit()

    lst = client.get("/api/admin/suspicious").json()
    assert len(lst) == 1
    assert lst[0]["declared_crosses"] == 9000

    # manual balance adjust by delta (clamped at 0)
    resp = client.post("/api/admin/users/777/balance", json={"delta": -8500})
    assert resp.status_code == 200
    assert resp.json()["stitches_balance"] == 0

    # set absolute
    resp2 = client.post("/api/admin/users/777/balance", json={"balance": 250})
    assert resp2.json()["stitches_balance"] == 250


def test_user_detail_shows_balance(client, db):
    user = User(vk_id=778, state="idle", stitches_balance=333)
    db.add(user)
    db.commit()
    data = client.get("/api/admin/users/778").json()
    assert data["stitches_balance"] == 333
    assert data["epic_unlocked"] is False


def test_user_detail_includes_own_suspicious(client, db):
    from models import SuspiciousReport
    db.add(User(vk_id=790, state="idle"))
    db.add(User(vk_id=791, state="idle"))
    db.add(SuspiciousReport(user_id=790, step_number=1, declared_crosses=9000,
                            normal_crosses=1000, mode="norm", status="pending"))
    db.add(SuspiciousReport(user_id=791, step_number=1, declared_crosses=9000,
                            normal_crosses=1000, mode="norm", status="pending"))
    db.commit()
    data = client.get("/api/admin/users/790").json()
    assert len(data["suspicious_reports"]) == 1
    assert data["suspicious_reports"][0]["declared_crosses"] == 9000


def test_suspicious_delete(client, db):
    from models import SuspiciousReport
    db.add(User(vk_id=779, stitches_balance=0))
    r = SuspiciousReport(user_id=779, dragon_id=None, step_number=2,
                         declared_crosses=8000, normal_crosses=1000, mode="norm", status="pending")
    db.add(r)
    db.commit()
    rid = r.id

    resp = client.delete(f"/api/admin/suspicious/{rid}")
    assert resp.status_code == 200
    assert client.get("/api/admin/suspicious").json() == []

    assert client.delete(f"/api/admin/suspicious/{rid}").status_code == 404


def test_users_list_suspicious_pending_count(client, db):
    from models import SuspiciousReport
    db.add(User(vk_id=780, state="idle", registered_at="2026-01-01T00:00:00"))
    db.add(User(vk_id=781, state="idle", registered_at="2026-01-02T00:00:00"))
    db.add(SuspiciousReport(user_id=780, step_number=1, declared_crosses=9000,
                            normal_crosses=1000, mode="norm", status="pending"))
    db.add(SuspiciousReport(user_id=780, step_number=2, declared_crosses=9000,
                            normal_crosses=1000, mode="norm", status="pending"))
    db.commit()

    rows = {u["vk_id"]: u for u in client.get("/api/admin/users").json()}
    assert rows[780]["suspicious_pending"] == 2
    assert rows[781]["suspicious_pending"] == 0


def test_suspicious_recent_feed(client, db):
    from models import SuspiciousReport
    db.add(User(vk_id=782, state="idle"))
    db.add(SuspiciousReport(user_id=782, step_number=3, declared_crosses=9000,
                            normal_crosses=1000, mode="norm", status="pending"))
    db.add(SuspiciousReport(user_id=782, step_number=4, declared_crosses=7000,
                            normal_crosses=1000, mode="norm", status="resolved"))
    db.commit()

    data = client.get("/api/admin/suspicious/recent").json()
    assert data["total_pending"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["user_id"] == 782
    assert item["declared_crosses"] == 9000
    assert item["name"]


def test_suspicious_detailed_returns_message_and_chat(client, db):
    from models import SuspiciousReport
    db.add(User(vk_id=783, state="idle"))
    db.add(SuspiciousReport(user_id=783, step_number=1, declared_crosses=9000,
                            normal_crosses=1000, mode="norm", status="pending",
                            raw_message="вышито 9000 круто"))
    db.commit()

    data = client.get("/api/admin/suspicious/detailed").json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["user_id"] == 783
    assert item["message"] == "вышито 9000 круто"
    assert str(item["user_id"]) in item["chat_url"]
    assert item["name"]


def test_stats_includes_suspicious_total(client, db):
    from models import SuspiciousReport
    db.add(User(vk_id=784, state="idle"))
    db.add(SuspiciousReport(user_id=784, step_number=1, declared_crosses=9000,
                            normal_crosses=1000, mode="norm", status="pending"))
    db.commit()

    stats = client.get("/api/admin/stats").json()
    assert stats["suspicious_total"] == 1
