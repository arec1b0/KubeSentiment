#!/usr/bin/env python3
"""
Healthcheck script for distroless Docker containers.

This script performs a health check on the FastAPI application by making an
HTTP request to the /health endpoint. It's designed to work in distroless
containers where curl and other shell utilities are not available.

Exit codes:
    0: Service is healthy
    1: Service is unhealthy or unreachable

Usage:
    python healthcheck.py [--host HOST] [--port PORT] [--path PATH] [--timeout TIMEOUT]

Environment variables:
    HEALTHCHECK_HOST: Host to check (default: localhost)
    HEALTHCHECK_PORT: Port to check (default: 8000)
    HEALTHCHECK_PATH: Health endpoint path (default: /health)
    HEALTHCHECK_TIMEOUT: Request timeout in seconds (default: 5)
"""

import argparse
import http.client
import os
import sys
from typing import NoReturn


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="FastAPI healthcheck for distroless containers")
    parser.add_argument(
        "--host",
        default=os.getenv("HEALTHCHECK_HOST", "localhost"),
        help="Host to check (default: localhost or HEALTHCHECK_HOST env var)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("HEALTHCHECK_PORT", "8000")),
        help="Port to check (default: 8000 or HEALTHCHECK_PORT env var)",
    )
    parser.add_argument(
        "--path",
        default=os.getenv("HEALTHCHECK_PATH", "/health"),
        help="Health endpoint path (default: /health or HEALTHCHECK_PATH env var)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("HEALTHCHECK_TIMEOUT", "5")),
        help="Request timeout in seconds (default: 5 or HEALTHCHECK_TIMEOUT env var)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    return parser.parse_args()


def check_health(host: str, port: int, path: str, timeout: int, verbose: bool = False) -> bool:
    """
    Perform health check by making HTTP request.

    Args:
        host: Host to check
        port: Port to check
        path: Health endpoint path
        timeout: Request timeout in seconds
        verbose: Enable verbose output

    Returns:
        True if service is healthy, False otherwise
    """
    try:
        if verbose:
            print(f"Connecting to {host}:{port}{path}", file=sys.stderr)

        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", path)
        response = conn.getresponse()

        if verbose:
            print(f"Response status: {response.status}", file=sys.stderr)
            print(f"Response reason: {response.reason}", file=sys.stderr)

        # Consider 200-299 status codes as healthy
        is_healthy = 200 <= response.status < 300

        if verbose and is_healthy:
            body = response.read().decode("utf-8")
            print(f"Response body: {body}", file=sys.stderr)

        conn.close()
        return is_healthy

    except http.client.HTTPException as e:
        if verbose:
            print(f"HTTP error: {e}", file=sys.stderr)
        return False
    except OSError as e:
        if verbose:
            print(f"Connection error: {e}", file=sys.stderr)
        return False
    except Exception as e:
        if verbose:
            print(f"Unexpected error: {e}", file=sys.stderr)
        return False


def main() -> NoReturn:
    """Main entry point."""
    args = parse_args()

    is_healthy = check_health(
        host=args.host,
        port=args.port,
        path=args.path,
        timeout=args.timeout,
        verbose=args.verbose,
    )

    if is_healthy:
        if args.verbose:
            print("✓ Service is healthy", file=sys.stderr)
        sys.exit(0)
    else:
        if args.verbose:
            print("✗ Service is unhealthy", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
