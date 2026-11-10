import pytest

from routing.adapters import http, open_meteo, tomtom

from .fakes import FakeApis


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda s: None)


@pytest.fixture
def apis(monkeypatch, settings):
    settings.TOMTOM_API_KEY = "test-key-123"
    fake = FakeApis()
    monkeypatch.setattr(tomtom, "make_client", fake.client)
    monkeypatch.setattr(open_meteo, "make_client", fake.client)
    return fake
