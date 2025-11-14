#!/usr/bin/env python3
"""
Test script for configuration profiles.

This script validates that all profiles load correctly and have the expected defaults.
"""

import os
import sys
from typing import Dict, Any


def clear_mlops_env_vars():
    """Clear all MLOPS_ environment variables."""
    for key in list(os.environ.keys()):
        if key.startswith('MLOPS_'):
            del os.environ[key]


def test_profile_loading():
    """Test loading each profile."""
    print("=" * 60)
    print("Testing Profile Loading")
    print("=" * 60)

    from app.core.config.profiles import load_profile, get_profile_info

    # Test getting available profiles
    print("\n1. Available Profiles:")
    profiles = get_profile_info()
    for name, info in profiles.items():
        print(f"   - {name}: {info['description']}")

    # Test loading each profile
    print("\n2. Loading Profile Defaults:")
    for profile_name in ['local', 'development', 'staging', 'production']:
        print(f"\n   Profile: {profile_name}")
        try:
            overrides = load_profile(profile_name)
            print(f"   ✓ Loaded {len(overrides)} settings")
            print(f"     - DEBUG: {overrides.get('MLOPS_DEBUG')}")
            print(f"     - LOG_LEVEL: {overrides.get('MLOPS_LOG_LEVEL')}")
            print(f"     - WORKERS: {overrides.get('MLOPS_WORKERS')}")
            print(f"     - REDIS_ENABLED: {overrides.get('MLOPS_REDIS_ENABLED')}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            return False

    print("\n✓ All profiles loaded successfully")
    return True


def test_settings_with_profiles():
    """Test Settings class with different profiles."""
    print("\n" + "=" * 60)
    print("Testing Settings with Profiles")
    print("=" * 60)

    from app.core.config import Settings

    profiles_to_test = [
        ('local', {
            'debug': True,
            'log_level': 'INFO',
            'workers': 1,
            'redis_enabled': False,
            'kafka_enabled': False,
        }),
        ('development', {
            'debug': True,
            'log_level': 'DEBUG',
            'workers': 1,
            'redis_enabled': False,
            'kafka_enabled': False,
        }),
        ('staging', {
            'debug': False,
            'log_level': 'INFO',
            'workers': 2,
            'redis_enabled': True,
            'vault_enabled': True,
        }),
        ('production', {
            'debug': False,
            'log_level': 'WARNING',
            'workers': 4,
            'redis_enabled': True,
            'kafka_enabled': True,
            'vault_enabled': True,
        }),
    ]

    for profile_name, expected in profiles_to_test:
        print(f"\n   Profile: {profile_name}")
        clear_mlops_env_vars()

        try:
            settings = Settings.load_from_profile(profile_name)

            # Verify expected settings
            for key, expected_value in expected.items():
                actual_value = getattr(settings, key)
                if actual_value == expected_value:
                    print(f"     ✓ {key}: {actual_value}")
                else:
                    print(f"     ✗ {key}: expected {expected_value}, got {actual_value}")
                    return False

        except Exception as e:
            print(f"   ✗ Failed to load settings: {e}")
            import traceback
            traceback.print_exc()
            return False

    print("\n✓ All settings loaded correctly with profiles")
    return True


def test_profile_overrides():
    """Test that environment variables override profile defaults."""
    print("\n" + "=" * 60)
    print("Testing Profile Overrides")
    print("=" * 60)

    from app.core.config import Settings

    # Test override with production profile
    clear_mlops_env_vars()
    os.environ['MLOPS_PROFILE'] = 'production'
    os.environ['MLOPS_DEBUG'] = 'true'  # Override production default (false)
    os.environ['MLOPS_WORKERS'] = '8'   # Override production default (4)

    try:
        settings = Settings.load_from_profile()

        print(f"\n   Profile: production (with overrides)")
        print(f"     MLOPS_DEBUG env var: true")
        print(f"     MLOPS_WORKERS env var: 8")

        # Verify overrides work
        if settings.debug == True:
            print(f"     ✓ debug overridden: {settings.debug}")
        else:
            print(f"     ✗ debug not overridden: {settings.debug}")
            return False

        if settings.workers == 8:
            print(f"     ✓ workers overridden: {settings.workers}")
        else:
            print(f"     ✗ workers not overridden: {settings.workers}")
            return False

        # Verify non-overridden values still come from profile
        if settings.redis_enabled == True:  # Production default
            print(f"     ✓ redis_enabled from profile: {settings.redis_enabled}")
        else:
            print(f"     ✗ redis_enabled not from profile: {settings.redis_enabled}")
            return False

    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✓ Profile overrides work correctly")
    return True


def test_backward_compatibility():
    """Test that the system works without MLOPS_PROFILE set."""
    print("\n" + "=" * 60)
    print("Testing Backward Compatibility")
    print("=" * 60)

    from app.core.config import Settings

    # Test without MLOPS_PROFILE
    clear_mlops_env_vars()
    # Don't set MLOPS_PROFILE

    try:
        settings = Settings()
        print(f"\n   No MLOPS_PROFILE set")
        print(f"     ✓ Settings loaded successfully")
        print(f"     - Environment: {settings.environment}")
        print(f"     - Debug: {settings.debug}")
        print(f"     - Log Level: {settings.log_level}")

    except Exception as e:
        print(f"   ✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n✓ Backward compatibility maintained")
    return True


def test_get_active_profile():
    """Test getting the active profile."""
    print("\n" + "=" * 60)
    print("Testing Get Active Profile")
    print("=" * 60)

    from app.core.config import Settings

    test_cases = [
        ('development', 'development'),
        ('staging', 'staging'),
        ('production', 'production'),
        ('local', 'local'),
    ]

    for profile, expected_active in test_cases:
        clear_mlops_env_vars()
        settings = Settings.load_from_profile(profile)
        active = settings.get_active_profile()

        print(f"\n   Profile: {profile}")
        if active == expected_active:
            print(f"     ✓ Active profile: {active}")
        else:
            print(f"     ✗ Expected {expected_active}, got {active}")
            return False

    print("\n✓ Get active profile works correctly")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("Configuration Profiles Test Suite")
    print("=" * 60)

    tests = [
        ("Profile Loading", test_profile_loading),
        ("Settings with Profiles", test_settings_with_profiles),
        ("Profile Overrides", test_profile_overrides),
        ("Backward Compatibility", test_backward_compatibility),
        ("Get Active Profile", test_get_active_profile),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! Configuration profiles are working correctly.")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
