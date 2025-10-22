import secrets

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger, log_security_event

logger = get_logger(__name__)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Provides API key-based authentication for HTTP requests.

    This middleware intercepts incoming requests and validates the API key
    provided in the `X-API-Key` header. It is designed to be a simple and
    secure way to protect API endpoints.

    Authentication is skipped for OPTIONS requests and for a predefined set of
    exempt paths, such as health checks and documentation. If no API key is
    configured in the application settings, this middleware becomes a no-op,
    allowing all requests to pass through, which is useful for local development.

    Attributes:
        header_name: The name of the HTTP header containing the API key.
        settings: The application's configuration settings.
        exempt_paths: A set of paths that do not require authentication.
    """

    def __init__(self, app, header_name: str = "X-API-Key"):
        """Initializes the API key authentication middleware.

        Args:
            app: The ASGI application instance.
            header_name: The name of the header to check for the API key.
        """
        super().__init__(app)
        self.header_name = header_name
        self.settings = get_settings()
        # Paths to skip authentication (public endpoints)
        self.exempt_paths = {"/metrics", "/health", "/docs", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        """Processes an incoming request to validate the API key.

        This method contains the core logic of the middleware. It checks for
        the API key, compares it with the expected key in a secure manner, and
        either forwards the request to the next middleware or returns a 401
        Unauthorized response.

        Args:
            request: The incoming `Request` object.
            call_next: A function to call to pass the request to the next
                middleware or the application.

        Returns:
            The response from the next middleware or a `JSONResponse` if
            authentication fails.
        """
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
        # Use constant-time comparison to prevent timing attacks
        if not provided or not secrets.compare_digest(provided, expected):
            log_security_event(
                logger,
                "auth_failure",
                {"path": request.url.path, "provided_key": bool(provided)},
            )
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        return await call_next(request)
