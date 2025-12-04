"""Tests for the LRU cache implementation in the sentiment analyzers.

This module contains test cases to verify the correct behavior of the
Least Recently Used (LRU) cache, including item eviction, cache hits and
misses, and statistics reporting.
"""

import pytest

from app.core.config import Settings
from app.models.pytorch_sentiment import SentimentAnalyzer

# Make ONNX import optional
try:
    from app.models.onnx_sentiment import ONNXSentimentAnalyzer

    ONNX_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    ONNXSentimentAnalyzer = None  # type: ignore
    ONNX_AVAILABLE = False


@pytest.fixture
def mock_settings(monkeypatch):
    """Provides a mocked `Settings` object with a small cache size for testing.

    Args:
        monkeypatch: The pytest `monkeypatch` fixture.

    Returns:
        A mocked `Settings` object.
    """
    settings = Settings(
        model_name="distilbert-base-uncased-finetuned-sst-2-english",
        prediction_cache_max_size=3,  # Small cache for testing
        prediction_cache_enabled=True,  # Cache enabled by default
        max_text_length=512,
    )
    monkeypatch.setattr("app.models.pytorch_sentiment.get_settings", lambda: settings)
    monkeypatch.setattr("app.models.onnx_sentiment.get_settings", lambda: settings, raising=False)
    return settings


@pytest.fixture
def mock_settings_cache_disabled(monkeypatch):
    """Provides a mocked `Settings` object with cache disabled for testing.

    Args:
        monkeypatch: The pytest `monkeypatch` fixture.

    Returns:
        A mocked `Settings` object with cache disabled.
    """
    settings = Settings(
        model_name="distilbert-base-uncased-finetuned-sst-2-english",
        prediction_cache_max_size=1000,
        prediction_cache_enabled=False,  # Cache disabled
        max_text_length=512,
    )
    monkeypatch.setattr("app.models.pytorch_sentiment.get_settings", lambda: settings)
    monkeypatch.setattr("app.models.onnx_sentiment.get_settings", lambda: settings, raising=False)
    return settings


@pytest.mark.unit
@pytest.mark.cache
class TestLRUCache:
    """A test suite for the LRU cache behavior in the sentiment analyzer."""

    def test_cache_key_generation_blake2b(self, mock_settings):
        """Tests that the cache keys are generated correctly and consistently."""
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
        """Tests that the LRU cache correctly evicts the least recently used item."""
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
        """Tests that accessing a cached item moves it to the end of the order (most recent)."""
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
        """Tests the functionality of clearing the cache."""
        analyzer = SentimentAnalyzer()

        # Add some items to cache
        analyzer._prediction_cache["key1"] = {"label": "POSITIVE"}
        analyzer._prediction_cache["key2"] = {"label": "NEGATIVE"}

        assert len(analyzer._prediction_cache) == 2

        # Clear cache
        analyzer.clear_cache()

        assert len(analyzer._prediction_cache) == 0

    def test_cache_hit_returns_copy(self, mock_settings, monkeypatch):
        """Tests that a cache hit returns a copy of the stored result and sets the `cached` flag."""
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
        """Performs an informational performance comparison of hashing algorithms.

        This test is not a strict assertion but is used to demonstrate
        the performance benefit of using BLAKE2b over SHA256 for generating
        cache keys.
        """
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
    """A test suite for the cache statistics functionality."""

    def test_get_cache_stats(self, mock_settings, monkeypatch):
        """Tests the retrieval of cache statistics.

        This test verifies that the `get_cache_stats` method returns the
        correct cache size and other relevant metrics.
        """
        analyzer = SentimentAnalyzer()

        # Add some items
        analyzer._prediction_cache["key1"] = {"label": "POSITIVE"}
        analyzer._prediction_cache["key2"] = {"label": "NEGATIVE"}

        stats = analyzer.get_cache_stats()

        assert stats["cache_size"] == 2
        assert stats["cache_max_size"] == 3
        assert "cache_hit_ratio" in stats


