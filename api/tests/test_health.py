from datetime import datetime, timedelta
from models import ServiceHeartbeat, DonorCache


def test_health_no_data(client):
    resp = client.get("/api/admin/health")
    assert resp.status_code == 200
    services = resp.json()["services"]
    assert services["bot"]["status"] == "unknown"
    assert services["donor_sync"]["status"] == "unknown"


def test_health_bot_online(client, db):
    now = datetime.now().isoformat()
    db.add(ServiceHeartbeat(service_name="bot", last_seen=now, status="online"))
    db.commit()
    services = client.get("/api/admin/health").json()["services"]
    assert services["bot"]["status"] == "online"


def test_health_donor_sync_online(client, db):
    now = datetime.now().isoformat()
    db.add(DonorCache(vk_id=1, is_don=True, last_synced_at=now, updated_at=now))
    db.commit()
    services = client.get("/api/admin/health").json()["services"]
    assert services["donor_sync"]["status"] == "online"
    assert services["donor_sync"]["last_seen"] == now


def test_health_donor_sync_offline(client, db):
    old = (datetime.now() - timedelta(hours=72)).isoformat()
    db.add(DonorCache(vk_id=1, is_don=True, last_synced_at=old, updated_at=old))
    db.commit()
    services = client.get("/api/admin/health").json()["services"]
    assert services["donor_sync"]["status"] == "offline"


def test_health_donor_sync_uses_latest_sync(client, db):
    now = datetime.now().isoformat()
    old = (datetime.now() - timedelta(hours=72)).isoformat()
    db.add(DonorCache(vk_id=1, is_don=True, last_synced_at=old, updated_at=old))
    db.add(DonorCache(vk_id=2, is_don=False, last_synced_at=now, updated_at=now))
    db.commit()
    services = client.get("/api/admin/health").json()["services"]
    assert services["donor_sync"]["status"] == "online"
