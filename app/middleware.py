from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import get_settings
from .logging_config import get_logger, log_security_event

logger = get_logger(__name__)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Simple API key authentication middleware.

    The middleware checks for an `X-API-Key` header and validates it
    against the configured `api_key` in settings. If no API key is set
    in configuration, the middleware is a no-op (useful for local dev).
    """

    def __init__(self, app, header_name: str = "X-API-Key"):
        super().__init__(app)
        self.header_name = header_name
        self.settings = get_settings()
        # Paths to skip authentication (public endpoints)
        self.exempt_paths = {"/metrics", "/health", "/docs", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        expected = self.settings.api_key
        # Allow OPTIONS preflight without auth
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip authentication for exempt paths
        path = request.url.path
        if any(path.startswith(p) for p in self.exempt_paths):
            return await call_next(request)
        # If no API key configured, allow all requests (dev mode)
        if not expected:
            return await call_next(request)

        provided = request.headers.get(self.header_name)
        if not provided or provided != expected:
            log_security_event(
                logger,
                "auth_failure",
                {"path": request.url.path, "provided_key": bool(provided)},
            )
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        return await call_next(request)
