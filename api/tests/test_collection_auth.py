import base64
import hashlib
import hmac

import auth as auth_module


SECRET = "test-app-secret"


def make_sign(params: dict, secret: str = SECRET) -> str:
    vk_params = {k: v for k, v in params.items() if k.startswith("vk_") and k != "vk_id"}
    qs = "&".join(f"{k}={vk_params[k]}" for k in sorted(vk_params))
    digest = hmac.new(secret.encode(), qs.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def signed_params(vk_user_id: int, secret: str = SECRET) -> dict:
    params = {"vk_user_id": str(vk_user_id), "vk_app_id": "12345", "vk_platform": "desktop_web"}
    params["sign"] = make_sign(params, secret)
    return params


def enable_prod(monkeypatch):
    monkeypatch.setattr(auth_module, "APP_ENV", "production")
    monkeypatch.setattr(auth_module, "VK_APP_SECRET", SECRET)


def test_valid_sign_allows_balance(client, monkeypatch):
    enable_prod(monkeypatch)
    resp = client.get("/api/collection/123/balance", params=signed_params(123))
    assert resp.status_code == 200
    assert resp.json()["stitches_balance"] == 0


def test_no_sign_forbidden(client, monkeypatch):
    enable_prod(monkeypatch)
    resp = client.get("/api/collection/123/balance")
    assert resp.status_code == 403


def test_invalid_sign_forbidden(client, monkeypatch):
    enable_prod(monkeypatch)
    resp = client.get("/api/collection/123/balance", params=signed_params(123, secret="wrong"))
    assert resp.status_code == 403


def test_foreign_sign_forbidden(client, monkeypatch):
    enable_prod(monkeypatch)
    resp = client.get("/api/collection/123/balance", params=signed_params(999))
    assert resp.status_code == 403


def test_dev_mode_allows_without_sign(client):
    resp = client.get("/api/collection/123/balance")
    assert resp.status_code == 200


def test_disabled_flag_allows_without_sign(client, monkeypatch):
    enable_prod(monkeypatch)
    monkeypatch.setattr(auth_module, "REQUIRE_VK_SIGN", False)
    resp = client.get("/api/collection/123/balance")
    assert resp.status_code == 200


def test_enabled_flag_still_blocks_without_sign(client, monkeypatch):
    enable_prod(monkeypatch)
    monkeypatch.setattr(auth_module, "REQUIRE_VK_SIGN", True)
    resp = client.get("/api/collection/123/balance")
    assert resp.status_code == 403


def test_dragon_endpoint_checks_sign(client, monkeypatch):
    enable_prod(monkeypatch)
    resp = client.get("/api/dragon/1", params={"vk_id": 123})
    assert resp.status_code == 403

    resp = client.get("/api/dragon/1", params={"vk_id": 123, **signed_params(123)})
    assert resp.status_code == 200


def test_public_pricing_stays_open(client, monkeypatch):
    enable_prod(monkeypatch)
    resp = client.get("/api/public/pricing")
    assert resp.status_code == 200
