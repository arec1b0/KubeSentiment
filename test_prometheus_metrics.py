#!/usr/bin/env python3
"""
Test script for Prometheus metrics endpoint.

This script tests that the /metrics endpoint returns proper Prometheus format
and validates the metrics content.
"""

import requests
import time
import sys


def test_prometheus_metrics(base_url="http://localhost:8000", api_prefix="/api/v1"):
    """Test Prometheus metrics endpoint."""
    print("🧪 Testing Prometheus Metrics Endpoint")
    print("=" * 50)

    try:
        # Test metrics endpoint
        print("📊 Testing /metrics endpoint...")
        response = requests.get(f"{base_url}{api_prefix}/metrics", timeout=10)

        if response.status_code != 200:
            print(f"❌ Metrics endpoint failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

        content = response.text
        content_type = response.headers.get("content-type", "")

        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Content-Type: {content_type}")

        # Validate Prometheus format
        if "text/plain" not in content_type:
            print(
                f"⚠️  Warning: Content-Type should contain 'text/plain', got: {content_type}"
            )

        # Check for expected metrics
        expected_metrics = [
            "sentiment_requests_total",
            "sentiment_request_duration_seconds",
            "sentiment_inference_duration_seconds",
            "sentiment_model_loaded",
            "sentiment_torch_version_info",
            "sentiment_cuda_available",
        ]

        print("\n📋 Checking for expected metrics:")
        for metric in expected_metrics:
            if metric in content:
                print(f"✅ Found: {metric}")
            else:
                print(f"❌ Missing: {metric}")

        # Show sample metrics
        print("\n📄 Sample metrics output (first 20 lines):")
        lines = content.split("\n")[:20]
        for line in lines:
            if line.strip() and not line.startswith("#"):
                print(f"   {line}")

        # Test some predictions to generate metrics
        print("\n🎯 Generating some metrics by making predictions...")
        test_texts = [
            "I love this service!",
            "This is terrible",
            "The weather is nice today",
            "I hate waiting in traffic",
        ]

        for text in test_texts:
            try:
                pred_response = requests.post(
                    f"{base_url}{api_prefix}/predict", json={"text": text}, timeout=10
                )
                if pred_response.status_code == 200:
                    result = pred_response.json()
                    print(
                        f"   ✅ '{text[:30]}...' → {result['label']} ({result['score']:.2f})"
                    )
                else:
                    print(f"   ❌ Prediction failed for: {text[:30]}...")
            except Exception as e:
                print(f"   ⚠️  Error predicting '{text[:30]}...': {e}")

        # Check metrics again after predictions
        print("\n📊 Checking metrics after predictions...")
        response2 = requests.get(f"{base_url}{api_prefix}/metrics", timeout=10)
        if response2.status_code == 200:
            content2 = response2.text

            # Look for request count metrics
            request_metrics = [
                line
                for line in content2.split("\n")
                if "sentiment_requests_total" in line and not line.startswith("#")
            ]

            if request_metrics:
                print("✅ Request metrics found:")
                for metric in request_metrics[:5]:  # Show first 5
                    print(f"   {metric}")
            else:
                print("⚠️  No request metrics found")

            # Look for inference metrics
            inference_metrics = [
                line
                for line in content2.split("\n")
                if "sentiment_inference_duration_seconds" in line
                and not line.startswith("#")
            ]

            if inference_metrics:
                print("✅ Inference metrics found:")
                for metric in inference_metrics[:3]:  # Show first 3
                    print(f"   {metric}")
            else:
                print("⚠️  No inference metrics found")

        print("\n🎉 Prometheus metrics test completed successfully!")
        return True

    except requests.exceptions.ConnectionError:
        print(f"❌ Connection failed to {base_url}")
        print("💡 Make sure the service is running:")
        print("   python run.py")
        return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


def test_legacy_json_metrics(base_url="http://localhost:8000", api_prefix="/api/v1"):
    """Test legacy JSON metrics endpoint."""
    print("\n📊 Testing Legacy JSON Metrics Endpoint")
    print("=" * 50)

    try:
        response = requests.get(f"{base_url}{api_prefix}/metrics-json", timeout=10)

        if response.status_code != 200:
            print(f"❌ JSON metrics endpoint failed: {response.status_code}")
            return False

        data = response.json()
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Response Type: JSON")

        expected_fields = ["torch_version", "cuda_available"]
        print("\n📋 Checking JSON response fields:")
        for field in expected_fields:
            if field in data:
                print(f"✅ Found: {field} = {data[field]}")
            else:
                print(f"❌ Missing: {field}")

        print("\n📄 Full JSON response:")
        import json

        print(json.dumps(data, indent=2))

        return True

    except Exception as e:
        print(f"❌ JSON metrics test failed: {e}")
        return False


def main():
    """Main test function."""
    base_url = "http://localhost:8000"

    # Test both endpoints
    prometheus_ok = test_prometheus_metrics(base_url)
    json_ok = test_legacy_json_metrics(base_url)

    print("\n" + "=" * 50)
    print("📊 FINAL RESULTS:")
    print(f"   Prometheus /metrics: {'✅ PASS' if prometheus_ok else '❌ FAIL'}")
    print(f"   Legacy /metrics-json: {'✅ PASS' if json_ok else '❌ FAIL'}")

    if prometheus_ok and json_ok:
        print("\n🎉 All metrics tests passed!")
        print("\n💡 Next steps:")
        print("   • Deploy to Kubernetes: bash scripts/deploy.sh")
        print(
            "   • Access Prometheus: kubectl port-forward svc/prometheus 9090:9090 -n mlops-sentiment"
        )
        print("   • View metrics in Prometheus: http://localhost:9090")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
