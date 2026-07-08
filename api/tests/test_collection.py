from models import User


def test_collection_balance(client, db):
    user = User(vk_id=555, stitches_balance=1234)
    db.add(user)
    db.commit()

    resp = client.get("/api/collection/555/balance")
    assert resp.status_code == 200
    assert resp.json()["stitches_balance"] == 1234


def test_collection_balance_unknown_user(client):
    resp = client.get("/api/collection/999888/balance")
    assert resp.status_code == 200
    assert resp.json()["stitches_balance"] == 0
