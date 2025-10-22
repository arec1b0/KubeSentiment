"""Tests for the refactored `predict()` method in `SentimentAnalyzer`.

This module contains test cases for the helper methods that make up the
refactored `predict()` method. Each test class focuses on a specific part of
the prediction workflow, such as input validation, caching, text preprocessing,
model inference, and metrics recording.
"""

from unittest.mock import Mock, patch

import pytest

from app.core.config import Settings
from app.models.pytorch_sentiment import SentimentAnalyzer
from app.utils.exceptions import ModelInferenceError, ModelNotLoadedError, TextEmptyError


@pytest.fixture
def mock_settings(monkeypatch):
    """Provides a mocked `Settings` object for testing.

    Args:
        monkeypatch: The pytest `monkeypatch` fixture.

    Returns:
        A mocked `Settings` object.
    """
    settings = Settings(
        model_name="distilbert-base-uncased-finetuned-sst-2-english",
        prediction_cache_max_size=100,
        max_text_length=512,
    )
    monkeypatch.setattr("app.models.pytorch_sentiment.get_settings", lambda: settings)
    return settings


@pytest.fixture
def analyzer_with_mock_pipeline(mock_settings, monkeypatch):
    """Creates a `SentimentAnalyzer` instance with a mocked inference pipeline.

    This fixture allows for testing the analyzer's logic without loading the
    actual machine learning model.

    Args:
        mock_settings: The mocked settings fixture.
        monkeypatch: The pytest `monkeypatch` fixture.

    Returns:
        A `SentimentAnalyzer` instance with a mocked pipeline.
    """
    analyzer = SentimentAnalyzer()

    # Mock pipeline
    def mock_pipeline(text):
        return [{"label": "POSITIVE", "score": 0.95}]

    analyzer._pipeline = mock_pipeline
    analyzer._is_loaded = True

    # Mock get_contextual_logger to avoid dependency
    mock_logger = Mock()
    monkeypatch.setattr(
        "app.models.pytorch_sentiment.get_contextual_logger", lambda *args, **kwargs: mock_logger
    )

    return analyzer


@pytest.mark.unit
class TestValidateInputText:
    """A test suite for the `_validate_input_text` method."""

    def test_validate_with_ready_model(self, analyzer_with_mock_pipeline):
        """Tests that validation passes when the model is ready and the text is valid."""
        analyzer = analyzer_with_mock_pipeline
        mock_logger = Mock()

        # Should not raise
        analyzer._validate_input_text("valid text", mock_logger)

    def test_validate_raises_when_model_not_ready(self, mock_settings):
        """Tests that `ModelNotLoadedError` is raised if the model is not ready."""
        analyzer = SentimentAnalyzer()
        analyzer._is_loaded = False
        mock_logger = Mock()

        with pytest.raises(ModelNotLoadedError):
            analyzer._validate_input_text("text", mock_logger)

    def test_validate_raises_on_empty_text(self, analyzer_with_mock_pipeline):
        """Tests that `TextEmptyError` is raised for empty or whitespace-only text."""
        analyzer = analyzer_with_mock_pipeline
        mock_logger = Mock()

        with pytest.raises(TextEmptyError):
            analyzer._validate_input_text("", mock_logger)

        with pytest.raises(TextEmptyError):
            analyzer._validate_input_text("   ", mock_logger)


@pytest.mark.unit
class TestTryGetCachedResult:
    """A test suite for the `_try_get_cached_result` method."""

    def test_returns_none_when_not_cached(self, analyzer_with_mock_pipeline):
        """Tests that `None` is returned if the result is not in the cache."""
        analyzer = analyzer_with_mock_pipeline
        mock_logger = Mock()

        result = analyzer._try_get_cached_result("uncached text", mock_logger)

        assert result is None

    def test_returns_cached_result_with_flag(self, analyzer_with_mock_pipeline):
        """Tests that a cached result is returned with the `cached` flag set to `True`."""
        analyzer = analyzer_with_mock_pipeline
        mock_logger = Mock()

        # Add to cache
        cache_key = analyzer._get_cache_key("cached text")
        analyzer._prediction_cache[cache_key] = {
            "label": "POSITIVE",
            "score": 0.99,
            "cached": False,
        }

        result = analyzer._try_get_cached_result("cached text", mock_logger)

        assert result is not None
        assert result["cached"] is True
        assert result["label"] == "POSITIVE"


