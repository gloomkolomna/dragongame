from models import User, DragonSet


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


def test_public_pricing_default(client):
    resp = client.get("/api/public/pricing")
    assert resp.status_code == 200
    data = resp.json()
    assert data["base_price_rub"] == 100
    assert data["sets"] == []


def test_public_pricing_with_sets(client, db):
    db.add(DragonSet(name="5 драконов", quantity=5, discount_percent=5,
                     donor_discount_percent=15, is_active=True, sort_order=1))
    db.add(DragonSet(name="10 драконов", quantity=10, discount_percent=10,
                     donor_discount_percent=20, is_active=True, sort_order=2))
    db.add(DragonSet(name="Скрытый", quantity=99, discount_percent=0,
                     donor_discount_percent=0, is_active=False, sort_order=0))
    db.commit()

    resp = client.get("/api/public/pricing")
    assert resp.status_code == 200
    data = resp.json()
    assert data["base_price_rub"] == 100
    assert len(data["sets"]) == 2
    assert data["sets"][0]["name"] == "5 драконов"
    assert data["sets"][0]["quantity"] == 5
    assert data["sets"][0]["discount_percent"] == 5
    assert data["sets"][0]["donor_discount_percent"] == 15
    assert data["sets"][0]["price_rub"] == 475
    assert data["sets"][0]["donor_price_rub"] == 425
    assert data["sets"][1]["name"] == "10 драконов"
    assert data["sets"][1]["price_rub"] == 900
    assert data["sets"][1]["donor_price_rub"] == 800


def test_public_pricing_custom_base(client, db):
    from models import PricingConfig
    db.add(PricingConfig(id=1, base_price_per_dragon=20000))
    db.add(DragonSet(name="1 дракон", quantity=1, discount_percent=0,
                     donor_discount_percent=10, is_active=True))
    db.commit()

    resp = client.get("/api/public/pricing")
    data = resp.json()
    assert data["base_price_rub"] == 200
    assert data["sets"][0]["price_rub"] == 200
    assert data["sets"][0]["donor_price_rub"] == 180
