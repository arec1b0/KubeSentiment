"""
Tests for LRU cache implementation in sentiment analyzers.

Tests verify proper LRU eviction behavior and cache hit/miss patterns.
"""

import pytest
from app.ml.sentiment import SentimentAnalyzer
from app.ml.onnx_optimizer import ONNXSentimentAnalyzer
from app.config import Settings


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings with small cache size for testing."""
    settings = Settings(
        model_name="distilbert-base-uncased-finetuned-sst-2-english",
        prediction_cache_max_size=3,  # Small cache for testing
        max_text_length=512,
    )
    monkeypatch.setattr("app.ml.sentiment.get_settings", lambda: settings)
    return settings


@pytest.mark.unit
@pytest.mark.cache
class TestLRUCache:
    """Test LRU cache behavior in sentiment analyzer."""

    def test_cache_key_generation_blake2b(self, mock_settings):
        """Test that cache keys are generated using BLAKE2b."""
        analyzer = SentimentAnalyzer()

        key1 = analyzer._get_cache_key("test text")
        key2 = analyzer._get_cache_key("test text")
        key3 = analyzer._get_cache_key("different text")

        # Same text should produce same key
        assert key1 == key2
        # Different text should produce different key
        assert key1 != key3
        # Key should be 32 chars (16 bytes in hex)
        assert len(key1) == 32

    def test_lru_eviction_order(self, mock_settings, monkeypatch):
        """Test that LRU cache evicts least recently used items."""
        analyzer = SentimentAnalyzer()

        # Mock the pipeline to avoid loading actual model
        def mock_predict(text):
            return [{"label": "POSITIVE", "score": 0.99}]

        monkeypatch.setattr(analyzer, "_pipeline", lambda text: mock_predict(text))
        monkeypatch.setattr(analyzer, "_is_loaded", True)

        # Fill cache to max size (3 items)
        analyzer.predict("text 1")
        analyzer.predict("text 2")
        analyzer.predict("text 3")

        assert len(analyzer._prediction_cache) == 3

        # Access text 1 to make it most recently used
        analyzer.predict("text 1")

        # Add new item, should evict text 2 (least recently used)
        analyzer.predict("text 4")

        assert len(analyzer._prediction_cache) == 3

        # Check that text 1, 3, and 4 are in cache
        key1 = analyzer._get_cache_key("text 1")
        key3 = analyzer._get_cache_key("text 3")
        key4 = analyzer._get_cache_key("text 4")

        assert key1 in analyzer._prediction_cache
        assert key3 in analyzer._prediction_cache
        assert key4 in analyzer._prediction_cache

        # Text 2 should be evicted
        key2 = analyzer._get_cache_key("text 2")
        assert key2 not in analyzer._prediction_cache

    def test_cache_move_to_end_on_access(self, mock_settings, monkeypatch):
        """Test that accessing cached items moves them to end (most recent)."""
        from collections import OrderedDict

        analyzer = SentimentAnalyzer()

        # Manually populate cache
        cache_data = {
            "key1": {"label": "POSITIVE", "score": 0.9},
            "key2": {"label": "NEGATIVE", "score": 0.8},
            "key3": {"label": "POSITIVE", "score": 0.7},
        }

        analyzer._prediction_cache = OrderedDict(cache_data)

        # Access key1
        result = analyzer._get_cached_prediction("key1")

        # key1 should now be at the end (most recent)
        keys_list = list(analyzer._prediction_cache.keys())
        assert keys_list[-1] == "key1"
        assert result is not None

    def test_cache_clear(self, mock_settings, monkeypatch):
        """Test cache clearing functionality."""
        analyzer = SentimentAnalyzer()

        # Add some items to cache
        analyzer._prediction_cache["key1"] = {"label": "POSITIVE"}
        analyzer._prediction_cache["key2"] = {"label": "NEGATIVE"}

        assert len(analyzer._prediction_cache) == 2

        # Clear cache
        analyzer.clear_cache()

        assert len(analyzer._prediction_cache) == 0

    def test_cache_hit_returns_copy(self, mock_settings, monkeypatch):
        """Test that cache hits return a copy with cached=True."""
        analyzer = SentimentAnalyzer()

        original_result = {
            "label": "POSITIVE",
            "score": 0.99,
            "inference_time_ms": 10.5,
            "model_name": "test-model",
            "text_length": 10,
            "cached": False,
        }

        cache_key = "test_key"
        analyzer._prediction_cache[cache_key] = original_result

        # Get cached result
        cached_result = analyzer._get_cached_prediction(cache_key)

        assert cached_result is not None
        assert cached_result["cached"] is True
        # Original should be unchanged
        assert original_result["cached"] is False

    def test_performance_blake2b_vs_sha256(self, mock_settings):
        """Test that BLAKE2b is faster than SHA256 (informational)."""
        import hashlib
        import time

        text = "This is a test text for hashing performance" * 10
        iterations = 1000

        # Test BLAKE2b
        start = time.perf_counter()
        for _ in range(iterations):
            hashlib.blake2b(text.encode("utf-8"), digest_size=16).hexdigest()
        blake2b_time = time.perf_counter() - start

        # Test SHA256
        start = time.perf_counter()
        for _ in range(iterations):
            hashlib.sha256(text.encode("utf-8")).hexdigest()
        sha256_time = time.perf_counter() - start

        # BLAKE2b should be faster (informational, not strict assertion)
        print(f"\nBLAKE2b: {blake2b_time:.4f}s, SHA256: {sha256_time:.4f}s")
        print(f"Speedup: {sha256_time / blake2b_time:.2f}x")

        # This is informational - actual speedup varies by system
        assert blake2b_time > 0 and sha256_time > 0


@pytest.mark.unit
@pytest.mark.cache
class TestCacheStats:
    """Test cache statistics functionality."""

    def test_get_cache_stats(self, mock_settings, monkeypatch):
        """Test cache statistics retrieval."""
        analyzer = SentimentAnalyzer()

        # Add some items
        analyzer._prediction_cache["key1"] = {"label": "POSITIVE"}
        analyzer._prediction_cache["key2"] = {"label": "NEGATIVE"}

        stats = analyzer.get_cache_stats()

        assert stats["cache_size"] == 2
        assert stats["cache_max_size"] == 3
        assert "cache_hit_ratio" in stats
