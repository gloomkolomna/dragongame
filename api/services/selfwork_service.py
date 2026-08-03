"""Selfwork (Сам.Эквайринг) provider: init payment, verify webhook, get status."""

import hashlib
import urllib.request
import urllib.parse
import json


def get_active_provider(db) -> str:
    from models import AppSettings
    cfg = db.query(AppSettings).filter(AppSettings.id == 1).first()
    if not cfg or not cfg.payment_provider:
        return "robokassa"
    return cfg.payment_provider


def selfwork_order_id_for(order_id: int) -> str:
    return f"dragons-{order_id}"


def order_id_from_selfwork(sw_id: str):
    if not sw_id or not isinstance(sw_id, str):
        return None
    prefix = "dragons-"
    if not sw_id.startswith(prefix):
        return None
    rest = sw_id[len(prefix):]
    try:
        return int(rest)
    except (ValueError, TypeError):
        return None


def _sha256_hex(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_init_signature(order_id: str, amount, info_items: list, api_key: str) -> str:
    raw = f"{order_id}{amount}"
    for item in info_items:
        raw += f"{item['name']}{item['quantity']}{item['amount']}"
    raw += api_key
    return _sha256_hex(raw)


def verify_webhook_signature(order_id: str, amount, api_key: str, signature: str) -> bool:
    if api_key is None or signature is None:
        return False
    expected = _sha256_hex(f"{order_id}{amount}{api_key}")
    return expected.lower() == (signature or "").lower()


def call_init(order, description: str) -> str:
    import config
    api_key = config.SELFWORK_API_KEY
    order_id = selfwork_order_id_for(order.id)
    amount = str(order.amount_rub)
    info_items = [{
        "name": f"{description or 'Набор драконов'}",
        "quantity": 1,
        "amount": order.amount_rub,
    }]
    signature = build_init_signature(order_id, amount, info_items, api_key)

    fields = {
        "order_id": order_id,
        "amount": amount,
        "signature": signature,
    }
    for i, item in enumerate(info_items):
        fields[f"info[{i}][name]"] = item["name"]
        fields[f"info[{i}][quantity]"] = str(item["quantity"])
        fields[f"info[{i}][amount]"] = str(item["amount"])

    data = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        config.SELFWORK_INIT_URL,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": config.SELFWORK_ORIGIN + "/",
            "Referer": config.SELFWORK_ORIGIN,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def get_status(order_id: str) -> dict:
    import config
    api_key = config.SELFWORK_API_KEY
    shop_id = config.SELFWORK_SHOP_ID
    auth = urllib.request.HTTPBasicAuthHandler()
    password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    full_url = f"{config.SELFWORK_STATUS_URL}?{urllib.parse.urlencode({'order_id': order_id})}"
    password_mgr.add_password(None, config.SELFWORK_STATUS_URL, shop_id, api_key)
    auth.add_password(None, config.SELFWORK_STATUS_URL, shop_id, api_key)
    opener = urllib.request.build_opener(auth)
    req = urllib.request.Request(full_url, method="GET")
    with opener.open(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))