@pytest.mark.unit
@pytest.mark.cache
class TestCacheDisabled:
    """Test suite for disabled cache functionality."""

    def test_predictions_work_without_cache(self, mock_settings_cache_disabled, monkeypatch):
        """Test that predictions work correctly when cache is disabled."""
        analyzer = SentimentAnalyzer()

        # Mock the pipeline to avoid loading actual model
        def mock_predict(text):
            return [{"label": "POSITIVE", "score": 0.99}]

        monkeypatch.setattr(analyzer, "_pipeline", lambda text: mock_predict(text))
        monkeypatch.setattr(analyzer, "_is_loaded", True)

        # Make predictions - should work without cache
        result1 = analyzer.predict("test text 1")
        result2 = analyzer.predict("test text 2")

        assert result1["label"] == "POSITIVE"
        assert result2["label"] == "POSITIVE"
        assert "score" in result1
        assert "score" in result2

    def test_cache_info_returns_mock_when_disabled(self, mock_settings_cache_disabled, monkeypatch):
        """Test that _get_cache_info returns mock cache info when cache is disabled."""
        analyzer = SentimentAnalyzer()

        monkeypatch.setattr(
            analyzer, "_pipeline", lambda text: [{"label": "POSITIVE", "score": 0.99}]
        )
        monkeypatch.setattr(analyzer, "_is_loaded", True)

        cache_info = analyzer._get_cache_info()

        assert cache_info.hits == 0
        assert cache_info.misses == 0
        assert cache_info.maxsize == 0
        assert cache_info.currsize == 0

    def test_get_model_info_shows_cache_disabled(self, mock_settings_cache_disabled, monkeypatch):
        """Test that get_model_info shows cache as disabled."""
        analyzer = SentimentAnalyzer()

        monkeypatch.setattr(
            analyzer, "_pipeline", lambda text: [{"label": "POSITIVE", "score": 0.99}]
        )
        monkeypatch.setattr(analyzer, "_is_loaded", True)

        model_info = analyzer.get_model_info()

        assert model_info["cache_enabled"] is False
        assert model_info["cache_size"] == 0
        assert model_info["cache_maxsize"] == 0

    def test_get_performance_metrics_shows_cache_disabled(
        self, mock_settings_cache_disabled, monkeypatch
    ):
        """Test that performance metrics show cache as disabled."""
        analyzer = SentimentAnalyzer()

        monkeypatch.setattr(
            analyzer, "_pipeline", lambda text: [{"label": "POSITIVE", "score": 0.99}]
        )
        monkeypatch.setattr(analyzer, "_is_loaded", True)

        # Make a prediction
        analyzer.predict("test text")

        metrics = analyzer.get_performance_metrics()

        assert metrics["cache_enabled"] is False
        assert metrics["cache_hits"] == 0
        assert metrics["cache_misses"] >= 0  # Should track misses even when disabled
        assert metrics["cache_hit_rate"] == 0.0
        assert metrics["cache_info"] is not None
        assert metrics["cache_info"]["hits"] == 0

    def test_clear_cache_noop_when_disabled(self, mock_settings_cache_disabled, monkeypatch):
        """Test that clear_cache is a no-op when cache is disabled."""
        analyzer = SentimentAnalyzer()

        monkeypatch.setattr(
            analyzer, "_pipeline", lambda text: [{"label": "POSITIVE", "score": 0.99}]
        )
        monkeypatch.setattr(analyzer, "_is_loaded", True)

        # Should not raise an error
        analyzer.clear_cache()

        # Verify predictions still work
        result = analyzer.predict("test text")
        assert result["label"] == "POSITIVE"

    @pytest.mark.skipif(not ONNX_AVAILABLE, reason="ONNX not available")
    def test_onnx_predictions_work_without_cache(
        self, mock_settings_cache_disabled, monkeypatch, tmp_path
    ):
        """Test that ONNX predictions work correctly when cache is disabled."""
        import onnxruntime as ort
        from transformers import AutoTokenizer

        # Create a minimal mock ONNX model path
        model_path = tmp_path / "model"
        model_path.mkdir()
        (model_path / "model.onnx").write_text("dummy")

        analyzer = ONNXSentimentAnalyzer(str(model_path))

        # Mock the session and tokenizer
        mock_session = type(
            "MockSession",
            (),
            {
                "run": lambda self, output_names, inputs: [[[0.1, 0.9]]],
                "get_providers": lambda self: ["CPUExecutionProvider"],
            },
        )()
        mock_tokenizer = type(
            "MockTokenizer",
            (),
            {
                "__call__": lambda self, text, **kwargs: {
                    "input_ids": [[1, 2, 3]],
                    "attention_mask": [[1, 1, 1]],
                }
            },
        )()

        monkeypatch.setattr(analyzer, "_session", mock_session)
        monkeypatch.setattr(analyzer, "_tokenizer", mock_tokenizer)
        monkeypatch.setattr(analyzer, "_is_loaded", True)

        # Make predictions - should work without cache
        result = analyzer.predict("test text")

        assert "label" in result
        assert "score" in result

    @pytest.mark.skipif(not ONNX_AVAILABLE, reason="ONNX not available")
    def test_onnx_get_model_info_shows_cache_disabled(
        self, mock_settings_cache_disabled, monkeypatch, tmp_path
    ):
        """Test that ONNX get_model_info shows cache as disabled."""
        import onnxruntime as ort

        model_path = tmp_path / "model"
        model_path.mkdir()
        (model_path / "model.onnx").write_text("dummy")

        analyzer = ONNXSentimentAnalyzer(str(model_path))

        mock_session = type(
            "MockSession", (), {"get_providers": lambda self: ["CPUExecutionProvider"]}
        )()
        monkeypatch.setattr(analyzer, "_session", mock_session)
        monkeypatch.setattr(analyzer, "_is_loaded", True)

        model_info = analyzer.get_model_info()

        assert model_info["cache_enabled"] is False
        assert model_info["cache_size"] == 0
        assert model_info["cache_maxsize"] == 0
