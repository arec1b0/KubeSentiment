"""Tests for BaseModelMetrics helper methods.

This module tests the common helper methods extracted to BaseModelMetrics
to ensure they work correctly for both PyTorch and ONNX implementations.
"""

import pytest

from app.models.base import BaseModelMetrics


@pytest.mark.unit
class TestPreprocessText:
    """Test suite for _preprocess_text method."""

    def test_strips_whitespace(self):
        """Test that leading/trailing whitespace is removed."""
        base = BaseModelMetrics()
        result = base._preprocess_text("  hello world  ", max_length=100)
        assert result == "hello world"

    def test_truncates_long_text(self):
        """Test that text longer than max_length is truncated."""
        base = BaseModelMetrics()
        long_text = "a" * 100
        result = base._preprocess_text(long_text, max_length=50)
        assert len(result) == 50
        assert result == "a" * 50

    def test_handles_exact_length(self):
        """Test that text at exact max_length is not truncated."""
        base = BaseModelMetrics()
        text = "a" * 50
        result = base._preprocess_text(text, max_length=50)
        assert result == text


@pytest.mark.unit
class TestPreprocessBatchTexts:
    """Test suite for _preprocess_batch_texts method."""

    def test_filters_empty_texts(self):
        """Test that empty and whitespace-only texts are filtered."""
        base = BaseModelMetrics()
        texts = ["hello", "  ", "", "world"]
        valid_texts, valid_indices = base._preprocess_batch_texts(texts, max_length=100)
        
        assert valid_texts == ["hello", "world"]
        assert valid_indices == [0, 3]

    def test_truncates_batch_texts(self):
        """Test that all texts in batch are truncated if needed."""
        base = BaseModelMetrics()
        texts = ["a" * 100, "b" * 50, "c" * 200]
        valid_texts, valid_indices = base._preprocess_batch_texts(texts, max_length=50)
        
        assert len(valid_texts) == 3
        assert all(len(text) == 50 for text in valid_texts)
        assert valid_texts[0] == "a" * 50
        assert valid_texts[1] == "b" * 50
        assert valid_texts[2] == "c" * 50

    def test_handles_all_empty_texts(self):
        """Test that all empty texts returns empty lists."""
        base = BaseModelMetrics()
        texts = ["", "  ", "   "]
        valid_texts, valid_indices = base._preprocess_batch_texts(texts, max_length=100)
        
        assert valid_texts == []
        assert valid_indices == []


@pytest.mark.unit
class TestBuildBatchResults:
    """Test suite for _build_batch_results method."""

    def test_builds_results_for_valid_texts(self):
        """Test that results are correctly built for valid texts."""
        base = BaseModelMetrics()
        raw_results = [
            {"label": "POSITIVE", "score": 0.9},
            {"label": "NEGATIVE", "score": 0.8},
        ]
        valid_indices = [0, 2]
        
        results = base._build_batch_results(
            raw_results, valid_indices, total_count=3, inference_time_ms=100.0
        )
        
        assert len(results) == 3
        assert results[0]["label"] == "POSITIVE"
        assert results[0]["score"] == 0.9
        assert results[0]["inference_time_ms"] == 50.0  # 100 / 2 valid texts
        
        assert results[1]["error"] == "Invalid or empty input"
        assert results[1]["label"] is None
        
        assert results[2]["label"] == "NEGATIVE"
        assert results[2]["score"] == 0.8

    def test_handles_all_invalid_texts(self):
        """Test that all invalid texts get error placeholders."""
        base = BaseModelMetrics()
        raw_results = []
        valid_indices = []
        
        results = base._build_batch_results(
            raw_results, valid_indices, total_count=3, inference_time_ms=0.0
        )
        
        assert len(results) == 3
        assert all(r["error"] == "Invalid or empty input" for r in results)
        assert all(r["label"] is None for r in results)

    def test_calculates_per_text_time(self):
        """Test that inference time is divided among valid texts."""
        base = BaseModelMetrics()
        raw_results = [
            {"label": "POSITIVE", "score": 0.9},
            {"label": "POSITIVE", "score": 0.8},
            {"label": "POSITIVE", "score": 0.7},
        ]
        valid_indices = [0, 1, 2]
        
        results = base._build_batch_results(
            raw_results, valid_indices, total_count=3, inference_time_ms=150.0
        )
        
        assert all(r["inference_time_ms"] == 50.0 for r in results)
