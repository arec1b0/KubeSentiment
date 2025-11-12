import logging

from app.utils.logging_adapters import (
    StdLibLoggerAdapter,
    get_fallback_contextual_logger,
    get_fallback_logger,
)


def test_adapter_formats_extra_fields(caplog):
    adapter = StdLibLoggerAdapter("test.logging")

    with caplog.at_level(logging.INFO):
        adapter.info("processed batch", request_id="abc123", duration_ms=42)

    assert "processed batch | request_id='abc123', duration_ms=42" in caplog.text


def test_exception_logs_exc_info(caplog):
    adapter = StdLibLoggerAdapter("test.logging")

    with caplog.at_level(logging.ERROR):
        adapter.exception("batch failed")

    record = next(rec for rec in caplog.records if rec.message.startswith("batch failed"))
    assert record.exc_info is not None


def test_fallback_helpers_return_new_adapters():
    adapter = get_fallback_logger("test.logger")
    contextual_adapter = get_fallback_contextual_logger("test.logger")

    assert isinstance(adapter, StdLibLoggerAdapter)
    assert isinstance(contextual_adapter, StdLibLoggerAdapter)
    assert adapter is not contextual_adapter
