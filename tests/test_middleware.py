"""Unit tests for the API authentication middleware.

This module contains test cases for the `APIKeyAuthMiddleware`, verifying that
it correctly protects endpoints when an API key is configured and allows
access when it is not.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.middleware.auth import APIKeyAuthMiddleware
from app.core.config import Settings


def test_middleware_allows_when_no_api_key():
    """Tests that the middleware allows access when no API key is configured.

    This test ensures that if the `api_key` setting is `None`, the middleware
    does not block requests, effectively disabling authentication.
    """
    settings = Settings()
    settings.api_key = None

    app = FastAPI()
    app.add_middleware(APIKeyAuthMiddleware, settings=settings)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_middleware_rejects_bad_key_and_accepts_good_key():
    """Tests that the middleware rejects requests with a missing or incorrect API key
    and accepts requests with the correct key when authentication is enabled.
    """
    app = FastAPI()
    # In a real scenario, this would be managed by a dependency injection
    # system that could be easily overridden. For this test, we'll
    # temporarily modify the global settings object.
    from app.core.config import settings as global_settings

    original_key = global_settings.api_key
    try:
        global_settings.api_key = "secret-test-key"
        app.add_middleware(APIKeyAuthMiddleware, settings=global_settings)

        @app.get("/protected")
        def protected():
            return {"status": "ok"}

        client = TestClient(app)

        # Test 1: No API key provided
        resp_no_key = client.get("/protected")
        assert resp_no_key.status_code == 401

        # Test 2: Incorrect API key provided
        resp_bad_key = client.get("/protected", headers={"X-API-Key": "wrong-key"})
        assert resp_bad_key.status_code == 401

        # Test 3: Correct API key provided
        resp_good_key = client.get("/protected", headers={"X-API-Key": "secret-test-key"})
        assert resp_good_key.status_code == 200
    finally:
        # Restore the original settings to avoid side effects
        global_settings.api_key = original_key
