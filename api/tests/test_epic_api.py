from models import (
    User, Dragon, DragonStep, UserDragon, UserLegendProgress,
    EpicStage, EpicStageAction, EpicActionItem, ShopItem, EpicMoodlet,
)
from services import epic_service


def _epic_dragon(db, steps=1, epic=True):
    d = Dragon(name="E", rarity=1, steps_count=steps, is_active=True, is_epic=epic, egg_type="Тень")
    db.add(d)
    db.flush()
    for i in range(1, steps + 1):
        db.add(DragonStep(dragon_id=d.id, step_number=i, phase=0, crosses_norm=1000))
    db.commit()
    return d


def test_epic_view_none(client, db):
    db.add(User(vk_id=1))
    db.commit()
    assert client.get("/api/collection/1/epic").json()["has_epic"] is False


def test_epic_view_egg(client, db):
    db.add(User(vk_id=2, epic_unlocked=False))
    _epic_dragon(db, steps=2)
    epic_service.spawn_random_epic(db, 2)
    r = client.get("/api/collection/2/epic").json()
    assert r["has_epic"] and r["phase"] == "egg"
    assert r["egg_progress"]["total"] == 2


def test_epic_view_care(client, db):
    db.add(User(vk_id=3))
    d = _epic_dragon(db, steps=1)
    epic_service.spawn_random_epic(db, 3)
    st = EpicStage(dragon_id=d.id, stage_number=1, name="Малыш")
    db.add(st)
    db.flush()
    it = ShopItem(name="Молоко", is_active=True)
    db.add(it)
    db.flush()
    a = EpicStageAction(dragon_id=d.id, stage_id=st.id, action_label="кормить", order_in_cycle=0, crosses_norm=500)
    db.add(a)
    db.flush()
    db.add(EpicActionItem(action_id=a.id, item_id=it.id))
    db.commit()
    epic_service.set_epic_name(db, 3, "Уголёк")
    epic_service.start_care(db, 3)

    r = client.get("/api/collection/3/epic").json()
    assert r["phase"] == "care"
    assert r["name"] == "Уголёк"
    assert r["stage"]["name"] == "Малыш"
    assert r["action"]["label"] == "кормить"
    assert r["action"]["items"][0]["owned"] is False


def test_legend_view(client, db):
    db.add(User(vk_id=4))
    d = Dragon(name="Leg", rarity=3, steps_count=1, is_active=True, legend_image_path="dragons/cover.png", legend_title="Сказание", legend_full_text="Вся легенда целиком.")
    db.add(d)
    db.flush()
    db.add(DragonStep(dragon_id=d.id, step_number=1, phase=1, task_description="Отрывок 1", magic_action="Вышей щит", image_path="dragons/f1.png"))
    db.add(DragonStep(dragon_id=d.id, step_number=2, phase=1, task_description="Отрывок 2", magic_action="Вышей меч", image_path="dragons/f2.png"))
    db.add(UserDragon(user_id=4, dragon_id=d.id, completed_at="2026"))
    db.add(UserLegendProgress(user_id=4, dragon_id=d.id, fragment_number=1, completed=True))
    db.commit()

    r = client.get(f"/api/collection/4/legend/{d.id}").json()
    assert r["has_legend"] is True
    assert r["dragon_id"] == d.id
    assert r["name"] == "Сказание"
    assert r["all_completed"] is False
    assert r["full_text"] == ""
    assert r["fragments"][0]["opened"] is True
    assert r["fragments"][0]["task"] == "Отрывок 1"
    assert r["fragments"][0]["assignment"] == "Вышей щит"
    assert r["fragments"][1]["opened"] is False
    assert r["fragments"][1]["task"] == ""
    assert r["fragments"][1]["assignment"] == ""


def test_legend_view_all_completed_shows_full_text(client, db):
    db.add(User(vk_id=5))
    d = Dragon(name="Leg2", rarity=3, steps_count=1, is_active=True, legend_full_text="Полная история.")
    db.add(d)
    db.flush()
    db.add(DragonStep(dragon_id=d.id, step_number=1, phase=1))
    db.add(DragonStep(dragon_id=d.id, step_number=2, phase=1))
    db.add(UserDragon(user_id=5, dragon_id=d.id, completed_at="2026"))
    db.add(UserLegendProgress(user_id=5, dragon_id=d.id, fragment_number=1, completed=True))
    db.add(UserLegendProgress(user_id=5, dragon_id=d.id, fragment_number=2, completed=True))
    db.commit()

    r = client.get(f"/api/collection/5/legend/{d.id}").json()
    assert r["all_completed"] is True
    assert r["full_text"] == "Полная история."
    assert r["name"] == "Leg2"


def test_epic_view_moodlets_exclude_first_time_markers(client, db):
    db.add(User(vk_id=30))
    d = _epic_dragon(db, steps=1)
    epic_service.spawn_random_epic(db, 30)
    st = EpicStage(dragon_id=d.id, stage_number=1, name="Малыш")
    db.add(st)
    db.flush()
    a = EpicStageAction(dragon_id=d.id, stage_id=st.id, action_label="кормить", order_in_cycle=0, crosses_norm=500)
    db.add(a)
    db.flush()
    db.commit()
    epic_service.set_epic_name(db, 30, "Уголёк")
    epic_service.start_care(db, 30)
    ud = epic_service.get_epic_user_dragon(db, 30)

    # "Впервые" marker (задание) — не должен показываться
    db.add(EpicMoodlet(user_dragon_id=ud.id, key=f"action:{a.id}", title="Впервые: кормить"))
    # реальный выданный мудлет — должен показываться
    db.add(EpicMoodlet(user_dragon_id=ud.id, key=f"action_outcome:{a.id}:positive", title="Сыт", text="Наелся", image_path="dragons/full.png", polarity="positive"))
    db.commit()

    r = client.get("/api/collection/30/epic").json()
    keys = [m["key"] for m in r["moodlets"]]
    assert keys == [f"action_outcome:{a.id}:positive"]
    assert r["moodlets"][0]["title"] == "Сыт"
    assert r["moodlets"][0]["image_path"].endswith("dragons/full.png")


def test_admin_actions_scoped_by_dragon(client, db):
    d1 = _epic_dragon(db, steps=1)
    d2 = _epic_dragon(db, steps=1)
    st = EpicStage(dragon_id=d1.id, stage_number=1, name="S1")
    db.add(st)
    db.commit()

    r1 = client.post(f"/api/admin/epic/species/{d1.id}/stages/{st.id}/actions", json={"action_label": "d1act", "crosses_norm": 100})
    assert r1.status_code == 200
    assert r1.json()["dragon_id"] == d1.id

    client.post(f"/api/admin/epic/species/{d2.id}/stages/{st.id}/actions", json={"action_label": "d2act", "crosses_norm": 100})

    l1 = client.get(f"/api/admin/epic/species/{d1.id}/stages/{st.id}/actions").json()
    l2 = client.get(f"/api/admin/epic/species/{d2.id}/stages/{st.id}/actions").json()
    assert [a["action_label"] for a in l1] == ["d1act"]
    assert [a["action_label"] for a in l2] == ["d2act"]
