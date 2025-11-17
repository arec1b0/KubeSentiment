"""Pytest configuration and shared fixtures for the test suite.

This module provides the main pytest configuration and imports shared
fixtures that are available to all test files.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import shared fixtures so they're available to all tests
pytest_plugins = [
    "tests.fixtures.common_fixtures",
]


# You can add session-scoped fixtures here if needed
# Example:
# @pytest.fixture(scope="session")
# def session_fixture():
#     """Session-scoped fixture that runs once per test session."""
#     pass
