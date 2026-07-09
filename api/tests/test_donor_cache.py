from models import DonorCache


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
