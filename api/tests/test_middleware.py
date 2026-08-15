from db import SessionLocal
from models import ApiRequestLog


def test_api_request_log_captures_detail(client):
    resp = client.post("/api/payment/result", data={})
    assert resp.status_code == 400

    s = SessionLocal()
    try:
        log = s.query(ApiRequestLog).order_by(ApiRequestLog.id.desc()).first()
        assert log is not None
        assert log.path == "/api/payment/result"
        assert log.status_code == 400
        assert log.response_detail == "bad params"
    finally:
        s.close()


def test_api_request_log_captures_query_params(client):
    resp = client.get("/api/payment/pay/99999", params={"vk_id": "77"})
    assert resp.status_code == 404

    s = SessionLocal()
    try:
        log = s.query(ApiRequestLog).order_by(ApiRequestLog.id.desc()).first()
        assert log is not None
        assert log.path == "/api/payment/pay/99999"
        assert log.status_code == 404
        assert "vk_id=77" in log.query_params
    finally:
        s.close()


def test_api_request_log_captures_form_body(client):
    resp = client.post("/api/payment/result", data={"OutSum": "10", "InvId": "5"})
    assert resp.status_code == 400

    s = SessionLocal()
    try:
        log = s.query(ApiRequestLog).order_by(ApiRequestLog.id.desc()).first()
        assert log is not None
        assert "OutSum=10" in log.request_body
        assert "InvId=5" in log.request_body
    finally:
        s.close()


def test_json_body_reaches_endpoint_through_middleware(client, monkeypatch):
    from models import Dragon
    import routes.admin as admin_module
    monkeypatch.setattr(admin_module, "_resolve_vk_name", lambda vk_url: "")

    s = SessionLocal()
    try:
        d = Dragon(name="MW", rarity=1, steps_count=1, is_active=True, pin_code="71717")
        s.add(d)
        s.commit()
        dragon_id = d.id
    finally:
        s.close()

    resp = client.post("/api/admin/reservations", json={"vk_url": "https://vk.ru/id193917440", "dragon_id": dragon_id, "notes": ""})
    assert resp.status_code == 200
    assert resp.json()["vk_user_id"] == 193917440
    assert resp.json()["pin_code"] == "71717"

    resp = client.post("/api/admin/reservations", json={"vk_url": "https://vk.ru/id193917440", "dragon_id": dragon_id, "notes": ""})
    assert resp.status_code == 400

    s = SessionLocal()
    try:
        log = s.query(ApiRequestLog).order_by(ApiRequestLog.id.desc()).first()
        assert log is not None
        assert "vk.ru/id193917440" in log.request_body
    finally:
        s.close()
