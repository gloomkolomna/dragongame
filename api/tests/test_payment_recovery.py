from datetime import datetime, timedelta

import config
from models import Dragon, DragonSet, PaymentOrder, PaymentLog


def _dragon(db, name, pin):
    d = Dragon(name=name, egg_type="egg", rarity=1, steps_count=1,
               pin_code=pin, family_id=None, is_active=True)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def _make_gateway_order(db, vk_id=42, quantity=2, created_minutes_ago=15,
                        txn="20260824-000001", status="pending"):
    for i in range(quantity + 2):
        _dragon(db, f"D{i}", pin=f"RC{i:04d}")
    s = DragonSet(name="2 драконов", quantity=quantity, discount_percent=5,
                  donor_discount_percent=15, is_active=True)
    db.add(s)
    db.commit()
    db.refresh(s)
    order = PaymentOrder(
        vk_id=vk_id, set_id=s.id, amount_rub=quantity * 9500, quantity=quantity,
        price_per_pin=9500, provider="gateway", status=status, dragon_ids="[]",
        gateway_txn_id=txn,
        created_at=(datetime.now() - timedelta(minutes=created_minutes_ago)
                    ).strftime("%Y-%m-%dT%H:%M:%S"),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def _setup(monkeypatch, gateway_status="success", amount=None):
    monkeypatch.setattr(config, "USE_PAY_GATEWAY", True)
    monkeypatch.setattr(config, "PAY_GATEWAY_API_KEY", "gamekey")
    monkeypatch.setattr(config, "VK_GROUP_TOKEN", "")
    from services import pay_gateway_client
    calls = []

    def fake_get_order(txn):
        calls.append(txn)
        return {
            "transaction_id": txn,
            "game_id": "dragons",
            "status": gateway_status,
            "amount_kop": amount if amount is not None else 19000,
            "paid_at": "2026-08-24 12:03:00",
        }

    monkeypatch.setattr(pay_gateway_client, "get_order", fake_get_order)
    return calls


def test_recovery_fulfills_gateway_success(db, monkeypatch):
    order = _make_gateway_order(db, quantity=2)
    calls = _setup(monkeypatch, amount=order.amount_rub)

    from routes.payment import recover_pending_gateway_orders
    recovered = recover_pending_gateway_orders(db)

    assert [o.id for o in recovered] == [order.id]
    assert calls == [order.gateway_txn_id]
    db.refresh(order)
    assert order.status == "success"
    import json
    assert len(json.loads(order.dragon_ids)) == 2
    log = db.query(PaymentLog).filter(
        PaymentLog.order_id == order.id,
        PaymentLog.action == "gateway_recovered_by_poller",
    ).first()
    assert log is not None


def test_recovery_ignores_fresh_orders(db, monkeypatch):
    _make_gateway_order(db, created_minutes_ago=3)
    calls = _setup(monkeypatch)

    from routes.payment import recover_pending_gateway_orders
    recovered = recover_pending_gateway_orders(db)

    assert recovered == []
    assert calls == []


def test_recovery_ignores_orders_without_gateway(db, monkeypatch):
    order = _make_gateway_order(db, txn=None)
    calls = _setup(monkeypatch)

    from routes.payment import recover_pending_gateway_orders
    recovered = recover_pending_gateway_orders(db)

    assert recovered == []
    assert calls == []
    db.refresh(order)
    assert order.status == "pending"


def test_recovery_gateway_pending_keeps_local_pending(db, monkeypatch):
    order = _make_gateway_order(db)
    _setup(monkeypatch, gateway_status="pending")

    from routes.payment import recover_pending_gateway_orders
    recovered = recover_pending_gateway_orders(db)

    assert recovered == []
    db.refresh(order)
    assert order.status == "pending"


def test_recovery_gateway_cancelled_keeps_local_pending(db, monkeypatch):
    order = _make_gateway_order(db)
    _setup(monkeypatch, gateway_status="cancelled")

    from routes.payment import recover_pending_gateway_orders
    recover_pending_gateway_orders(db)

    db.refresh(order)
    assert order.status == "pending"


def test_recovery_amount_mismatch_keeps_pending(db, monkeypatch):
    order = _make_gateway_order(db)
    _setup(monkeypatch, amount=order.amount_rub + 100)

    from routes.payment import recover_pending_gateway_orders
    recover_pending_gateway_orders(db)

    db.refresh(order)
    assert order.status == "pending"
    log = db.query(PaymentLog).filter(
        PaymentLog.order_id == order.id,
        PaymentLog.action == "gateway_amount_mismatch",
    ).first()
    assert log is not None


def test_recovery_gateway_error_logged_and_kept_pending(db, monkeypatch):
    order = _make_gateway_order(db)
    monkeypatch.setattr(config, "USE_PAY_GATEWAY", True)
    monkeypatch.setattr(config, "PAY_GATEWAY_API_KEY", "gamekey")
    from services import pay_gateway_client
    from services.pay_gateway_client import PayGatewayError
    monkeypatch.setattr(pay_gateway_client, "get_order",
                        lambda txn: (_ for _ in ()).throw(PayGatewayError("http 500: boom")))

    from routes.payment import recover_pending_gateway_orders
    recovered = recover_pending_gateway_orders(db)

    assert recovered == []
    db.refresh(order)
    assert order.status == "pending"
    log = db.query(PaymentLog).filter(
        PaymentLog.order_id == order.id,
        PaymentLog.action == "gateway_poll_error",
    ).first()
    assert log is not None
    assert "500" in log.detail


def test_recovery_disabled_without_flag(db, monkeypatch):
    _make_gateway_order(db)
    monkeypatch.setattr(config, "USE_PAY_GATEWAY", False)
    monkeypatch.setattr(config, "PAY_GATEWAY_API_KEY", "gamekey")
    from services import pay_gateway_client
    calls = []
    monkeypatch.setattr(pay_gateway_client, "get_order",
                        lambda txn: calls.append(txn) or {})

    from routes.payment import recover_pending_gateway_orders
    assert recover_pending_gateway_orders(db) == []
    assert calls == []


def test_recovery_skips_already_success(db, monkeypatch):
    order = _make_gateway_order(db, status="success")
    calls = _setup(monkeypatch, amount=order.amount_rub)

    from routes.payment import recover_pending_gateway_orders
    assert recover_pending_gateway_orders(db) == []
    assert calls == []


def test_recovery_poller_disabled_in_testing(db, monkeypatch):
    from services.payment_recovery import start_payment_recovery
    start_payment_recovery(lambda: None, interval=60)
