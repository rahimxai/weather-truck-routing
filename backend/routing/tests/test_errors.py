from django.urls import path


def boom(request):
    raise RuntimeError("boom")


urlpatterns = [path("boom", boom)]
handler500 = "routing.api.errors.server_error"


def test_unknown_route_is_json_404(client):
    resp = client.get("/api/nope")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


def test_trailing_slash_is_404(client):
    assert client.get("/api/health/").status_code == 404


def test_bad_host_is_json_400(client):
    resp = client.get("/api/health", HTTP_HOST="evil.com")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_REQUEST"


def test_crash_is_json_500(client, settings):
    settings.ROOT_URLCONF = __name__
    client.raise_request_exception = False
    resp = client.get("/boom")
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "SERVER_ERROR"
    assert "boom" not in resp.content.decode()
