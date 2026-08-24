import json
import hmac
import hashlib

import httpx

import config
from services import pay_gateway_client
from services.pay_gateway_client import (
    PayGatewayBlocked, PayGatewayError, create_order, get_order,
)


class _Resp:
    def __init__(self, status_code=200, data=None, text="", bad_json=False):
        self.status_code = status_code
        self._data = data if data is not None else {}
        self.text = text or json.dumps(self._data)
        self._bad_json = bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("bad json")
        return self._data


def _setup(monkeypatch):
    monkeypatch.setattr(config, "PAY_GATEWAY_URL", "https://gw.example/pay")
    monkeypatch.setattr(config, "PAY_GATEWAY_API_KEY", "gamekey")
    monkeypatch.setattr(config, "PAY_GATEWAY_GAME_ID", "dragons")
    monkeypatch.setattr(config, "PAY_GATEWAY_TIMEOUT_SECONDS", 5)


def _capture_request(monkeypatch, resp=None, raises=None):
    calls = []

    def fake_request(method, url, content=None, headers=None, timeout=None):
        calls.append({
            "method": method, "url": url, "content": content,
            "headers": headers, "timeout": timeout,
        })
        if raises is not None:
            raise raises
        return resp or _Resp(201, {"ok": True})

    monkeypatch.setattr(pay_gateway_client.httpx, "request", fake_request)
    return calls


def test_create_order_signs_raw_body(monkeypatch):
    _setup(monkeypatch)
    calls = _capture_request(monkeypatch, _Resp(201, {
        "transaction_id": "20260824-000001",
        "payment_url": "https://gw.example/pay/20260824-000001",
        "amount_kop": 47500,
        "expires_at": "2026-08-24T13:00:00+03:00",
    }))

    info = create_order(7, 47500, "Набор цифровых товаров «5 драконов»", "Buyer@Example.com")

    assert info["transaction_id"] == "20260824-000001"
    call = calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "https://gw.example/pay/pay/orders"
    assert call["timeout"] == 5
    body = call["content"]
    sent = json.loads(body)
    assert sent == {
        "vk_id": 7,
        "amount_kop": 47500,
        "description": "Набор цифровых товаров «5 драконов»",
        "receipt_email": "buyer@example.com",
    }
    headers = call["headers"]
    assert headers["X-Game-Id"] == "dragons"
    assert headers["X-Timestamp"].isdigit()
    expected = hmac.new(b"gamekey", body, hashlib.sha256).hexdigest()
    assert headers["X-Game-Signature"] == expected


def test_create_order_without_email_omits_field(monkeypatch):
    _setup(monkeypatch)
    calls = _capture_request(monkeypatch)
    create_order(7, 100, "Набор")
    sent = json.loads(calls[0]["content"])
    assert "receipt_email" not in sent


def test_get_order_signs_empty_body(monkeypatch):
    _setup(monkeypatch)
    calls = _capture_request(monkeypatch, _Resp(200, {
        "transaction_id": "20260824-000001", "game_id": "dragons",
        "status": "success", "amount_kop": 47500, "paid_at": "2026-08-24 12:03:00",
    }))

    info = get_order("20260824-000001")

    assert info["status"] == "success"
    call = calls[0]
    assert call["method"] == "GET"
    assert call["url"] == "https://gw.example/pay/pay/orders/20260824-000001"
    assert call["content"] == b""
    expected = hmac.new(b"gamekey", b"", hashlib.sha256).hexdigest()
    assert call["headers"]["X-Game-Signature"] == expected


def test_test_blocked_raises_blocked(monkeypatch):
    _setup(monkeypatch)
    _capture_request(monkeypatch, _Resp(403, {"error": "test_blocked"}))
    try:
        create_order(7, 100, "Набор")
        assert False, "должен бросить PayGatewayBlocked"
    except PayGatewayBlocked:
        pass


def test_http_error_raises(monkeypatch):
    _setup(monkeypatch)
    _capture_request(monkeypatch, _Resp(500, {}, text="Internal Server Error"))
    try:
        create_order(7, 100, "Набор")
        assert False, "должен бросить PayGatewayError"
    except PayGatewayError as exc:
        assert "500" in str(exc)


def test_other_403_raises_generic_error(monkeypatch):
    _setup(monkeypatch)
    _capture_request(monkeypatch, _Resp(403, {"error": "game disabled"}))
    try:
        create_order(7, 100, "Набор")
        assert False, "должен бросить PayGatewayError"
    except PayGatewayBlocked:
        assert False, "не PayGatewayBlocked"
    except PayGatewayError:
        pass


def test_network_error_raises(monkeypatch):
    _setup(monkeypatch)
    _capture_request(monkeypatch, raises=httpx.ConnectError("refused"))
    try:
        create_order(7, 100, "Набор")
        assert False, "должен бросить PayGatewayError"
    except PayGatewayError as exc:
        assert "network" in str(exc)


def test_bad_json_raises(monkeypatch):
    _setup(monkeypatch)
    _capture_request(monkeypatch, _Resp(200, bad_json=True))
    try:
        get_order("20260824-000001")
        assert False, "должен бросить PayGatewayError"
    except PayGatewayError:
        pass