@pytest.mark.unit
class TestPreprocessText:
    """A test suite for the `_preprocess_text` method."""

    def test_no_truncation_for_short_text(self, analyzer_with_mock_pipeline):
        """Tests that short text is not truncated."""
        analyzer = analyzer_with_mock_pipeline
        mock_logger = Mock()

        text = "Short text"
        processed, original, truncated = analyzer._preprocess_text(text, mock_logger)

        assert processed == text
        assert original == text
        assert truncated is False

    def test_truncation_for_long_text(self, analyzer_with_mock_pipeline, mock_settings):
        """Tests that long text is correctly truncated to the maximum length."""
        analyzer = analyzer_with_mock_pipeline
        mock_logger = Mock()

        # Create text longer than max_text_length (512)
        long_text = "a" * 600

        processed, original, truncated = analyzer._preprocess_text(long_text, mock_logger)

        assert len(processed) == 512
        assert len(original) == 600
        assert truncated is True
        assert mock_logger.warning.called


@pytest.mark.unit
class TestRunModelInference:
    """A test suite for the `_run_model_inference` method."""

    def test_successful_inference(self, analyzer_with_mock_pipeline):
        """Tests a successful model inference call."""
        analyzer = analyzer_with_mock_pipeline
        mock_logger = Mock()

        result, inference_time = analyzer._run_model_inference(
            "test text", "test text", mock_logger
        )

        assert result["label"] == "POSITIVE"
        assert result["score"] == 0.95
        assert "inference_time_ms" in result
        assert inference_time > 0
        assert result["cached"] is False

    def test_inference_error_raises_exception(self, analyzer_with_mock_pipeline):
        """Tests that a runtime error during inference is wrapped in a `ModelInferenceError`."""
        analyzer = analyzer_with_mock_pipeline
        mock_logger = Mock()

        # Make pipeline raise an error
        def failing_pipeline(text):
            raise RuntimeError("Pipeline error")

        analyzer._pipeline = failing_pipeline

        with pytest.raises(ModelInferenceError) as exc_info:
            analyzer._run_model_inference("text", "text", mock_logger)

        assert "Pipeline error" in str(exc_info.value)


@pytest.mark.unit
class TestRecordPredictionMetrics:
    """A test suite for the `_record_prediction_metrics` method."""

    def test_metrics_recorded_when_available(self, analyzer_with_mock_pipeline, monkeypatch):
        """Tests that metrics are recorded when the monitoring utility is available."""
        analyzer = analyzer_with_mock_pipeline

        mock_metrics = Mock()
        monkeypatch.setattr("app.models.pytorch_sentiment.MONITORING_AVAILABLE", True)
        monkeypatch.setattr("app.models.pytorch_sentiment.get_metrics", lambda: mock_metrics)

        analyzer._record_prediction_metrics(0.95, 100, 45.5)

        # Verify metrics were called
        mock_metrics.record_inference_duration.assert_called_once()
        mock_metrics.record_prediction_metrics.assert_called_once_with(0.95, 100)

    def test_metrics_skipped_when_unavailable(self, analyzer_with_mock_pipeline, monkeypatch):
        """Tests that no error occurs when metrics are recorded but monitoring is unavailable."""
        analyzer = analyzer_with_mock_pipeline

        monkeypatch.setattr("app.models.pytorch_sentiment.MONITORING_AVAILABLE", False)

        # Should not raise
        analyzer._record_prediction_metrics(0.95, 100, 45.5)


@pytest.mark.unit
class TestPredictOrchestration:
    """A test suite for the main `predict()` orchestration method.

    These tests verify that the `predict` method correctly calls the helper
    methods in sequence and handles the overall workflow, including caching
    and text processing.
    """

    def test_predict_full_workflow(self, analyzer_with_mock_pipeline, monkeypatch):
        """Tests the complete prediction workflow through the main `predict` method."""
        analyzer = analyzer_with_mock_pipeline

        # Mock monitoring
        monkeypatch.setattr("app.models.pytorch_sentiment.MONITORING_AVAILABLE", False)

        result = analyzer.predict("This is a test")

        assert result["label"] == "POSITIVE"
        assert result["score"] == 0.95
        assert result["cached"] is False
        assert result["inference_time_ms"] > 0

    def test_predict_uses_cache_on_second_call(self, analyzer_with_mock_pipeline, monkeypatch):
        """Tests that a second call with the same text uses the cache."""
        analyzer = analyzer_with_mock_pipeline
        monkeypatch.setattr("app.models.pytorch_sentiment.MONITORING_AVAILABLE", False)

        # First call
        result1 = analyzer.predict("Same text")
        assert result1["cached"] is False

        # Second call should use cache
        result2 = analyzer.predict("Same text")
        assert result2["cached"] is True
        assert result2["label"] == result1["label"]

    def test_predict_handles_whitespace_stripping(self, analyzer_with_mock_pipeline, monkeypatch):
        """Tests that input text with leading/trailing whitespace is handled correctly by the cache."""
        analyzer = analyzer_with_mock_pipeline
        monkeypatch.setattr("app.models.pytorch_sentiment.MONITORING_AVAILABLE", False)

        result1 = analyzer.predict("  text  ")
        result2 = analyzer.predict("text")

        # Both should use same cache entry
        assert result2["cached"] is True
