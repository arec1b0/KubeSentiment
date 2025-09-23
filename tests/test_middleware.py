import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware import APIKeyAuthMiddleware
from app.config import Settings


def test_middleware_allows_when_no_api_key():
    settings = Settings()
    settings.api_key = None

    app = FastAPI()
    app.add_middleware(APIKeyAuthMiddleware)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_middleware_rejects_bad_key():
    app = FastAPI()
    # Use a settings instance with an api_key via environment or patching would be better
    # We'll set via monkeypatch approach by setting env var
    # But the middleware reads get_settings(); easiest approach is to instantiate and patch attribute
    from app.config import settings as global_settings

    original = global_settings.api_key
    try:
        global_settings.api_key = "secret"
        app.add_middleware(APIKeyAuthMiddleware)

        @app.get("/protected")
        def protected():
            return {"status": "ok"}

        client = TestClient(app)
        resp = client.get("/protected")
        assert resp.status_code == 401

        # Provide correct key
        resp2 = client.get("/protected", headers={"X-API-Key": "secret"})
        assert resp2.status_code == 200
    finally:
        global_settings.api_key = original
