from models import DonorCache
from models import User


def test_create_donor_cache_row(db):
    db.add(DonorCache(vk_id=555, is_don=True, don_since="2026-01-01", updated_at="now", last_synced_at="now"))
    db.commit()
    donor = db.query(DonorCache).filter(DonorCache.vk_id == 555).first()
    assert donor is not None
    assert donor.is_don is True
    assert donor.don_since == "2026-01-01"


def test_admin_get_donors(client, db):
    db.add(DonorCache(vk_id=555, is_don=True, don_since="2026-01-01", updated_at="now", last_synced_at="now"))
    db.commit()
    resp = client.get("/api/admin/donors")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["donors"][0]["vk_id"] == 555
    assert data["donors"][0]["is_don"] is True


def test_users_list_includes_is_don(client, db):
    db.add(User(vk_id=555, state="idle", registered_at="2026-01-01"))
    db.add(User(vk_id=777, state="idle", registered_at="2026-01-02"))
    db.add(DonorCache(vk_id=555, is_don=True, don_since="2026-01-01", updated_at="now", last_synced_at="now"))
    db.commit()
    resp = client.get("/api/admin/users")
    assert resp.status_code == 200
    by_id = {u["vk_id"]: u for u in resp.json()}
    assert by_id[555]["is_don"] is True
    assert by_id[777]["is_don"] is False


def test_user_detail_includes_is_don(client, db):
    db.add(User(vk_id=555, state="idle", registered_at="2026-01-01"))
    db.add(DonorCache(vk_id=555, is_don=True, don_since="2026-01-01", updated_at="now", last_synced_at="synced"))
    db.commit()
    resp = client.get("/api/admin/users/555")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_don"] is True
    assert data["don_since"] == "2026-01-01"
    assert data["don_synced_at"] == "synced"


def test_user_detail_is_don_false_when_no_cache(client, db):
    db.add(User(vk_id=777, state="idle", registered_at="2026-01-02"))
    db.commit()
    resp = client.get("/api/admin/users/777")
    assert resp.status_code == 200
    assert resp.json()["is_don"] is False
