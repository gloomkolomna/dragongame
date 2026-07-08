from models import (
    User, Dragon, DragonStep, UserDragon, UserLegendProgress,
    EpicStage, EpicStageAction, EpicActionItem, ShopItem,
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
    _epic_dragon(db, steps=1)
    epic_service.spawn_random_epic(db, 3)
    st = EpicStage(stage_number=1, name="Малыш", cycles_count=2, care_timeout_hours=0)
    db.add(st)
    db.flush()
    it = ShopItem(name="Молоко", is_active=True)
    db.add(it)
    db.flush()
    a = EpicStageAction(stage_id=st.id, action_label="кормить", order_in_cycle=0, crosses_norm=500)
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
    d = Dragon(name="Leg", rarity=3, steps_count=1, is_active=True, legend_image_path="dragons/cover.png")
    db.add(d)
    db.flush()
    db.add(DragonStep(dragon_id=d.id, step_number=1, phase=1, task_description="Отрывок 1", magic_action="Вышей щит", image_path="dragons/f1.png"))
    db.add(DragonStep(dragon_id=d.id, step_number=2, phase=1, task_description="Отрывок 2", magic_action="Вышей меч", image_path="dragons/f2.png"))
    db.add(UserDragon(user_id=4, dragon_id=d.id, completed_at="2026"))
    db.add(UserLegendProgress(user_id=4, dragon_id=d.id, fragment_number=1, completed=True))
    db.commit()

    r = client.get(f"/api/collection/4/legend/{d.id}").json()
    assert r["has_legend"] is True
    assert r["fragments"][0]["opened"] is True
    assert r["fragments"][0]["task"] == "Отрывок 1"
    assert r["fragments"][0]["assignment"] == "Вышей щит"
    assert r["fragments"][1]["opened"] is False
    assert r["fragments"][1]["task"] == ""
    assert r["fragments"][1]["assignment"] == ""
