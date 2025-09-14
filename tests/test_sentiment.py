"""Tests for the sentiment analysis model."""

import pytest
from unittest.mock import patch, MagicMock

from app.ml.sentiment import SentimentAnalyzer, get_sentiment_analyzer


class TestSentimentAnalyzer:
    """Test suite for the SentimentAnalyzer class."""

    def test_init_success(self):
        """Test successful initialization of SentimentAnalyzer."""
        with patch("app.ml.sentiment.pipeline") as mock_pipeline:
            mock_pipeline.return_value = MagicMock()
            analyzer = SentimentAnalyzer()
            assert analyzer.settings.model_name == "distilbert-base-uncased-finetuned-sst-2-english"
            assert analyzer._pipeline is not None
            assert analyzer._is_loaded is True

    def test_init_failure(self):
        """Test failed initialization of SentimentAnalyzer."""
        with patch("app.ml.sentiment.pipeline", side_effect=Exception("Model not found")):
            analyzer = SentimentAnalyzer()
            assert analyzer.settings.model_name == "distilbert-base-uncased-finetuned-sst-2-english"
            assert analyzer._pipeline is None
            assert analyzer._is_loaded is False

    def test_is_ready_true(self):
        """Test is_ready returns True when model is loaded."""
        with patch("app.ml.sentiment.pipeline") as mock_pipeline:
            mock_pipeline.return_value = MagicMock()
            analyzer = SentimentAnalyzer()
            assert analyzer.is_ready() is True

    def test_is_ready_false(self):
        """Test is_ready returns False when model failed to load."""
        with patch("app.ml.sentiment.pipeline", side_effect=Exception("Model error")):
            analyzer = SentimentAnalyzer()
            assert analyzer.is_ready() is False

    def test_predict_success(self):
        """Test successful prediction."""
        with patch("app.ml.sentiment.pipeline") as mock_pipeline:
            mock_model = MagicMock()
            mock_model.return_value = [{"label": "POSITIVE", "score": 0.9876}]
            mock_pipeline.return_value = mock_model
            
            analyzer = SentimentAnalyzer()
            result = analyzer.predict("I love this!")
            
            assert result["label"] == "POSITIVE"
            assert result["score"] == 0.9876
            assert "inference_time_ms" in result
            assert "model_name" in result
            assert "text_length" in result
            mock_model.assert_called_once_with("I love this!")

    def test_predict_model_not_ready(self):
        """Test prediction when model is not ready."""
        with patch("app.ml.sentiment.pipeline", side_effect=Exception("Model error")):
            analyzer = SentimentAnalyzer()
            
            with pytest.raises(RuntimeError):
                analyzer.predict("Test text")

    def test_predict_model_exception(self):
        """Test prediction when model raises an exception."""
        with patch("app.ml.sentiment.pipeline") as mock_pipeline:
            mock_model = MagicMock()
            mock_model.side_effect = Exception("Prediction error")
            mock_pipeline.return_value = mock_model
            
            analyzer = SentimentAnalyzer()
            
            with pytest.raises(RuntimeError):
                analyzer.predict("Test text")

    def test_predict_empty_text(self):
        """Test prediction with empty text."""
        with patch("app.ml.sentiment.pipeline") as mock_pipeline:
            mock_model = MagicMock()
            mock_model.return_value = [{"label": "POSITIVE", "score": 0.5}]
            mock_pipeline.return_value = mock_model
            
            analyzer = SentimentAnalyzer()
            
            with pytest.raises(ValueError):
                analyzer.predict("")

    def test_predict_long_text(self):
        """Test prediction with very long text."""
        with patch("app.ml.sentiment.pipeline") as mock_pipeline:
            mock_model = MagicMock()
            mock_model.return_value = [{"label": "NEGATIVE", "score": 0.8}]
            mock_pipeline.return_value = mock_model
            
            analyzer = SentimentAnalyzer()
            long_text = "This is a very long text. " * 1000
            result = analyzer.predict(long_text)
            
            assert result["label"] == "NEGATIVE"
            assert result["score"] == 0.8


class TestGetSentimentAnalyzer:
    """Test suite for the get_sentiment_analyzer function."""

    def test_singleton_behavior(self):
        """Test that get_sentiment_analyzer returns the same instance."""
        with patch("app.ml.sentiment.pipeline") as mock_pipeline:
            mock_pipeline.return_value = MagicMock()
            
            analyzer1 = get_sentiment_analyzer()
            analyzer2 = get_sentiment_analyzer()
            
            assert analyzer1 is analyzer2

    @patch("app.ml.sentiment._sentiment_analyzer", None)
    def test_lazy_initialization(self):
        """Test that analyzer is created lazily."""
        with patch("app.ml.sentiment.pipeline") as mock_pipeline:
            mock_pipeline.return_value = MagicMock()
            
            analyzer = get_sentiment_analyzer()
            assert analyzer is not None
            assert isinstance(analyzer, SentimentAnalyzer)

    @patch("app.ml.sentiment._sentiment_analyzer", None)
    def test_initialization_with_config(self):
        """Test that analyzer is initialized with config."""
        with patch("app.ml.sentiment.pipeline") as mock_pipeline:
            mock_pipeline.return_value = MagicMock()
            
            analyzer = get_sentiment_analyzer()
            assert analyzer.settings.model_name == "distilbert-base-uncased-finetuned-sst-2-english"