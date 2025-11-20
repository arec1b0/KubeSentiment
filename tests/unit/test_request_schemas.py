"""Tests for request schema validation.

This module tests the Pydantic request schemas to ensure they properly handle
structural validation while delegating business logic validation to the service layer.
"""

import pytest
from pydantic import ValidationError

from app.api.schemas.requests import BatchTextInput, TextInput


@pytest.mark.unit
class TestTextInputValidation:
    """Test suite for TextInput schema validation.

    These tests verify that TextInput performs STRUCTURAL validation only,
    not business logic validation (which is handled in the service layer).
    """

    def test_valid_text_input(self):
        """Test that valid text input is accepted and stripped."""
        text_input = TextInput(text="  This is valid text  ")

        assert text_input.text == "This is valid text"
        assert isinstance(text_input.text, str)

    def test_empty_text_raises_error(self):
        """Test that empty text raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TextInput(text="")

        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert "empty" in str(errors[0]["msg"]).lower() or "whitespace" in str(errors[0]["msg"]).lower()

    def test_whitespace_only_text_raises_error(self):
        """Test that whitespace-only text raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TextInput(text="   ")

        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert "empty" in str(errors[0]["msg"]).lower() or "whitespace" in str(errors[0]["msg"]).lower()

    def test_text_with_leading_trailing_whitespace_is_stripped(self):
        """Test that leading and trailing whitespace is stripped."""
        text_input = TextInput(text="  test content  \n")

        assert text_input.text == "test content"

    def test_long_text_is_accepted_by_schema(self):
        """Test that very long text is accepted by the schema.

        Business logic validation (max_text_length) is handled in the service layer,
        so the schema should accept long texts.
        """
        long_text = "a" * 20000  # Longer than typical max_text_length
        text_input = TextInput(text=long_text)

        assert text_input.text == long_text
        assert len(text_input.text) == 20000

    def test_unicode_text_is_accepted(self):
        """Test that Unicode text is properly handled."""
        unicode_text = "Hello 世界 🌍 مرحبا"
        text_input = TextInput(text=unicode_text)

        assert text_input.text == unicode_text

    def test_text_with_newlines_is_accepted(self):
        """Test that text with newlines is accepted."""
        multiline_text = "Line 1\nLine 2\nLine 3"
        text_input = TextInput(text=multiline_text)

        assert text_input.text == multiline_text


@pytest.mark.unit
class TestBatchTextInputValidation:
    """Test suite for BatchTextInput schema validation.

    These tests verify that BatchTextInput performs STRUCTURAL validation only,
    not business logic validation (which is handled in the service layer).
    """

    def test_valid_batch_input(self):
        """Test that valid batch input is accepted."""
        batch_input = BatchTextInput(
            texts=["Text 1", "Text 2", "Text 3"],
            priority="medium"
        )

        assert len(batch_input.texts) == 3
        assert batch_input.priority == "medium"
        assert batch_input.max_batch_size is None
        assert batch_input.timeout_seconds == 300  # default

    def test_empty_batch_raises_error(self):
        """Test that empty batch raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            BatchTextInput(texts=[])

        errors = exc_info.value.errors()
        assert any("empty" in str(error["msg"]).lower() for error in errors)

    def test_batch_exceeding_hard_limit_raises_error(self):
        """Test that batch exceeding 1000 items raises validation error."""
        too_many_texts = ["text"] * 1001

        with pytest.raises(ValidationError) as exc_info:
            BatchTextInput(texts=too_many_texts)

        errors = exc_info.value.errors()
        assert any("1000" in str(error["msg"]) for error in errors)

    def test_batch_with_empty_text_raises_error(self):
        """Test that batch with empty text raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            BatchTextInput(texts=["Valid text", "", "Another valid text"])

        errors = exc_info.value.errors()
        assert any("empty" in str(error["msg"]).lower() or "whitespace" in str(error["msg"]).lower() for error in errors)

    def test_batch_with_whitespace_only_text_raises_error(self):
        """Test that batch with whitespace-only text raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            BatchTextInput(texts=["Valid text", "   ", "Another valid text"])

        errors = exc_info.value.errors()
        assert any("empty" in str(error["msg"]).lower() or "whitespace" in str(error["msg"]).lower() for error in errors)

    def test_batch_with_long_texts_is_accepted_by_schema(self):
        """Test that batch with very long texts is accepted by the schema.

        Business logic validation (max_text_length) is handled in the service layer,
        so the schema should accept long texts.
        """
        long_texts = ["a" * 20000, "b" * 20000]  # Longer than typical max_text_length
        batch_input = BatchTextInput(texts=long_texts)

        assert len(batch_input.texts) == 2
        assert len(batch_input.texts[0]) == 20000

    def test_batch_priority_validation(self):
        """Test that priority field validates correctly."""
        # Valid priorities
        for priority in ["low", "medium", "high"]:
            batch_input = BatchTextInput(texts=["test"], priority=priority)
            assert batch_input.priority == priority

        # Invalid priority
        with pytest.raises(ValidationError):
            BatchTextInput(texts=["test"], priority="invalid")

    def test_batch_max_batch_size_validation(self):
        """Test that max_batch_size field validates correctly."""
        # Valid max_batch_size
        batch_input = BatchTextInput(texts=["test"], max_batch_size=100)
        assert batch_input.max_batch_size == 100

        # Invalid max_batch_size (too large)
        with pytest.raises(ValidationError):
            BatchTextInput(texts=["test"], max_batch_size=1001)

        # Invalid max_batch_size (too small)
        with pytest.raises(ValidationError):
            BatchTextInput(texts=["test"], max_batch_size=0)

    def test_batch_timeout_validation(self):
        """Test that timeout_seconds field validates correctly."""
        # Valid timeout
        batch_input = BatchTextInput(texts=["test"], timeout_seconds=600)
        assert batch_input.timeout_seconds == 600

        # Invalid timeout (too large)
        with pytest.raises(ValidationError):
            BatchTextInput(texts=["test"], timeout_seconds=3601)

        # Invalid timeout (too small)
        with pytest.raises(ValidationError):
            BatchTextInput(texts=["test"], timeout_seconds=9)

    def test_batch_default_values(self):
        """Test that default values are properly set."""
        batch_input = BatchTextInput(texts=["test"])

        assert batch_input.priority == "medium"
        assert batch_input.max_batch_size is None
        assert batch_input.timeout_seconds == 300


@pytest.mark.unit
class TestSeparationOfConcerns:
    """Test suite to verify separation of concerns.

    These tests verify that structural validation happens in the schema layer
    while business logic validation is delegated to the service layer.
    """

    def test_schema_does_not_import_settings(self):
        """Test that request schemas don't import get_settings."""
        from app.api.schemas import requests
        import inspect

        source = inspect.getsource(requests)

        # Should not import get_settings
        assert "from app.core.config import get_settings" not in source
        assert "get_settings()" not in source

    def test_schema_validation_is_testable_without_settings(self):
        """Test that schema validation works without any settings configuration.

        This proves that the schema is decoupled from the settings/config layer.
        """
        # This should work without any settings being configured
        text_input = TextInput(text="test")
        assert text_input.text == "test"

        batch_input = BatchTextInput(texts=["test1", "test2"])
        assert len(batch_input.texts) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
