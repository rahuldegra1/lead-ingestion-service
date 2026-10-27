from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_create_lead_success_and_sanitization(client: TestClient):
    payload = {
        "full_name": "  kavita sharma  ",
        "email": "KAVITA@VENTURES.CO",
        "budget_inr": "₹1,25,000",
        "phone": "+91 987-654-3210",
    }
    response = client.post("/leads", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] == 1
    assert data["full_name"] == "Kavita Sharma"
    assert data["email"] == "kavita@ventures.co"
    assert data["budget_inr"] == 125000
    assert data["phone"] == "9876543210"


def test_create_lead_validation_failure(client: TestClient):
    invalid_payload = {
        "full_name": "Test User",
        "email": "invalid-email-no-at-symbol",
        "budget_inr": -500,
        "phone": "123",
    }
    response = client.post("/leads", json=invalid_payload)
    assert response.status_code == 422


def test_get_lead_not_found(client: TestClient):
    response = client.get("/leads/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Lead with ID 999 not found"


def test_update_lead_partial(client: TestClient):
    create_res = client.post(
        "/leads",
        json={
            "full_name": "Rohan Das",
            "email": "rohan@test.com",
            "budget_inr": 50000,
            "phone": "9876543210",
        },
    )
    lead_id = create_res.json()["id"]

    update_res = client.patch(f"/leads/{lead_id}", json={"budget_inr": "₹75,000"})
    assert update_res.status_code == 200
    assert update_res.json()["budget_inr"] == 75000
    assert update_res.json()["full_name"] == "Rohan Das"


def test_delete_lead(client: TestClient):
    create_res = client.post(
        "/leads",
        json={
            "full_name": "Delete Me",
            "email": "delete@test.com",
            "budget_inr": 20000,
            "phone": "9998887776",
        },
    )
    lead_id = create_res.json()["id"]

    delete_res = client.delete(f"/leads/{lead_id}")
    assert delete_res.status_code == 204
    assert delete_res.text == ""

    get_res = client.get(f"/leads/{lead_id}")
    assert get_res.status_code == 404


def test_pagination_and_filtering(client: TestClient):
    client.post(
        "/leads",
        json={
            "full_name": "User Low",
            "email": "low@a.com",
            "budget_inr": 10000,
            "phone": "1111111111",
        },
    )
    client.post(
        "/leads",
        json={
            "full_name": "User Mid",
            "email": "mid@b.com",
            "budget_inr": 50000,
            "phone": "2222222222",
        },
    )
    client.post(
        "/leads",
        json={
            "full_name": "User High",
            "email": "high@c.com",
            "budget_inr": 100000,
            "phone": "3333333333",
        },
    )

    res = client.get("/leads?min_budget=40000")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] == 2
    assert len(data["data"]) == 2

    res_paginated = client.get("/leads?limit=1")
    assert res_paginated.status_code == 200
    assert len(res_paginated.json()["data"]) == 1
    assert res_paginated.json()["data"][0]["budget_inr"] == 100000


def test_observability_middleware_headers(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Process-Time" in response.headers
    assert response.headers["X-Process-Time"].endswith("ms")


def test_health_check_database_failure(client: TestClient):
    with patch.object(Session, "execute", side_effect=Exception("Database down")):
        response = client.get("/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert "error" in data


def test_prometheus_metrics_endpoint(client: TestClient):
    client.get("/health")

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    assert (
        "http_requests_total" in response.text
        or "http_request_duration_seconds" in response.text
    )


def test_rate_limit_exceeded_on_create_lead(client: TestClient):
    payload = {
        "full_name": "Test Burst",
        "email": "burst@example.com",
        "phone": "+91 99999-88888",
        "budget_inr": "1,00,000",
    }

    for _ in range(5):
        resp = client.post("/leads", json=payload)
        assert resp.status_code == 201

    rate_limited_resp = client.post("/leads", json=payload)
    assert rate_limited_resp.status_code == 429
    assert "Rate limit exceeded" in rate_limited_resp.text


def test_lead_routes_reject_missing_or_invalid_api_key(
    unauthenticated_client: TestClient,
):
    # Missing header on protected route
    res_missing = unauthenticated_client.post(
        "/leads",
        json={
            "full_name": "Unauthorized User",
            "email": "unauth@example.com",
            "phone": "9876543210",
            "budget_inr": "50000",
        },
    )
    assert res_missing.status_code == 401
    assert res_missing.json()["detail"] == "Invalid or missing API Key"

    # Invalid API key token
    res_invalid = unauthenticated_client.get(
        "/leads",
        headers={"X-API-Key": "invalid-dummy-key"},
    )
    assert res_invalid.status_code == 401
    assert res_invalid.json()["detail"] == "Invalid or missing API Key"


def test_public_routes_remain_accessible_without_auth(
    unauthenticated_client: TestClient,
):
    # Health probe
    res_health = unauthenticated_client.get("/health")
    assert res_health.status_code == 200

    # Prometheus metrics scraper
    res_metrics = unauthenticated_client.get("/metrics")
    assert res_metrics.status_code == 200


def test_global_exception_handler(client: TestClient):
    client_no_raise = TestClient(
        app,
        headers={"X-API-Key": "prod-secret-lead-ingest-key-2026"},
        raise_server_exceptions=False,
    )
    with patch(
        "app.routers.leads.LeadDB",
        side_effect=RuntimeError("Database pool crashed"),
    ):
        payload = {
            "full_name": "Test User",
            "email": "test@example.com",
            "budget_inr": 100000,
            "phone": "9876543210",
        }
        response = client_no_raise.post("/leads", json=payload)
        assert response.status_code == 500
