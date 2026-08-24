import hashlib
import hmac
import json
from datetime import datetime

import config
from models import Dragon, DragonSet, PaymentOrder, PaymentLog, DragonReservation

SECRET = "whsec-test"


def _dragon(db, name, pin):
    d = Dragon(name=name, egg_type="egg", rarity=1, steps_count=1,
               pin_code=pin, family_id=None, is_active=True)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def _make_gateway_order(db, vk_id=42, quantity=2, status="pending",
                        created_at=None, txn="20260824-000001"):
    for i in range(quantity + 2):
        _dragon(db, f"D{i}", pin=f"WH{i:04d}")
    s = DragonSet(name="2 драконов", quantity=quantity, discount_percent=5,
                  donor_discount_percent=15, is_active=True)
    db.add(s)
    db.commit()
    db.refresh(s)
    order = PaymentOrder(
        vk_id=vk_id, set_id=s.id, amount_rub=quantity * 9500, quantity=quantity,
        price_per_pin=9500, provider="gateway", status=status, dragon_ids="[]",
        gateway_txn_id=txn, receipt_email="buyer@example.com",
        created_at=created_at or datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def _webhook_body(order, amount_kop=None, vk_id=None, game_id="dragons",
                  txn=None):
    payload = {
        "transaction_id": txn or order.gateway_txn_id,
        "game_id": game_id,
        "vk_id": vk_id if vk_id is not None else order.vk_id,
        "amount_kop": amount_kop if amount_kop is not None else order.amount_rub,
        "status": "success",
        "paid_at": "2026-08-24 12:03:00",
        "moneta_operation_id": "555000",
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sig(body: bytes) -> str:
    return hmac.new(SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _post(client, body: bytes, signature: str):
    return client.post(
        "/api/payment/webhook",
        content=body,
        headers={"Content-Type": "application/json", "X-Pay-Signature": signature},
    )


def _setup_config(monkeypatch):
    monkeypatch.setattr(config, "PAY_GATEWAY_WEBHOOK_SECRET", SECRET)
    monkeypatch.setattr(config, "PAY_GATEWAY_GAME_ID", "dragons")
    monkeypatch.setattr(config, "VK_GROUP_TOKEN", "")


def test_webhook_success_fulfills_order(client, db, monkeypatch):
    _setup_config(monkeypatch)
    order = _make_gateway_order(db, quantity=2)
    resp = _post(client, _webhook_body(order), _sig(_webhook_body(order)))
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    db.refresh(order)
    assert order.status == "success"
    assert order.completed_at
    assert len(json.loads(order.dragon_ids)) == 2
    log = db.query(PaymentLog).filter(
        PaymentLog.order_id == order.id,
        PaymentLog.action == "gateway_success_webhook",
    ).first()
    assert log is not None
    reservations = db.query(DragonReservation).filter(
        DragonReservation.vk_user_id == order.vk_id,
    ).all()
    assert len(reservations) == 2


def test_webhook_idempotent(client, db, monkeypatch):
    _setup_config(monkeypatch)
    order = _make_gateway_order(db, quantity=1)
    body = _webhook_body(order)
    r1 = _post(client, body, _sig(body))
    assert r1.status_code == 200
    db.refresh(order)
    first_ids = order.dragon_ids
    r2 = _post(client, body, _sig(body))
    assert r2.status_code == 200
    db.refresh(order)
    assert order.dragon_ids == first_ids
    reservations = db.query(DragonReservation).filter(
        DragonReservation.vk_user_id == order.vk_id,
    ).count()
    assert reservations == 1


def test_webhook_bad_signature(client, db, monkeypatch):
    _setup_config(monkeypatch)
    order = _make_gateway_order(db, quantity=1)
    resp = _post(client, _webhook_body(order), "deadbeef")
    assert resp.status_code == 401
    db.refresh(order)
    assert order.status == "pending"
    log = db.query(PaymentLog).filter(
        PaymentLog.action == "gateway_webhook_bad_sig").first()
    assert log is not None


def test_webhook_unknown_txn_returns_404(client, db, monkeypatch):
    _setup_config(monkeypatch)
    order = _make_gateway_order(db, quantity=1, txn="20260824-000001")
    body = _webhook_body(order, txn="20260824-999999")
    resp = _post(client, body, _sig(body))
    assert resp.status_code == 404
    log = db.query(PaymentLog).filter(
        PaymentLog.action == "gateway_webhook_not_found").first()
    assert log is not None


def test_webhook_amount_mismatch(client, db, monkeypatch):
    _setup_config(monkeypatch)
    order = _make_gateway_order(db, quantity=1)
    body = _webhook_body(order, amount_kop=order.amount_rub + 100)
    resp = _post(client, body, _sig(body))
    assert resp.status_code == 400
    assert resp.json()["detail"] == "amount mismatch"
    db.refresh(order)
    assert order.status == "pending"


def test_webhook_vk_mismatch(client, db, monkeypatch):
    _setup_config(monkeypatch)
    order = _make_gateway_order(db, quantity=1)
    body = _webhook_body(order, vk_id=999)
    resp = _post(client, body, _sig(body))
    assert resp.status_code == 400
    db.refresh(order)
    assert order.status == "pending"


def test_webhook_game_mismatch(client, db, monkeypatch):
    _setup_config(monkeypatch)
    order = _make_gateway_order(db, quantity=1)
    body = _webhook_body(order, game_id="other-game")
    resp = _post(client, body, _sig(body))
    assert resp.status_code == 400
    assert resp.json()["detail"] == "game mismatch"


def test_webhook_not_configured(client, db, monkeypatch):
    monkeypatch.setattr(config, "PAY_GATEWAY_WEBHOOK_SECRET", "")
    order = _make_gateway_order(db, quantity=1)
    body = _webhook_body(order)
    resp = _post(client, body, _sig(body))
    assert resp.status_code == 503


def test_webhook_recovers_cancelled_order(client, db, monkeypatch):
    _setup_config(monkeypatch)
    order = _make_gateway_order(db, quantity=1, status="cancelled")
    body = _webhook_body(order)
    resp = _post(client, body, _sig(body))
    assert resp.status_code == 200
    db.refresh(order)
    assert order.status == "success"
    assert len(json.loads(order.dragon_ids)) == 1
    log = db.query(PaymentLog).filter(
        PaymentLog.order_id == order.id,
        PaymentLog.action == "gateway_recovered_cancelled",
    ).first()
    assert log is not None


def test_webhook_fail_status_skips_fulfillment(client, db, monkeypatch):
    _setup_config(monkeypatch)
    order = _make_gateway_order(db, quantity=1, status="fail")
    body = _webhook_body(order)
    resp = _post(client, body, _sig(body))
    assert resp.status_code == 200
    db.refresh(order)
    assert order.status == "fail"
    assert json.loads(order.dragon_ids) == []
    log = db.query(PaymentLog).filter(
        PaymentLog.order_id == order.id,
        PaymentLog.action == "gateway_webhook_fail_skipped",
    ).first()
    assert log is not None


def test_webhook_missing_txn(client, db, monkeypatch):
    _setup_config(monkeypatch)
    payload = json.dumps({"game_id": "dragons", "vk_id": 1, "amount_kop": 100,
                          "status": "success"}).encode()
    resp = _post(client, payload, _sig(payload))
    assert resp.status_code == 400
