import hashlib
import json
from datetime import datetime, timedelta
import config
from models import Dragon, DragonSet, PaymentOrder, PaymentLog


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


def _make_order(db, vk_id=42, quantity=2, provider="robokassa",
                created_at=None, gateway_txn_id=None, status="pending"):
    for i in range(quantity + 2):
        _dragon(db, f"D{i}", family_id=i % 2, pin=f"H{i:04d}")
    s = _set(db, quantity=quantity)
    order = PaymentOrder(
        vk_id=vk_id, set_id=s.id, amount_rub=quantity * 9500, quantity=quantity,
        price_per_pin=9500, provider=provider, status=status, dragon_ids="[]",
        gateway_txn_id=gateway_txn_id,
        created_at=created_at or datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


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


# ─── Create order (тонкая обёртка над pay-gateway) ───

def _gateway_created(monkeypatch, info=None, raises=None):
    from services import pay_gateway_client
    calls = []

    def fake_create_order(**kwargs):
        calls.append(kwargs)
        if raises is not None:
            raise raises
        return info or {
            "transaction_id": "20260824-000001",
            "payment_url": "https://belovolovhome.ru/pay/20260824-000001",
            "amount_kop": kwargs["amount_kop"],
            "expires_at": "2026-08-24T13:00:00+03:00",
        }

    monkeypatch.setattr(pay_gateway_client, "create_order", fake_create_order)
    return calls


def test_create_order_gateway_disabled(client):
    resp = client.post("/api/payment/create-order", json={
        "vk_id": 1, "amount_kop": 47500, "description": "Набор",
    })
    assert resp.status_code == 503


def test_create_order_gateway_success(client, monkeypatch):
    monkeypatch.setattr(config, "USE_PAY_GATEWAY", True)
    calls = _gateway_created(monkeypatch)
    resp = client.post("/api/payment/create-order", json={
        "vk_id": 7, "amount_kop": 47500, "description": "Набор цифровых товаров",
        "receipt_email": "Buyer@Example.com",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["transaction_id"] == "20260824-000001"
    assert data["payment_url"].endswith("/pay/20260824-000001")
    assert data["amount_kop"] == 47500
    assert calls[0]["vk_id"] == 7
    assert calls[0]["receipt_email"] == "Buyer@Example.com"


def test_create_order_gateway_blocked(client, monkeypatch):
    monkeypatch.setattr(config, "USE_PAY_GATEWAY", True)
    from services.pay_gateway_client import PayGatewayBlocked
    _gateway_created(monkeypatch, raises=PayGatewayBlocked("test_blocked"))
    resp = client.post("/api/payment/create-order", json={
        "vk_id": 8, "amount_kop": 47500, "description": "Набор",
    })
    assert resp.status_code == 200
    assert resp.json()["error"] == "unavailable"


def test_create_order_gateway_error(client, monkeypatch):
    monkeypatch.setattr(config, "USE_PAY_GATEWAY", True)
    from services.pay_gateway_client import PayGatewayError
    _gateway_created(monkeypatch, raises=PayGatewayError("http 500: boom"))
    resp = client.post("/api/payment/create-order", json={
        "vk_id": 9, "amount_kop": 47500, "description": "Набор",
    })
    assert resp.status_code == 502


def test_create_order_validation(client, monkeypatch):
    monkeypatch.setattr(config, "USE_PAY_GATEWAY", True)
    resp = client.post("/api/payment/create-order", json={"vk_id": 1})
    assert resp.status_code == 400
    resp = client.post("/api/payment/create-order", json={
        "vk_id": 0, "amount_kop": 100, "description": "X",
    })
    assert resp.status_code == 400
    resp = client.post("/api/payment/create-order", json={
        "vk_id": 1, "amount_kop": 100, "description": "  ",
    })
    assert resp.status_code == 400


# ─── Robokassa result callback ───

def _result_sig(out_sum, inv_id, vk_id, password2):
    return hashlib.md5(
        f"{out_sum}:{inv_id}:{password2}:Shp_vk_id={vk_id}".encode("utf-8")
    ).hexdigest()


def test_robokassa_result_callback_success(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "pass2")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    order = _make_order(db, quantity=2)
    inv_id = str(order.id)
    out_sum = f"{order.amount_rub / 100:.2f}"
    sig = _result_sig(out_sum, inv_id, 42, "pass2")
    resp = client.post("/api/payment/result", data={
        "OutSum": out_sum, "InvId": inv_id, "SignatureValue": sig, "Shp_vk_id": "42",
    })
    assert resp.status_code == 200
    assert resp.text == f"OK{inv_id}"
    db.refresh(order)
    assert order.status == "success"
    assert len(json.loads(order.dragon_ids)) == 2


def test_robokassa_result_callback_idempotent(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "pass2")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    order = _make_order(db, quantity=2)
    inv_id = str(order.id)
    out_sum = f"{order.amount_rub / 100:.2f}"
    sig = _result_sig(out_sum, inv_id, 42, "pass2")
    payload = {"OutSum": out_sum, "InvId": inv_id, "SignatureValue": sig, "Shp_vk_id": "42"}
    client.post("/api/payment/result", data=payload)
    db.refresh(order)
    first_ids = order.dragon_ids
    resp = client.post("/api/payment/result", data=payload)
    assert resp.status_code == 200
    db.refresh(order)
    assert order.dragon_ids == first_ids


def test_robokassa_result_callback_get_method(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "pass2")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    order = _make_order(db, quantity=2)
    inv_id = str(order.id)
    out_sum = f"{order.amount_rub / 100:.2f}"
    sig = _result_sig(out_sum, inv_id, 42, "pass2")
    resp = client.get(
        f"/api/payment/result?OutSum={out_sum}&InvId={inv_id}"
        f"&SignatureValue={sig}&Shp_vk_id=42"
    )
    assert resp.status_code == 200
    assert resp.text == f"OK{inv_id}"
    db.refresh(order)
    assert order.status == "success"


def test_robokassa_result_prod_six_decimals(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "pass2")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    order = _make_order(db, quantity=2)
    inv_id = str(order.id)
    out_sum = f"{order.amount_rub / 100:.6f}"
    sig = _result_sig(out_sum, inv_id, 42, "pass2")
    resp = client.post("/api/payment/result", data={
        "OutSum": out_sum, "InvId": inv_id, "SignatureValue": sig, "Shp_vk_id": "42",
    })
    assert resp.status_code == 200
    assert resp.text == f"OK{inv_id}"


def test_robokassa_result_signature_mismatch(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "pass2")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    order = _make_order(db, quantity=2)
    inv_id = str(order.id)
    out_sum = f"{order.amount_rub / 100:.2f}"
    resp = client.post("/api/payment/result", data={
        "OutSum": out_sum, "InvId": inv_id, "SignatureValue": "deadbeef", "Shp_vk_id": "42",
    })
    assert resp.status_code == 400
    db.refresh(order)
    assert order.status == "pending"


def test_robokassa_result_vk_mismatch(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "pass2")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    order = _make_order(db, quantity=2)
    inv_id = str(order.id)
    out_sum = f"{order.amount_rub / 100:.2f}"
    sig = _result_sig(out_sum, inv_id, 999, "pass2")
    resp = client.post("/api/payment/result", data={
        "OutSum": out_sum, "InvId": inv_id, "SignatureValue": sig, "Shp_vk_id": "999",
    })
    assert resp.status_code == 400


def test_robokassa_test_mode_uses_test_password(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    monkeypatch.setattr(config, "ROBOKASSA_TEST_PASSWORD2", "testpass")
    monkeypatch.setattr(config, "ROBOKASSA_PASSWORD2", "prodpass")
    order = _make_order(db, quantity=1)
    inv_id = str(order.id)
    out_sum = f"{order.amount_rub / 100:.2f}"

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
    order = _make_order(db, quantity=1)
    inv_id = str(order.id)
    out_sum = f"{order.amount_rub / 100:.2f}"

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
    order = _make_order(db, quantity=1)
    inv_id = str(order.id)
    out_sum = f"{order.amount_rub / 100:.2f}"

    sig_test = _result_sig(out_sum, inv_id, 42, "testpass")
    resp_wrong = client.post("/api/payment/result", data={
        "OutSum": out_sum, "InvId": inv_id,
        "SignatureValue": sig_test, "Shp_vk_id": "42",
    })
    assert resp_wrong.status_code == 400


def _pay_html(client, order_id, vk_id):
    return client.get(f"/api/payment/pay/{order_id}?vk_id={vk_id}").text


def _extract_input(html, name):
    import re
    m = re.search(rf'name="{name}"\s+value="([^"]*)"', html)
    return m.group(1) if m else None


def test_payment_url_contains_receipt(client, db):
    order = _make_order(db, vk_id=9, quantity=3)
    html = _pay_html(client, order.id, 9)
    receipt = _extract_input(html, "Receipt")
    assert receipt is not None
    from urllib.parse import unquote_plus
    receipt_raw = unquote_plus(receipt)
    assert "tax" in receipt_raw and "none" in receipt_raw


def test_payment_receipt_signature_includes_receipt(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "0")
    monkeypatch.setattr(config, "ROBOKASSA_MERCHANT_LOGIN", "bestiary")
    monkeypatch.setattr(config, "ROBOKASSA_PASSWORD1", "sec1")
    order = _make_order(db, vk_id=10, quantity=2)
    html = _pay_html(client, order.id, 10)
    out_sum = _extract_input(html, "OutSum")
    inv_id = _extract_input(html, "InvId")
    login = _extract_input(html, "MerchantLogin")
    signature = _extract_input(html, "SignatureValue")
    receipt_encoded = _extract_input(html, "Receipt")
    from urllib.parse import unquote_plus, quote_plus
    receipt_raw = unquote_plus(receipt_encoded)
    receipt_re_encoded = quote_plus(receipt_raw, safe="")
    expected = hashlib.md5(
        f"{login}:{out_sum}:{inv_id}:{receipt_re_encoded}:sec1:Shp_vk_id=10".encode("utf-8")
    ).hexdigest()
    assert signature == expected


def test_robokassa_payment_url_contains_istest_in_test_mode(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "1")
    order = _make_order(db, vk_id=7, quantity=1)
    html = _pay_html(client, order.id, 7)
    assert _extract_input(html, "IsTest") == "1"


def test_robokassa_payment_url_no_istest_in_prod_mode(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_TEST_MODE", "0")
    order = _make_order(db, vk_id=8, quantity=1)
    html = _pay_html(client, order.id, 8)
    assert _extract_input(html, "IsTest") is None


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


def test_admin_payment_orders_no_robokassa_fields(client, db):
    order = _make_order(db, quantity=1)
    resp = client.get("/api/admin/payment-orders")
    item = next(o for o in resp.json()["items"] if o["id"] == order.id)
    assert "provider" not in item
    assert "robokassa_inv_id" not in item
    assert "robokassa_inv_id_expected" not in item
    assert item["gateway_txn_id"] is None


def test_admin_payment_orders_includes_gateway_txn(client, db):
    order = _make_order(db, quantity=1, provider="gateway",
                        gateway_txn_id="20260824-000042")
    resp = client.get("/api/admin/payment-orders")
    item = next(o for o in resp.json()["items"] if o["id"] == order.id)
    assert item["gateway_txn_id"] == "20260824-000042"


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


# ─── Auto-cancel expired orders ───

def test_cancel_expired_orders_scoped_to_user(client, db):
    from routes.payment import _cancel_expired_orders
    old_str = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S")
    s = _set(db, quantity=2)
    expired = PaymentOrder(
        vk_id=99, set_id=s.id, amount_rub=19000, quantity=2,
        price_per_pin=9500, status="pending", dragon_ids="[]",
        created_at=old_str,
    )
    other_fresh = PaymentOrder(
        vk_id=98, set_id=s.id, amount_rub=19000, quantity=2,
        price_per_pin=9500, status="pending", dragon_ids="[]",
        created_at=old_str,
    )
    db.add_all([expired, other_fresh])
    db.commit()

    cancelled = _cancel_expired_orders(db, vk_id=99)
    assert expired.id in {o.id for o in cancelled}
    assert other_fresh.id not in {o.id for o in cancelled}
    db.refresh(expired)
    db.refresh(other_fresh)
    assert expired.status == "cancelled"
    assert other_fresh.status == "pending"


def test_cancel_expired_orders_all_batch(client, db):
    from routes.payment import _cancel_expired_orders
    s = _set(db, quantity=1)
    expired_old = PaymentOrder(
        vk_id=101, set_id=s.id, amount_rub=9500, quantity=1,
        price_per_pin=9500, status="pending", dragon_ids="[]",
        created_at=(datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S"),
    )
    expired_other = PaymentOrder(
        vk_id=102, set_id=s.id, amount_rub=9500, quantity=1,
        price_per_pin=9500, status="pending", dragon_ids="[]",
        created_at=(datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S"),
    )
    fresh = PaymentOrder(
        vk_id=103, set_id=s.id, amount_rub=9500, quantity=1,
        price_per_pin=9500, status="pending", dragon_ids="[]",
        created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add_all([expired_old, expired_other, fresh])
    db.commit()
    db.refresh(expired_old)
    db.refresh(expired_other)
    db.refresh(fresh)

    cancelled = _cancel_expired_orders(db)

    cancelled_ids = {o.id for o in cancelled}
    assert expired_old.id in cancelled_ids
    assert expired_other.id in cancelled_ids
    assert fresh.id not in cancelled_ids
    db.refresh(expired_old)
    db.refresh(expired_other)
    db.refresh(fresh)
    assert expired_old.status == "cancelled"
    assert expired_other.status == "cancelled"
    assert fresh.status == "pending"


def test_cancel_expired_orders_idempotent(client, db):
    from routes.payment import _cancel_expired_orders
    s = _set(db, quantity=1)
    order = PaymentOrder(
        vk_id=201, set_id=s.id, amount_rub=9500, quantity=1,
        price_per_pin=9500, status="cancelled", dragon_ids="[]",
        created_at=(datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(order)
    db.commit()

    cancelled = _cancel_expired_orders(db)
    assert order.id not in {o.id for o in cancelled}
    db.refresh(order)
    assert order.status == "cancelled"


def test_payment_page_rejects_expired_order(client, db):
    order = _make_order(
        db, vk_id=97, quantity=1,
        created_at=(datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S"),
    )
    resp = client.get(f"/api/payment/pay/{order.id}?vk_id=97")
    assert resp.status_code == 410
    assert "просрочен" in resp.text


def test_payment_page_logs_not_found(client, db):
    resp = client.get("/api/payment/pay/9999?vk_id=77")
    assert resp.status_code == 404
    log = db.query(PaymentLog).filter(PaymentLog.action == "pay_not_found").first()
    assert log is not None
    assert log.order_id == 9999
    assert log.vk_id == 77
    assert "not found" in log.detail


def test_payment_page_logs_expired(client, db):
    order = _make_order(
        db, vk_id=88, quantity=1,
        created_at=(datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%S"),
    )
    resp = client.get(f"/api/payment/pay/{order.id}?vk_id=88")
    assert resp.status_code == 410
    log = db.query(PaymentLog).filter(PaymentLog.action == "pay_expired").first()
    assert log is not None
    assert log.order_id == order.id
    assert "expired" in log.detail


def test_payment_page_logs_already_paid(client, db):
    order = _make_order(db, vk_id=66, quantity=1, status="success")
    resp = client.get(f"/api/payment/pay/{order.id}?vk_id=66")
    assert resp.status_code == 400
    log = db.query(PaymentLog).filter(PaymentLog.action == "pay_already_success").first()
    assert log is not None
    assert log.order_id == order.id
    assert "status=success" in log.detail


def test_payment_url_uses_inv_id_offset(client, db, monkeypatch):
    monkeypatch.setattr(config, "ROBOKASSA_INV_ID_OFFSET", 100)
    from routes.payment import build_payment_url, inv_id_for_order
    order = _make_order(db, vk_id=96, quantity=1)

    url = build_payment_url(order, 96, "Test")
    from urllib.parse import urlparse, parse_qs
    qs = parse_qs(urlparse(url).query)
    assert qs["InvId"][0] == str(order.id + 100)
    assert inv_id_for_order(order.id) == order.id + 100


# ─── MONETA: service helpers ───

def test_moneta_order_id_roundtrip():
    from services.moneta_service import moneta_transaction_id_for, order_id_from_moneta
    assert moneta_transaction_id_for(123) == "123"
    assert order_id_from_moneta("123") == 123
    assert order_id_from_moneta("abc") is None
    assert order_id_from_moneta(None) is None


def test_moneta_format_amount():
    from services.moneta_service import format_amount
    assert format_amount(0) == "0.00"
    assert format_amount(9500) == "95.00"
    assert format_amount(47500) == "475.00"
    assert format_amount(10001) == "100.01"


def test_moneta_payment_form_signature_spec_example():
    from services.moneta_service import build_payment_signature
    sig = build_payment_signature("54600817", "FF790ABCD", "120.25", "QWERTY", "0")
    assert sig == "c8222aef6362c7f1239ccdc729d1a200"


def test_moneta_callback_signature_spec_example():
    from services.moneta_service import verify_callback_signature
    params = {
        "MNT_ID": "54600817",
        "MNT_TRANSACTION_ID": "FF790ABCD",
        "MNT_OPERATION_ID": "123456",
        "MNT_AMOUNT": "120.25",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_TEST_MODE": "0",
        "MNT_SIGNATURE": "69bdf9bd91820b8f7b4c4b25d3d22dfa",
    }
    assert verify_callback_signature(params, "QWERTY") is True


def test_moneta_callback_signature_mismatch():
    from services.moneta_service import verify_callback_signature
    params = {
        "MNT_ID": "54600817",
        "MNT_TRANSACTION_ID": "FF790ABCD",
        "MNT_OPERATION_ID": "123456",
        "MNT_AMOUNT": "120.25",
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_TEST_MODE": "0",
        "MNT_SIGNATURE": "deadbeef",
    }
    assert verify_callback_signature(params, "QWERTY") is False


# ─── MONETA: payment form ───

def _make_moneta_pending_order(db, quantity=2):
    return _make_order(db, quantity=quantity, provider="moneta")


def test_moneta_payment_form_contains_signature(client, db, monkeypatch):
    monkeypatch.setattr(config, "MONETA_MNT_ID", "54600817")
    monkeypatch.setattr(config, "MONETA_INTEGRITY_CODE", "QWERTY")
    monkeypatch.setattr(config, "MONETA_TEST_MODE", "0")
    order = _make_moneta_pending_order(db, quantity=2)
    html = _pay_html(client, order.id, 42)
    mnt_id = _extract_input(html, "MNT_ID")
    mnt_trx = _extract_input(html, "MNT_TRANSACTION_ID")
    mnt_amount = _extract_input(html, "MNT_AMOUNT")
    signature = _extract_input(html, "MNT_SIGNATURE")
    assert mnt_id == "54600817"
    assert mnt_trx == str(order.id)
    assert mnt_amount == f"{order.amount_rub / 100:.2f}"
    from services.moneta_service import build_payment_signature
    expected = build_payment_signature(mnt_id, mnt_trx, mnt_amount, "QWERTY", "0")
    assert signature == expected


def test_moneta_payment_form_test_mode(client, db, monkeypatch):
    monkeypatch.setattr(config, "MONETA_MNT_ID", "54600817")
    monkeypatch.setattr(config, "MONETA_INTEGRITY_CODE", "QWERTY")
    monkeypatch.setattr(config, "MONETA_TEST_MODE", "1")
    order = _make_moneta_pending_order(db, quantity=1)
    html = _pay_html(client, order.id, 42)
    assert "demo.moneta.ru/assistant.htm" in html
    assert _extract_input(html, "MNT_TEST_MODE") == "1"


def test_moneta_payment_form_prod_mode(client, db, monkeypatch):
    monkeypatch.setattr(config, "MONETA_MNT_ID", "54600817")
    monkeypatch.setattr(config, "MONETA_INTEGRITY_CODE", "QWERTY")
    monkeypatch.setattr(config, "MONETA_TEST_MODE", "0")
    order = _make_moneta_pending_order(db, quantity=1)
    html = _pay_html(client, order.id, 42)
    assert "payanyway.ru/assistant.htm" in html
    assert _extract_input(html, "MNT_TEST_MODE") == "0"


def test_moneta_payment_form_contains_inventory(client, db, monkeypatch):
    monkeypatch.setattr(config, "MONETA_MNT_ID", "54600817")
    monkeypatch.setattr(config, "MONETA_INTEGRITY_CODE", "QWERTY")
    monkeypatch.setattr(config, "MONETA_TEST_MODE", "0")
    order = _make_moneta_pending_order(db, quantity=1)
    html = _pay_html(client, order.id, 42)
    custom2_raw = _extract_input(html, "MNT_CUSTOM2")
    assert custom2_raw is not None
    import html as _html
    inventory = json.loads(_html.unescape(custom2_raw))
    assert "items" in inventory
    item = inventory["items"][0]
    assert item["p"] == f"{order.amount_rub / 100:.2f}"
    assert item["q"] == "1"
    assert item["t"] == "1105"
    assert item["pm"] == "full_payment"
    assert item["po"] == "commodity"


def test_moneta_payment_form_inventory_includes_customer(client, db, monkeypatch):
    monkeypatch.setattr(config, "MONETA_MNT_ID", "54600817")
    monkeypatch.setattr(config, "MONETA_INTEGRITY_CODE", "QWERTY")
    monkeypatch.setattr(config, "MONETA_TEST_MODE", "0")
    order = _make_moneta_pending_order(db, quantity=1)
    order.receipt_email = "buyer@example.com"
    db.commit()

    html = _pay_html(client, order.id, 42)
    import html as _html
    inventory = json.loads(_html.unescape(_extract_input(html, "MNT_CUSTOM2")))
    assert inventory["customer"] == "buyer@example.com"


def test_moneta_payment_form_no_customer_without_email(client, db, monkeypatch):
    monkeypatch.setattr(config, "MONETA_MNT_ID", "54600817")
    monkeypatch.setattr(config, "MONETA_INTEGRITY_CODE", "QWERTY")
    monkeypatch.setattr(config, "MONETA_TEST_MODE", "0")
    order = _make_moneta_pending_order(db, quantity=1)
    order.receipt_email = None
    db.commit()

    html = _pay_html(client, order.id, 42)
    import html as _html
    inventory = json.loads(_html.unescape(_extract_input(html, "MNT_CUSTOM2")))
    assert "customer" not in inventory


# ─── MONETA: callback (Pay URL) ───

def _callback_sig(mnt_id, mnt_trx, mnt_operation_id, amount, code, test_mode="0"):
    return hashlib.md5(
        f"{mnt_id}{mnt_trx}{mnt_operation_id}{amount}RUB{test_mode}{code}".encode("utf-8")
    ).hexdigest()


def test_moneta_callback_success(client, db, monkeypatch):
    monkeypatch.setattr(config, "MONETA_INTEGRITY_CODE", "QWERTY")
    order = _make_moneta_pending_order(db, quantity=2)
    mnt_trx = str(order.id)
    amount = f"{order.amount_rub / 100:.2f}"
    sig = _callback_sig("", mnt_trx, "555000", amount, "QWERTY")
    resp = client.post("/api/payment/moneta/callback", data={
        "MNT_TRANSACTION_ID": mnt_trx,
        "MNT_OPERATION_ID": "555000",
        "MNT_AMOUNT": amount,
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_TEST_MODE": "0",
        "MNT_SIGNATURE": sig,
    })
    assert resp.status_code == 200
    assert resp.text == "SUCCESS"
    db.refresh(order)
    assert order.status == "success"
    assert len(json.loads(order.dragon_ids)) == 2


def test_moneta_callback_get_method(client, db, monkeypatch):
    monkeypatch.setattr(config, "MONETA_INTEGRITY_CODE", "QWERTY")
    order = _make_moneta_pending_order(db, quantity=2)
    mnt_trx = str(order.id)
    amount = f"{order.amount_rub / 100:.2f}"
    sig = _callback_sig("", mnt_trx, "555001", amount, "QWERTY")
    from urllib.parse import urlencode
    resp = client.get(
        "/api/payment/moneta/callback?" + urlencode({
            "MNT_TRANSACTION_ID": mnt_trx,
            "MNT_OPERATION_ID": "555001",
            "MNT_AMOUNT": amount,
            "MNT_CURRENCY_CODE": "RUB",
            "MNT_TEST_MODE": "0",
            "MNT_SIGNATURE": sig,
        })
    )
    assert resp.status_code == 200
    assert resp.text == "SUCCESS"
    db.refresh(order)
    assert order.status == "success"


def test_moneta_callback_idempotent(client, db, monkeypatch):
    monkeypatch.setattr(config, "MONETA_INTEGRITY_CODE", "QWERTY")
    order = _make_moneta_pending_order(db, quantity=2)
    mnt_trx = str(order.id)
    amount = f"{order.amount_rub / 100:.2f}"
    sig = _callback_sig("", mnt_trx, "555002", amount, "QWERTY")
    payload = {
        "MNT_TRANSACTION_ID": mnt_trx,
        "MNT_OPERATION_ID": "555002",
        "MNT_AMOUNT": amount,
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_TEST_MODE": "0",
        "MNT_SIGNATURE": sig,
    }
    r1 = client.post("/api/payment/moneta/callback", data=payload)
    assert r1.status_code == 200
    db.refresh(order)
    first_ids = order.dragon_ids
    r2 = client.post("/api/payment/moneta/callback", data=payload)
    assert r2.status_code == 200
    db.refresh(order)
    assert order.dragon_ids == first_ids


def test_moneta_callback_bad_signature(client, db, monkeypatch):
    monkeypatch.setattr(config, "MONETA_INTEGRITY_CODE", "QWERTY")
    order = _make_moneta_pending_order(db, quantity=1)
    mnt_trx = str(order.id)
    amount = f"{order.amount_rub / 100:.2f}"
    resp = client.post("/api/payment/moneta/callback", data={
        "MNT_TRANSACTION_ID": mnt_trx,
        "MNT_OPERATION_ID": "555003",
        "MNT_AMOUNT": amount,
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_TEST_MODE": "0",
        "MNT_SIGNATURE": "deadbeef",
    })
    assert resp.status_code == 400
    db.refresh(order)
    assert order.status == "pending"


def test_moneta_callback_amount_mismatch(client, db, monkeypatch):
    monkeypatch.setattr(config, "MONETA_INTEGRITY_CODE", "QWERTY")
    order = _make_moneta_pending_order(db, quantity=1)
    mnt_trx = str(order.id)
    wrong_amount = f"{(order.amount_rub + 99999) / 100:.2f}"
    sig = _callback_sig("", mnt_trx, "555004", wrong_amount, "QWERTY")
    resp = client.post("/api/payment/moneta/callback", data={
        "MNT_TRANSACTION_ID": mnt_trx,
        "MNT_OPERATION_ID": "555004",
        "MNT_AMOUNT": wrong_amount,
        "MNT_CURRENCY_CODE": "RUB",
        "MNT_TEST_MODE": "0",
        "MNT_SIGNATURE": sig,
    })
    assert resp.status_code == 400
    assert resp.json()["detail"] == "amount mismatch"


# ─── Settings (без платёжных полей) ───

def test_settings_no_payment_fields(client):
    got = client.get("/api/admin/settings").json()
    assert "payment_provider" not in got
    assert "payments_test_mode" not in got
    assert "payments_test_vk_id" not in got


def test_settings_roundtrip(client):
    resp = client.put("/api/admin/settings", json={
        "welcome_keyword": "дракон", "suspicious_multiplier": 2, "block_multiplier": 4,
    })
    assert resp.status_code == 200
    got = client.get("/api/admin/settings").json()
    assert got["welcome_keyword"] == "дракон"
    assert got["block_multiplier"] == 4


def test_payment_return_redirect(client):
    resp = client.get("/api/payment/return", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == config.VK_GROUP_URL
