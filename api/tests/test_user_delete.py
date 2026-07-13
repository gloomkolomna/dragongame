from models import (
    Dragon, User, UserDragon, UserProgress, UserLegendProgress,
    UserTreasure, UserInventory, SuspiciousReport, Treasure, ShopItem,
    EpicStage, EpicCareState, EpicMoodlet, ErrorLog,
)


def _setup_user_with_full_progress(db):
    d = Dragon(name="Rare", rarity=2, steps_count=1, is_active=True)
    epic = Dragon(name="Epic", rarity=3, steps_count=1, is_active=True, is_epic=True)
    db.add_all([d, epic])
    db.flush()

    treasure = Treasure(name="Gem", description="Shiny", dragon_id=d.id, is_active=True)
    item = ShopItem(name="Book", description="", cost_stitches=0, is_active=True)
    db.add_all([treasure, item])
    db.flush()

    u = User(vk_id=501, state="grow_step_1_norm", current_dragon_id=d.id,
             current_step=1, stitches_balance=500, epic_unlocked=True, epic_dragon_id=epic.id)
    db.add(u)
    db.flush()

    ud = UserDragon(user_id=u.vk_id, dragon_id=d.id, completed_at="")
    ud_epic = UserDragon(user_id=u.vk_id, dragon_id=epic.id, completed_at="")
    db.add_all([ud, ud_epic])
    db.flush()

    db.add(UserProgress(user_id=u.vk_id, dragon_id=d.id, step_number=1, completed=True))
    db.add(UserLegendProgress(user_id=u.vk_id, dragon_id=d.id, fragment_number=1, completed=True))
    db.add(UserTreasure(user_id=u.vk_id, treasure_id=treasure.id))
    db.add(UserInventory(user_id=u.vk_id, item_id=item.id, quantity=1))
    db.add(SuspiciousReport(user_id=u.vk_id, dragon_id=d.id, step_number=1,
                            declared_crosses=99999, normal_crosses=1000, mode="norm",
                            status="pending"))

    stage = EpicStage(dragon_id=epic.id, stage_number=1, name="Stage1", description="")
    db.add(stage)
    db.flush()
    db.add(EpicCareState(user_dragon_id=ud_epic.id, stage_id=stage.id, current_action_order=0))
    db.add(EpicMoodlet(user_dragon_id=ud_epic.id, key="action:1", title="First", stage_id=stage.id))

    db.commit()
    return u, d, epic


def test_delete_user_removes_all_progress(client, db):
    u, d, epic = _setup_user_with_full_progress(db)

    resp = client.delete(f"/api/admin/users/{u.vk_id}")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    assert db.query(User).filter(User.vk_id == u.vk_id).count() == 0
    assert db.query(UserDragon).filter(UserDragon.user_id == u.vk_id).count() == 0
    assert db.query(UserProgress).filter(UserProgress.user_id == u.vk_id).count() == 0
    assert db.query(UserLegendProgress).filter(UserLegendProgress.user_id == u.vk_id).count() == 0
    assert db.query(UserTreasure).filter(UserTreasure.user_id == u.vk_id).count() == 0
    assert db.query(UserInventory).filter(UserInventory.user_id == u.vk_id).count() == 0
    assert db.query(SuspiciousReport).filter(SuspiciousReport.user_id == u.vk_id).count() == 0
    assert db.query(EpicCareState).count() == 0
    assert db.query(EpicMoodlet).count() == 0


def test_delete_user_not_found(client, db):
    resp = client.delete("/api/admin/users/999999")
    assert resp.status_code == 404


def test_delete_user_keeps_dragons_and_logs(client, db):
    u, d, epic = _setup_user_with_full_progress(db)
    db.add(ErrorLog(source="bot", error_type="UPLOAD", message="fail",
                    user_id=u.vk_id, created_at="2026-01-01T00:00:00"))
    db.commit()

    resp = client.delete(f"/api/admin/users/{u.vk_id}")
    assert resp.status_code == 200

    assert db.query(Dragon).filter(Dragon.id == d.id).count() == 1
    assert db.query(Dragon).filter(Dragon.id == epic.id).count() == 1
    assert db.query(Treasure).filter(Treasure.dragon_id == d.id).count() == 1
    log = db.query(ErrorLog).filter(ErrorLog.user_id == u.vk_id).first()
    assert log is not None
