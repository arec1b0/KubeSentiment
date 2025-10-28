"""
Unit tests for the AnomalyBuffer service.

Tests the BoundedAnomalyBuffer class and AnomalyEntry dataclass,
including thread safety, TTL expiration, size limits, and singleton behavior.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

from app.services.anomaly_buffer import (
    AnomalyEntry,
    BoundedAnomalyBuffer,
    get_anomaly_buffer,
)


class TestAnomalyEntry:
    """Tests for the AnomalyEntry dataclass."""

    def test_default_values(self):
        """Test that AnomalyEntry has correct default values."""
        entry = AnomalyEntry()

        assert entry.id is not None
        assert len(entry.id) > 0
        assert entry.timestamp > 0
        assert entry.text == ""
        assert entry.prediction == {}
        assert entry.anomaly_score == 0.0
        assert entry.anomaly_type == "unknown"
        assert entry.metadata == {}
        assert entry.ttl_seconds == 3600

    def test_custom_values(self):
        """Test AnomalyEntry with custom values."""
        entry = AnomalyEntry(
            text="Test text",
            prediction={"label": "positive", "score": 0.95},
            anomaly_score=0.85,
            anomaly_type="high_confidence",
            metadata={"source": "test"},
            ttl_seconds=1800,
        )

        assert entry.text == "Test text"
        assert entry.prediction == {"label": "positive", "score": 0.95}
        assert entry.anomaly_score == 0.85
        assert entry.anomaly_type == "high_confidence"
        assert entry.metadata == {"source": "test"}
        assert entry.ttl_seconds == 1800

    def test_unique_ids(self):
        """Test that each AnomalyEntry gets a unique ID."""
        entry1 = AnomalyEntry()
        entry2 = AnomalyEntry()

        assert entry1.id != entry2.id

    def test_is_expired_not_expired(self):
        """Test is_expired returns False for fresh entries."""
        entry = AnomalyEntry(ttl_seconds=3600)
        assert not entry.is_expired()

    def test_is_expired_expired(self):
        """Test is_expired returns True for expired entries."""
        entry = AnomalyEntry(ttl_seconds=0)
        time.sleep(0.01)  # Small delay to ensure expiration
        assert entry.is_expired()

    def test_is_expired_edge_case(self):
        """Test is_expired at the boundary of expiration."""
        entry = AnomalyEntry(ttl_seconds=1)
        assert not entry.is_expired()
        time.sleep(1.1)
        assert entry.is_expired()

    def test_to_dict(self):
        """Test to_dict returns correct dictionary representation."""
        entry = AnomalyEntry(
            text="Test",
            prediction={"label": "positive"},
            anomaly_score=0.75,
            anomaly_type="test_type",
            metadata={"key": "value"},
            ttl_seconds=3600,
        )

        result = entry.to_dict()

        assert result["id"] == entry.id
        assert result["timestamp"] == entry.timestamp
        assert "age_seconds" in result
        assert result["age_seconds"] >= 0
        assert result["text"] == "Test"
        assert result["prediction"] == {"label": "positive"}
        assert result["anomaly_score"] == 0.75
        assert result["anomaly_type"] == "test_type"
        assert result["metadata"] == {"key": "value"}
        assert result["expired"] is False

    def test_to_dict_expired(self):
        """Test to_dict correctly marks expired entries."""
        entry = AnomalyEntry(ttl_seconds=0)
        time.sleep(0.01)

        result = entry.to_dict()
        assert result["expired"] is True


class TestBoundedAnomalyBuffer:
    """Tests for the BoundedAnomalyBuffer class."""

    @pytest.fixture
    def buffer(self):
        """Create a fresh buffer for each test."""
        return BoundedAnomalyBuffer(max_size=100, default_ttl=3600)

    def test_initialization(self):
        """Test buffer initialization with default and custom values."""
        # Default initialization
        buffer1 = BoundedAnomalyBuffer()
        assert buffer1.max_size == 10000
        assert buffer1.default_ttl == 3600

        # Custom initialization
        buffer2 = BoundedAnomalyBuffer(max_size=50, default_ttl=1800)
        assert buffer2.max_size == 50
        assert buffer2.default_ttl == 1800

    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    def test_add_single_entry(self, mock_size, mock_detected, buffer):
        """Test adding a single entry to the buffer."""
        entry_id = buffer.add(
            text="Test text",
            anomaly_score=0.8,
            anomaly_type="test",
        )

        assert entry_id is not None
        assert len(entry_id) > 0
        mock_detected.assert_called_once_with("test")
        mock_size.assert_called_once_with(1)

    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    def test_add_multiple_entries(self, mock_size, mock_detected, buffer):
        """Test adding multiple entries to the buffer."""
        ids = []
        for i in range(10):
            entry_id = buffer.add(
                text=f"Text {i}",
                anomaly_score=0.5 + i * 0.05,
                anomaly_type=f"type_{i}",
            )
            ids.append(entry_id)

        assert len(set(ids)) == 10  # All IDs are unique
        assert mock_detected.call_count == 10
        assert mock_size.call_count == 10

    @patch("app.services.anomaly_buffer.record_anomaly_buffer_eviction")
    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    def test_add_exceeds_max_size(self, mock_size, mock_detected, mock_eviction):
        """Test that oldest entries are evicted when max_size is exceeded."""
        buffer = BoundedAnomalyBuffer(max_size=5, default_ttl=3600)

        ids = []
        for i in range(7):
            entry_id = buffer.add(text=f"Text {i}", anomaly_type="test")
            ids.append(entry_id)

        # First two entries should have been evicted
        assert buffer.get(ids[0]) is None
        assert buffer.get(ids[1]) is None

        # Last five entries should still exist
        for i in range(2, 7):
            assert buffer.get(ids[i]) is not None

        # Check eviction was recorded twice (for entries 0 and 1)
        assert mock_eviction.call_count == 2
        mock_eviction.assert_called_with("size_limit")

    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    def test_get_existing_entry(self, mock_size, mock_detected, buffer):
        """Test retrieving an existing entry."""
        entry_id = buffer.add(
            text="Test",
            anomaly_score=0.9,
            anomaly_type="test",
        )

        retrieved = buffer.get(entry_id)

        assert retrieved is not None
        assert retrieved.id == entry_id
        assert retrieved.text == "Test"
        assert retrieved.anomaly_score == 0.9

    def test_get_nonexistent_entry(self, buffer):
        """Test retrieving a non-existent entry returns None."""
        result = buffer.get("nonexistent-id")
        assert result is None

    @patch("app.services.anomaly_buffer.record_anomaly_buffer_eviction")
    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    def test_get_expired_entry(self, mock_size, mock_detected, mock_eviction):
        """Test that expired entries are removed when retrieved."""
        buffer = BoundedAnomalyBuffer(max_size=100, default_ttl=3600)

        entry_id = buffer.add(
            text="Test",
            ttl_seconds=0,
            anomaly_type="test",
        )

        time.sleep(0.01)

        result = buffer.get(entry_id)

        assert result is None
        mock_eviction.assert_called_with("expired")

    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    def test_get_all_empty_buffer(self, mock_size, mock_detected, buffer):
        """Test get_all returns empty list for empty buffer."""
        result = buffer.get_all()
        assert result == []

    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    def test_get_all_with_entries(self, mock_size, mock_detected, buffer):
        """Test get_all returns all active entries."""
        ids = []
        for i in range(5):
            entry_id = buffer.add(text=f"Text {i}", anomaly_type="test")
            ids.append(entry_id)

        result = buffer.get_all()

        assert len(result) == 5
        result_ids = {entry.id for entry in result}
        assert result_ids == set(ids)

    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    def test_get_all_filters_expired(self, mock_size, mock_detected):
        """Test get_all filters out expired entries."""
        buffer = BoundedAnomalyBuffer(max_size=100, default_ttl=3600)

        # Add entries with different TTLs
        fresh_id = buffer.add(text="Fresh", ttl_seconds=3600, anomaly_type="test")
        buffer.add(text="Expired", ttl_seconds=0, anomaly_type="test")

        time.sleep(0.01)

        result = buffer.get_all()

        assert len(result) == 1
        assert result[0].id == fresh_id

    @patch("app.services.anomaly_buffer.record_anomaly_buffer_eviction")
    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    def test_cleanup_expired(self, mock_size, mock_detected, mock_eviction):
        """Test manual cleanup of expired entries."""
        buffer = BoundedAnomalyBuffer(max_size=100, default_ttl=3600)

        # Add mix of fresh and expired entries
        buffer.add(text="Fresh 1", ttl_seconds=3600, anomaly_type="test")
        buffer.add(text="Expired 1", ttl_seconds=0, anomaly_type="test")
        buffer.add(text="Fresh 2", ttl_seconds=3600, anomaly_type="test")
        buffer.add(text="Expired 2", ttl_seconds=0, anomaly_type="test")

        time.sleep(0.01)

        removed_count = buffer.cleanup_expired()

        assert removed_count == 2
        mock_eviction.assert_called_with("expired")

    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    def test_cleanup_expired_no_expired_entries(self, mock_size, mock_detected, buffer):
        """Test cleanup when no entries are expired."""
        buffer.add(text="Fresh", ttl_seconds=3600, anomaly_type="test")

        removed_count = buffer.cleanup_expired()

        assert removed_count == 0

    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    def test_get_stats(self, mock_size, mock_detected, buffer):
        """Test get_stats returns correct statistics."""
        # Empty buffer
        stats = buffer.get_stats()
        assert stats["current_size"] == 0
        assert stats["max_size"] == 100
        assert stats["utilization"] == 0.0

        # Add some entries
        for i in range(25):
            buffer.add(text=f"Text {i}", anomaly_type="test")

        stats = buffer.get_stats()
        assert stats["current_size"] == 25
        assert stats["max_size"] == 100
        assert stats["utilization"] == 25.0

    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    def test_thread_safety_concurrent_adds(self, mock_size, mock_detected):
        """Test thread safety with concurrent add operations."""
        buffer = BoundedAnomalyBuffer(max_size=1000, default_ttl=3600)

        def add_entries(start_idx, count):
            ids = []
            for i in range(count):
                entry_id = buffer.add(
                    text=f"Text {start_idx + i}",
                    anomaly_type="test",
                )
                ids.append(entry_id)
            return ids

        # Add entries concurrently from multiple threads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(add_entries, i * 10, 10)
                for i in range(10)
            ]
            results = [f.result() for f in futures]

        # Flatten the list of IDs
        all_ids = [id for sublist in results for id in sublist]

        # Check all entries are unique
        assert len(set(all_ids)) == 100

        # Check all entries can be retrieved
        stats = buffer.get_stats()
        assert stats["current_size"] == 100

    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    def test_thread_safety_concurrent_reads(self, mock_size, mock_detected):
        """Test thread safety with concurrent read operations."""
        buffer = BoundedAnomalyBuffer(max_size=100, default_ttl=3600)

        # Add entries first
        ids = []
        for i in range(20):
            entry_id = buffer.add(text=f"Text {i}", anomaly_type="test")
            ids.append(entry_id)

        def read_entries(entry_ids):
            results = []
            for entry_id in entry_ids:
                entry = buffer.get(entry_id)
                if entry:
                    results.append(entry.id)
            return results

        # Read entries concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(read_entries, ids)
                for _ in range(5)
            ]
            results = [f.result() for f in futures]

        # All reads should return the same entries
        for result in results:
            assert len(result) == 20

    @patch("app.services.anomaly_buffer.record_anomaly_detected")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_size")
    @patch("app.services.anomaly_buffer.record_anomaly_buffer_eviction")
    def test_thread_safety_mixed_operations(self, mock_eviction, mock_size, mock_detected):
        """Test thread safety with mixed read/write/cleanup operations."""
        buffer = BoundedAnomalyBuffer(max_size=200, default_ttl=3600)

        def add_entries():
            for i in range(10):
                buffer.add(text=f"Text {i}", anomaly_type="test")

        def read_all():
            return buffer.get_all()

        def cleanup():
            return buffer.cleanup_expired()

        def get_statistics():
            return buffer.get_stats()

        # Run mixed operations concurrently
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            futures.extend([executor.submit(add_entries) for _ in range(3)])
            futures.extend([executor.submit(read_all) for _ in range(3)])
            futures.append(executor.submit(cleanup))
            futures.append(executor.submit(get_statistics))

            # Wait for all to complete
            for f in futures:
                f.result()

        # Buffer should be in a consistent state
        stats = buffer.get_stats()
        assert stats["current_size"] == 30
        assert stats["max_size"] == 200


class TestGetAnomalyBuffer:
    """Tests for the get_anomaly_buffer singleton function."""

    def teardown_method(self):
        """Reset the singleton after each test."""
        import app.services.anomaly_buffer
        app.services.anomaly_buffer._anomaly_buffer = None

    @patch("app.services.anomaly_buffer.get_settings")
    def test_singleton_initialization(self, mock_get_settings):
        """Test that get_anomaly_buffer creates a singleton instance."""
        mock_settings = MagicMock()
        mock_settings.anomaly_buffer_max_size = 5000
        mock_settings.anomaly_buffer_default_ttl = 7200
        mock_get_settings.return_value = mock_settings

        buffer1 = get_anomaly_buffer()
        buffer2 = get_anomaly_buffer()

        # Same instance
        assert buffer1 is buffer2

        # Correct configuration
        assert buffer1.max_size == 5000
        assert buffer1.default_ttl == 7200

        # get_settings should only be called once
        assert mock_get_settings.call_count == 1

    @patch("app.services.anomaly_buffer.get_settings")
    def test_singleton_uses_settings(self, mock_get_settings):
        """Test that the singleton uses values from settings."""
        mock_settings = MagicMock()
        mock_settings.anomaly_buffer_max_size = 2500
        mock_settings.anomaly_buffer_default_ttl = 1800
        mock_get_settings.return_value = mock_settings

        buffer = get_anomaly_buffer()

        assert buffer.max_size == 2500
        assert buffer.default_ttl == 1800
