def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_hides_key(client, settings):
    settings.TOMTOM_API_KEY = "secret-123"
    resp = client.get("/api/health")
    assert resp.json()["tomtom_key"] is True
    assert "secret-123" not in resp.content.decode()


def test_health_reports_missing_key(client, settings):
    settings.TOMTOM_API_KEY = ""
    assert client.get("/api/health").json()["tomtom_key"] is False


def test_health_head_ok(client):
    assert client.head("/api/health").status_code == 200


def test_health_rejects_post(client):
    assert client.post("/api/health").status_code == 405
