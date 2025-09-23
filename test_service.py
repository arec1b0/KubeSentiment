#!/usr/bin/env python3
"""
Test script for the MLOps sentiment analysis service.

This script tests all endpoints to ensure the service is working correctly.
"""

import requests
import time


def run_endpoint(url, method="GET", data=None, description=""):
    """Run an API endpoint check (helper for manual testing)."""
    print(f"🧪 Testing {description}: {method} {url}")

    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)

        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")

        if response.status_code == 200:
            print("   ✅ Success")
        else:
            print("   ❌ Failed")

        return response.status_code == 200

    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 MLOps Service Test Suite")
    print("=" * 40)

    base_url = "http://localhost:8000"

    # Wait for server to be ready
    print("⏳ Waiting for server to be ready...")
    time.sleep(2)

    tests = [
        {"url": f"{base_url}/health", "method": "GET", "description": "Health Check"},
        {"url": f"{base_url}/metrics", "method": "GET", "description": "Metrics"},
        {
            "url": f"{base_url}/predict",
            "method": "POST",
            "data": {"text": "I love this amazing service!"},
            "description": "Positive Sentiment Prediction",
        },
        {
            "url": f"{base_url}/predict",
            "method": "POST",
            "data": {"text": "I hate this terrible product."},
            "description": "Negative Sentiment Prediction",
        },
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if run_endpoint(**test):
            passed += 1
        print()

    print("=" * 40)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Service is working correctly.")
    else:
        print("❌ Some tests failed. Check the service logs.")

    print("\n📚 Try the interactive API docs:")
    print(f"   {base_url}/docs")


if __name__ == "__main__":
    main()
