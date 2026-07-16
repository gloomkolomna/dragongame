import hashlib
import config
from models import Dragon, DragonSet, PaymentOrder


def _dragon(db, name, family_id=None, pin="P0001"):
    d = Dragon(name=name, egg_type="egg", rarity=1, steps_count=1,
               pin_code=pin, family_id=family_id, is_active=True)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def _set(db, name="5 драконов", quantity=5, discount=5, donor_discount=15, active=True):
    s = DragonSet(name=name, quantity=quantity, discount_percent=discount,
                  donor_discount_percent=donor_discount, is_active=active)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# ─── Admin: pricing ───

def test_admin_get_pricing_default(client):
    resp = client.get("/api/admin/pricing")
    assert resp.status_code == 200
    assert resp.json()["base_price_rub"] == 100


def test_admin_update_pricing(client):
    resp = client.put("/api/admin/pricing", json={"base_price_rub": 150})
    assert resp.status_code == 200
    assert resp.json()["base_price_rub"] == 150
    assert client.get("/api/admin/pricing").json()["base_price_rub"] == 150


# ─── Admin: sets ───

def test_admin_create_set(client):
    resp = client.post("/api/admin/sets", json={
        "name": "5 драконов", "quantity": 5,
        "discount_percent": 5, "donor_discount_percent": 15,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "5 драконов"
    assert data["quantity"] == 5


def test_admin_create_set_requires_name(client):
    resp = client.post("/api/admin/sets", json={"name": "", "quantity": 5})
    assert resp.status_code == 400


def test_admin_update_set(client):
    sid = client.post("/api/admin/sets", json={"name": "X", "quantity": 3}).json()["id"]
    resp = client.put(f"/api/admin/sets/{sid}", json={"quantity": 10, "discount_percent": 20})
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 10
    assert resp.json()["discount_percent"] == 20


def test_admin_delete_set_soft(client):
    sid = client.post("/api/admin/sets", json={"name": "X", "quantity": 3}).json()["id"]
    resp = client.delete(f"/api/admin/sets/{sid}")
    assert resp.status_code == 200
    sets = client.get("/api/admin/sets").json()
    assert sets[0]["is_active"] is False


# ─── Create order ───

def test_create_order_success(client, db):
    for i in range(6):
        _dragon(db, f"D{i}", family_id=i % 3, pin=f"C{i:04d}")
    s = _set(db, quantity=5)
    resp = client.post("/api/payment/create-order", json={"vk_id": 1, "set_id": s.id})
    assert resp.status_code == 200
    data = resp.json()
    assert "payment_url" in data
    assert data["quantity"] == 5
    assert data["amount_rub"] == 47500
    assert "auth.robokassa.ru" in data["payment_url"]


def test_create_order_partial_rejection(client, db):
    for i in range(3):
        _dragon(db, f"D{i}", family_id=i, pin=f"E{i:04d}")
    s = _set(db, quantity=5)
    resp = client.post("/api/payment/create-order", json={"vk_id": 1, "set_id": s.id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] == "partial"
    assert data["available"] == 3


def test_create_order_partial_acceptance(client, db):
    for i in range(3):
        _dragon(db, f"D{i}", family_id=i, pin=f"F{i:04d}")
    s = _set(db, quantity=5)
    resp = client.post("/api/payment/create-order",
                       json={"vk_id": 1, "set_id": s.id, "accept_partial": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["quantity"] == 3
    assert data["amount_rub"] == 3 * 9500


def test_create_order_no_dragons(client, db):
    s = _set(db, quantity=5)
    resp = client.post("/api/payment/create-order", json={"vk_id": 1, "set_id": s.id})
    assert resp.json()["error"] == "no_dragons"


def test_create_order_pending_exists(client, db):
    _dragon(db, "D0", family_id=1, pin="G0001")
    s = _set(db, quantity=1)
    first = client.post("/api/payment/create-order", json={"vk_id": 1, "set_id": s.id}).json()
    resp = client.post("/api/payment/create-order", json={"vk_id": 1, "set_id": s.id})
    assert resp.json()["error"] == "pending"
    assert resp.json()["order_id"] == first["order_id"]


def test_create_order_set_not_found(client):
    resp = client.post("/api/payment/create-order", json={"vk_id": 1, "set_id": 999})
    assert resp.status_code == 404


# ─── Robokassa result callback ───

def _result_sig(out_sum, inv_id, vk_id, password2):
    return hashlib.md5(
        f"{out_sum}:{inv_id}:{password2}:Shp_vk_id={vk_id}".encode("utf-8")
    ).hexdigest()


def _make_pending_order(client, db, quantity=2):
    for i in range(quantity + 2):
        _dragon(db, f"D{i}", family_id=i % 2, pin=f"H{i:04d}")
    s = _set(db, quantity=quantity)
    order = client.post("/api/payment/create-order", json={"vk_id": 42, "set_id": s.id}).json()
    return order


def test_robokassa_result_callback_success(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "pass2")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    order = _make_pending_order(client, db, quantity=2)
    inv_id = str(order["order_id"])
    out_sum = f"{order['amount_rub'] / 100:.2f}"
    sig = _result_sig(out_sum, inv_id, 42, "pass2")
    resp = client.post("/api/payment/result", data={
        "OutSum": out_sum, "InvId": inv_id, "SignatureValue": sig, "Shp_vk_id": "42",
    })
    assert resp.status_code == 200
    assert resp.text == f"OK{inv_id}"
    o = db.query(PaymentOrder).filter(PaymentOrder.id == int(inv_id)).first()
    db.refresh(o)
    assert o.status == "success"
    import json as _json
    assert len(_json.loads(o.dragon_ids)) == 2


def test_robokassa_result_callback_idempotent(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "pass2")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    order = _make_pending_order(client, db, quantity=2)
    inv_id = str(order["order_id"])
    out_sum = f"{order['amount_rub'] / 100:.2f}"
    sig = _result_sig(out_sum, inv_id, 42, "pass2")
    payload = {"OutSum": out_sum, "InvId": inv_id, "SignatureValue": sig, "Shp_vk_id": "42"}
    client.post("/api/payment/result", data=payload)
    o = db.query(PaymentOrder).filter(PaymentOrder.id == int(inv_id)).first()
    db.refresh(o)
    first_ids = o.dragon_ids
    resp = client.post("/api/payment/result", data=payload)
    assert resp.status_code == 200
    db.refresh(o)
    assert o.dragon_ids == first_ids


def test_robokassa_result_callback_get_method(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "pass2")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    order = _make_pending_order(client, db, quantity=2)
    inv_id = str(order["order_id"])
    out_sum = f"{order['amount_rub'] / 100:.2f}"
    sig = _result_sig(out_sum, inv_id, 42, "pass2")
    resp = client.get(
        f"/api/payment/result?OutSum={out_sum}&InvId={inv_id}"
        f"&SignatureValue={sig}&Shp_vk_id=42"
    )
    assert resp.status_code == 200
    assert resp.text == f"OK{inv_id}"
    o = db.query(PaymentOrder).filter(PaymentOrder.id == int(inv_id)).first()
    db.refresh(o)
    assert o.status == "success"


def test_robokassa_result_prod_six_decimals(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "pass2")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    order = _make_pending_order(client, db, quantity=2)
    inv_id = str(order["order_id"])
    out_sum = f"{order['amount_rub'] / 100:.6f}"
    sig = _result_sig(out_sum, inv_id, 42, "pass2")
    resp = client.post("/api/payment/result", data={
        "OutSum": out_sum, "InvId": inv_id, "SignatureValue": sig, "Shp_vk_id": "42",
    })
    assert resp.status_code == 200
    assert resp.text == f"OK{inv_id}"


def test_robokassa_result_signature_mismatch(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "pass2")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    order = _make_pending_order(client, db, quantity=2)
    inv_id = str(order["order_id"])
    out_sum = f"{order['amount_rub'] / 100:.2f}"
    resp = client.post("/api/payment/result", data={
        "OutSum": out_sum, "InvId": inv_id, "SignatureValue": "deadbeef", "Shp_vk_id": "42",
    })
    assert resp.status_code == 400
    o = db.query(PaymentOrder).filter(PaymentOrder.id == int(inv_id)).first()
    db.refresh(o)
    assert o.status == "pending"


def test_robokassa_result_vk_mismatch(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "pass2")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    order = _make_pending_order(client, db, quantity=2)
    inv_id = str(order["order_id"])
    out_sum = f"{order['amount_rub'] / 100:.2f}"
    sig = _result_sig(out_sum, inv_id, 999, "pass2")
    resp = client.post("/api/payment/result", data={
        "OutSum": out_sum, "InvId": inv_id, "SignatureValue": sig, "Shp_vk_id": "999",
    })
    assert resp.status_code == 400


def test_robokassa_test_mode_uses_test_password(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "testpass")
    monkeypatch.setattr(config, "ROBOKASSA_PASSWORD2", "prodpass")
    order = _make_pending_order(client, db, quantity=1)
    inv_id = str(order["order_id"])
    out_sum = f"{order['amount_rub'] / 100:.2f}"

    sig_test = _result_sig(out_sum, inv_id, 42, "testpass")
    resp_test = client.post("/api/payment/result", data={
        "OutSum": out_sum, "InvId": inv_id, "SignatureValue": sig_test, "Shp_vk_id": "42",
    })
    assert resp_test.status_code == 200
    assert resp_test.text == f"OK{inv_id}"


def test_robokassa_prod_mode_uses_prod_password(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "0")
    monkeypatch.setattr(config, "ROBOKASSA_PASSWORD2", "prodpass")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "testpass")
    order = _make_pending_order(client, db, quantity=1)
    inv_id = str(order["order_id"])
    out_sum = f"{order['amount_rub'] / 100:.2f}"

    sig_prod = _result_sig(out_sum, inv_id, 42, "prodpass")
    resp_prod = client.post("/api/payment/result", data={
        "OutSum": out_sum, "InvId": inv_id, "SignatureValue": sig_prod, "Shp_vk_id": "42",
    })
    assert resp_prod.status_code == 200
    assert resp_prod.text == f"OK{inv_id}"


def test_robokassa_prod_mode_rejects_test_password(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "0")
    monkeypatch.setattr(config, "ROBOKASSA_PASSWORD2", "prodpass")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "testpass")
    order = _make_pending_order(client, db, quantity=1)
    inv_id = str(order["order_id"])
    out_sum = f"{order['amount_rub'] / 100:.2f}"

    sig_test = _result_sig(out_sum, inv_id, 42, "testpass")
    resp_wrong = client.post("/api/payment/result", data={
        "OutSum": out_sum, "InvId": inv_id,
        "SignatureValue": sig_test, "Shp_vk_id": "42",
    })
    assert resp_wrong.status_code == 400


def test_payment_url_contains_receipt(client, db):
    for i in range(3):
        _dragon(db, f"T{i}", family_id=i, pin=f"RR{i:04d}")
    s = _set(db, name="3 драконов", quantity=3)
    resp = client.post("/api/payment/create-order", json={"vk_id": 9, "set_id": s.id})
    url = resp.json()["payment_url"]
    assert "Receipt=" in url
    assert "payment_object" in url
    assert "commodity" in url
    assert "tax" in url and "none" in url
    assert "full_payment" in url


def test_payment_receipt_signature_includes_receipt(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "0")
    monkeypatch.setattr(config, "ROBOKASSA_MERCHANT_LOGIN", "bestiary")
    monkeypatch.setattr(config, "ROBOKASSA_PASSWORD1", "sec1")
    for i in range(2):
        _dragon(db, f"S{i}", family_id=i, pin=f"ST{i:04d}")
    s = _set(db, name="2 драконов", quantity=2)
    resp = client.post("/api/payment/create-order", json={"vk_id": 10, "set_id": s.id})
    url = resp.json()["payment_url"]
    from urllib.parse import parse_qs, urlparse, unquote
    qs = parse_qs(urlparse(url).query)
    receipt_raw = unquote(qs["Receipt"][0])
    out_sum = qs["OutSum"][0]
    inv_id = qs["InvId"][0]
    login = qs["MerchantLogin"][0]
    from urllib.parse import quote
    receipt_encoded = quote(receipt_raw, safe="")
    expected = hashlib.md5(
        f"{login}:{out_sum}:{inv_id}:{receipt_encoded}:sec1:Shp_vk_id=10".encode("utf-8")
    ).hexdigest()
    assert qs["SignatureValue"][0] == expected


def test_robokassa_payment_url_contains_istest_in_test_mode(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    for i in range(3):
        _dragon(db, f"T{i}", family_id=i, pin=f"R{i:04d}")
    s = _set(db, quantity=1)
    resp = client.post("/api/payment/create-order", json={"vk_id": 7, "set_id": s.id})
    assert "IsTest=1" in resp.json()["payment_url"]


def test_robokassa_payment_url_no_istest_in_prod_mode(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "0")
    for i in range(3):
        _dragon(db, f"T{i}", family_id=i, pin=f"S{i:04d}")
    s = _set(db, quantity=1)
    resp = client.post("/api/payment/create-order", json={"vk_id": 8, "set_id": s.id})
    assert "IsTest" not in resp.json()["payment_url"]


# ─── Success / fail pages ───

def test_payment_success_page(client):
    resp = client.get("/api/payment/success?InvId=1", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == config.VK_GROUP_URL


def test_payment_fail_page(client):
    resp = client.get("/api/payment/fail?InvId=1", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == config.VK_GROUP_URL


# ─── Admin payment-orders list ───

def test_list_payment_orders_empty(client):
    resp = client.get("/api/admin/payment-orders")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_payment_orders_filters(client, db):
    from models import DragonSet, PaymentOrder
    s = DragonSet(name="Test Set", quantity=5, discount_percent=5)
    db.add(s)
    db.commit()
    db.add(PaymentOrder(vk_id=1, set_id=s.id, amount_rub=47500, quantity=5, status="pending"))
    db.add(PaymentOrder(vk_id=2, set_id=s.id, amount_rub=47500, quantity=5, status="success", notified=True))
    db.add(PaymentOrder(vk_id=3, set_id=s.id, amount_rub=47500, quantity=5, status="fail"))
    db.commit()

    all_resp = client.get("/api/admin/payment-orders")
    assert all_resp.json()["total"] == 3

    success_resp = client.get("/api/admin/payment-orders?status=success")
    assert success_resp.json()["total"] == 1
    assert success_resp.json()["items"][0]["status"] == "success"

    pending_resp = client.get("/api/admin/payment-orders?status=pending")
    assert pending_resp.json()["total"] == 1
    assert pending_resp.json()["items"][0]["notified"] is False


# ─── Custom price ───

def test_custom_price_set_and_list(client, db):
    from models import User
    u = User(vk_id=555, state="idle")
    db.add(u)
    db.commit()

    resp = client.post("/api/admin/users/555/custom-price", json={"custom_price_per_dragon": 200})
    assert resp.status_code == 200
    assert resp.json()["custom_price_per_dragon"] == 20000

    user_resp = client.get("/api/admin/users/555")
    assert user_resp.json()["custom_price_per_dragon"] == 20000

    users_resp = client.get("/api/admin/users")
    u_data = next(u for u in users_resp.json() if u["vk_id"] == 555)
    assert u_data["custom_price_per_dragon"] == 20000

    resp_clear = client.post("/api/admin/users/555/custom-price", json={"custom_price_per_dragon": None})
    assert resp_clear.status_code == 200
    assert resp_clear.json()["custom_price_per_dragon"] is None
