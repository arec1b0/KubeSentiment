"""
Tests for refactored predict() method in sentiment analyzer.

Tests verify that the broken-down helper methods work correctly.
"""

from unittest.mock import Mock, patch

import pytest

from app.core.config import Settings
from app.models.pytorch_sentiment import SentimentAnalyzer
from app.utils.exceptions import (
    ModelInferenceError,
    ModelNotLoadedError,
    TextEmptyError,
)


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    settings = Settings(
        model_name="distilbert-base-uncased-finetuned-sst-2-english",
        prediction_cache_max_size=100,
        max_text_length=512,
    )
    monkeypatch.setattr("app.ml.sentiment.get_settings", lambda: settings)
    return settings


@pytest.fixture
def analyzer_with_mock_pipeline(mock_settings, monkeypatch):
    """Create analyzer with mocked pipeline."""
    analyzer = SentimentAnalyzer()

    # Mock pipeline
    def mock_pipeline(text):
        return [{"label": "POSITIVE", "score": 0.95}]

    analyzer._pipeline = mock_pipeline
    analyzer._is_loaded = True

    # Mock get_contextual_logger to avoid dependency
    mock_logger = Mock()
    monkeypatch.setattr(
        "app.ml.sentiment.get_contextual_logger", lambda *args, **kwargs: mock_logger
    )

    return analyzer


@pytest.mark.unit
class TestValidateInputText:
    """Test _validate_input_text method."""

    def test_validate_with_ready_model(self, analyzer_with_mock_pipeline):
        """Test validation passes when model is ready and text is valid."""
        analyzer = analyzer_with_mock_pipeline
        mock_logger = Mock()

        # Should not raise
        analyzer._validate_input_text("valid text", mock_logger)

    def test_validate_raises_when_model_not_ready(self, mock_settings):
        """Test validation raises ModelNotLoadedError when model not ready."""
        analyzer = SentimentAnalyzer()
        analyzer._is_loaded = False
        mock_logger = Mock()

        with pytest.raises(ModelNotLoadedError):
            analyzer._validate_input_text("text", mock_logger)

    def test_validate_raises_on_empty_text(self, analyzer_with_mock_pipeline):
        """Test validation raises TextEmptyError on empty text."""
        analyzer = analyzer_with_mock_pipeline
        mock_logger = Mock()

        with pytest.raises(TextEmptyError):
            analyzer._validate_input_text("", mock_logger)

        with pytest.raises(TextEmptyError):
            analyzer._validate_input_text("   ", mock_logger)


@pytest.mark.unit
class TestTryGetCachedResult:
    """Test _try_get_cached_result method."""

    def test_returns_none_when_not_cached(self, analyzer_with_mock_pipeline):
        """Test returns None when result not in cache."""
        analyzer = analyzer_with_mock_pipeline
        mock_logger = Mock()

        result = analyzer._try_get_cached_result("uncached text", mock_logger)

        assert result is None

    def test_returns_cached_result_with_flag(self, analyzer_with_mock_pipeline):
        """Test returns cached result with cached=True flag."""
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
    """Test _preprocess_text method."""

    def test_no_truncation_for_short_text(self, analyzer_with_mock_pipeline):
        """Test no truncation when text is within limit."""
        analyzer = analyzer_with_mock_pipeline
        mock_logger = Mock()

        text = "Short text"
        processed, original, truncated = analyzer._preprocess_text(text, mock_logger)

        assert processed == text
        assert original == text
        assert truncated is False

    def test_truncation_for_long_text(self, analyzer_with_mock_pipeline, mock_settings):
        """Test truncation when text exceeds max length."""
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
    """Test _run_model_inference method."""

    def test_successful_inference(self, analyzer_with_mock_pipeline):
        """Test successful model inference."""
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
        """Test that inference errors are properly wrapped."""
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
    """Test _record_prediction_metrics method."""

    def test_metrics_recorded_when_available(self, analyzer_with_mock_pipeline, monkeypatch):
        """Test metrics are recorded when monitoring is available."""
        analyzer = analyzer_with_mock_pipeline

        mock_metrics = Mock()
        monkeypatch.setattr("app.ml.sentiment.MONITORING_AVAILABLE", True)
        monkeypatch.setattr("app.ml.sentiment.get_metrics", lambda: mock_metrics)

        analyzer._record_prediction_metrics(0.95, 100, 45.5)

        # Verify metrics were called
        mock_metrics.record_inference_duration.assert_called_once()
        mock_metrics.record_prediction_metrics.assert_called_once_with(0.95, 100)

    def test_metrics_skipped_when_unavailable(self, analyzer_with_mock_pipeline, monkeypatch):
        """Test no error when monitoring unavailable."""
        analyzer = analyzer_with_mock_pipeline

        monkeypatch.setattr("app.ml.sentiment.MONITORING_AVAILABLE", False)

        # Should not raise
        analyzer._record_prediction_metrics(0.95, 100, 45.5)


@pytest.mark.unit
class TestPredictOrchestration:
    """Test the main predict() orchestration method."""

    def test_predict_full_workflow(self, analyzer_with_mock_pipeline, monkeypatch):
        """Test complete prediction workflow through orchestrator."""
        analyzer = analyzer_with_mock_pipeline

        # Mock monitoring
        monkeypatch.setattr("app.ml.sentiment.MONITORING_AVAILABLE", False)

        result = analyzer.predict("This is a test")

        assert result["label"] == "POSITIVE"
        assert result["score"] == 0.95
        assert result["cached"] is False
        assert result["inference_time_ms"] > 0

    def test_predict_uses_cache_on_second_call(self, analyzer_with_mock_pipeline, monkeypatch):
        """Test that second prediction uses cache."""
        analyzer = analyzer_with_mock_pipeline
        monkeypatch.setattr("app.ml.sentiment.MONITORING_AVAILABLE", False)

        # First call
        result1 = analyzer.predict("Same text")
        assert result1["cached"] is False

        # Second call should use cache
        result2 = analyzer.predict("Same text")
        assert result2["cached"] is True
        assert result2["label"] == result1["label"]

    def test_predict_handles_whitespace_stripping(self, analyzer_with_mock_pipeline, monkeypatch):
        """Test that whitespace is properly stripped."""
        analyzer = analyzer_with_mock_pipeline
        monkeypatch.setattr("app.ml.sentiment.MONITORING_AVAILABLE", False)

        result1 = analyzer.predict("  text  ")
        result2 = analyzer.predict("text")

        # Both should use same cache entry
        assert result2["cached"] is True
