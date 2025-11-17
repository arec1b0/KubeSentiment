"""
Data Lake Writer Service for streaming predictions to cloud storage.

This module provides an async writer service that batches predictions and writes
them to cloud storage (S3, GCS, Azure Blob) in Parquet format for efficient
querying with Athena, BigQuery, or Azure Synapse.
"""

import asyncio
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pyarrow as pa
import pyarrow.parquet as pq

from app.core.config import Settings
from app.core.logging import get_logger
from app.interfaces.storage_interface import IDataWriter

logger = get_logger(__name__)


class DataLakeWriter(IDataWriter):
    """Async writer for streaming predictions to data lake storage.

    This service batches predictions and writes them to cloud storage in Parquet
    format, enabling long-term analytics and ML research with tools like Athena,
    BigQuery, or Azure Synapse.

    Attributes:
        settings: Application configuration settings.
        buffer: In-memory buffer for batching predictions.
        batch_task: Background task for periodic flushing.
        storage_client: Cloud storage client (S3, GCS, or Azure).
    """

    def __init__(self, settings: Settings):
        """Initialize the data lake writer.

        Args:
            settings: Application configuration settings.
        """
        self.settings = settings
        self.buffer: List[Dict[str, Any]] = []
        self.buffer_lock = asyncio.Lock()
        self.batch_task: Optional[asyncio.Task] = None
        self.storage_client = None
        self._initialized = False
        self.logger = get_logger(__name__)

        if settings.data_lake_enabled:
            self._initialize_storage_client()

    def _initialize_storage_client(self):
        """Initialize the appropriate cloud storage client based on provider."""
        try:
            if self.settings.data_lake_provider == "s3":
                self._initialize_s3_client()
            elif self.settings.data_lake_provider == "gcs":
                self._initialize_gcs_client()
            elif self.settings.data_lake_provider == "azure":
                self._initialize_azure_client()
            self._initialized = True
            self.logger.info(
                f"Data lake writer initialized with {self.settings.data_lake_provider} storage"
            )
        except Exception as e:
            self.logger.error(
                f"Failed to initialize data lake writer: {e}",
                exc_info=True,
            )
            self._initialized = False

    def _initialize_s3_client(self):
        """Initialize AWS S3 client."""
        import boto3

        session = boto3.Session()
        self.storage_client = session.client(
            "s3",
            region_name=self.settings.data_lake_s3_region,
            endpoint_url=self.settings.data_lake_s3_endpoint_url,
        )
        self.logger.info(f"Initialized S3 client for region {self.settings.data_lake_s3_region}")

    def _initialize_gcs_client(self):
        """Initialize Google Cloud Storage client."""
        from google.cloud import storage

        if self.settings.data_lake_gcs_credentials_path:
            self.storage_client = storage.Client.from_service_account_json(
                self.settings.data_lake_gcs_credentials_path
            )
        else:
            # Use default credentials (e.g., from GOOGLE_APPLICATION_CREDENTIALS env var)
            self.storage_client = storage.Client(project=self.settings.data_lake_gcs_project)
        self.logger.info("Initialized GCS client")

    def _initialize_azure_client(self):
        """Initialize Azure Blob Storage client."""
        from azure.storage.blob import BlobServiceClient

        if self.settings.data_lake_azure_connection_string:
            self.storage_client = BlobServiceClient.from_connection_string(
                self.settings.data_lake_azure_connection_string
            )
        elif (
            self.settings.data_lake_azure_account_name and self.settings.data_lake_azure_account_key
        ):
            account_url = (
                f"https://{self.settings.data_lake_azure_account_name}.blob.core.windows.net"
            )
            self.storage_client = BlobServiceClient(
                account_url=account_url,
                credential=self.settings.data_lake_azure_account_key,
            )
        else:
            raise ValueError(
                "Azure storage requires either connection_string or account_name + account_key"
            )
        self.logger.info("Initialized Azure Blob Storage client")

    async def start(self):
        """Start the background batch flushing task."""
        if not self.settings.data_lake_enabled or not self._initialized:
            return

        if self.batch_task is None or self.batch_task.done():
            self.batch_task = asyncio.create_task(self._batch_flush_loop())
            self.logger.info("Started data lake writer batch flush task")

    async def stop(self):
        """Stop the background task and flush remaining data."""
        if self.batch_task and not self.batch_task.done():
            self.batch_task.cancel()
            try:
                await self.batch_task
            except asyncio.CancelledError:
                pass

        # Flush any remaining data
        await self.flush()
        self.logger.info("Stopped data lake writer")

    async def write_prediction(self, prediction_data: Dict[str, Any]):
        """Add a prediction to the buffer for async writing.

        Args:
            prediction_data: Prediction data including text, label, score, features, etc.
        """
        if not self.settings.data_lake_enabled or not self._initialized:
            return

        # Enrich prediction with metadata
        enriched_data = self._enrich_prediction(prediction_data)

        async with self.buffer_lock:
            self.buffer.append(enriched_data)

            # Flush if batch size reached
            if len(self.buffer) >= self.settings.data_lake_batch_size:
                asyncio.create_task(self.flush())

    def _enrich_prediction(self, prediction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich prediction with metadata for analytics.

        Args:
            prediction_data: Raw prediction data.

        Returns:
            Enriched prediction with timestamp, version, and other metadata.
        """
        now = datetime.now(timezone.utc)

        enriched = {
            "timestamp": now.isoformat(),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "hour": now.hour,
            "text": prediction_data.get("text", ""),
            "label": prediction_data.get("label", ""),
            "score": prediction_data.get("score", 0.0),
            "inference_time_ms": prediction_data.get("inference_time_ms", 0.0),
            "model_name": self.settings.model_name,
            "backend": prediction_data.get("backend", "unknown"),
            "cached": prediction_data.get("cached", False),
            "app_version": self.settings.app_version,
            "environment": self.settings.environment,
        }

        # Add features if available
        if "features" in prediction_data:
            features = prediction_data["features"]
            enriched.update(
                {
                    "word_count": features.get("word_count", 0),
                    "avg_word_length": features.get("avg_word_length", 0.0),
                    "sentiment_vader": features.get("sentiment_vader", 0.0),
                    "readability_score": features.get("readability_score", 0.0),
                }
            )

        return enriched

    async def flush(self):
        """Flush the current buffer to cloud storage."""
        if not self.settings.data_lake_enabled or not self._initialized:
            return

        async with self.buffer_lock:
            if not self.buffer:
                return

            # Copy buffer and clear it
            data_to_write = self.buffer.copy()
            self.buffer.clear()

        try:
            await self._write_batch(data_to_write)
            self.logger.info(f"Flushed {len(data_to_write)} predictions to data lake")
        except Exception as e:
            self.logger.error(
                f"Failed to write batch to data lake: {e}",
                exc_info=True,
            )
            # Re-add to buffer for retry
            async with self.buffer_lock:
                self.buffer.extend(data_to_write)

    async def _batch_flush_loop(self):
        """Background task that periodically flushes the buffer."""
        while True:
            try:
                await asyncio.sleep(self.settings.data_lake_batch_timeout_seconds)
                await self.flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    f"Error in batch flush loop: {e}",
                    exc_info=True,
                )

    async def _write_batch(self, data: List[Dict[str, Any]]):
        """Write a batch of predictions to cloud storage in Parquet format.

        Args:
            data: List of prediction records to write.
        """
        if not data:
            return

        # Convert to PyArrow table
        table = self._create_parquet_table(data)

        # Generate partition path
        partition_path = self._get_partition_path(data[0])

        # Write to appropriate storage
        parquet_buffer = io.BytesIO()
        pq.write_table(
            table,
            parquet_buffer,
            compression=self.settings.data_lake_compression,
        )
        parquet_buffer.seek(0)

        # Upload to cloud storage
        if self.settings.data_lake_provider == "s3":
            await self._upload_to_s3(partition_path, parquet_buffer.getvalue())
        elif self.settings.data_lake_provider == "gcs":
            await self._upload_to_gcs(partition_path, parquet_buffer.getvalue())
        elif self.settings.data_lake_provider == "azure":
            await self._upload_to_azure(partition_path, parquet_buffer.getvalue())

    def _create_parquet_table(self, data: List[Dict[str, Any]]) -> pa.Table:
        """Create a PyArrow table from prediction data.

        Args:
            data: List of prediction records.

        Returns:
            PyArrow table ready for Parquet serialization.
        """
        # Define schema for consistency
        schema = pa.schema(
            [
                ("timestamp", pa.timestamp("us", tz="UTC")),
                ("year", pa.int32()),
                ("month", pa.int32()),
                ("day", pa.int32()),
                ("hour", pa.int32()),
                ("text", pa.string()),
                ("label", pa.string()),
                ("score", pa.float64()),
                ("inference_time_ms", pa.float64()),
                ("model_name", pa.string()),
                ("backend", pa.string()),
                ("cached", pa.bool_()),
                ("app_version", pa.string()),
                ("environment", pa.string()),
                # Optional feature columns
                ("word_count", pa.int32()),
                ("avg_word_length", pa.float64()),
                ("sentiment_vader", pa.float64()),
                ("readability_score", pa.float64()),
            ]
        )

        # Convert data to table
        # Handle missing optional fields
        for record in data:
            record.setdefault("word_count", 0)
            record.setdefault("avg_word_length", 0.0)
            record.setdefault("sentiment_vader", 0.0)
            record.setdefault("readability_score", 0.0)

        return pa.Table.from_pylist(data, schema=schema)

    def _get_partition_path(self, sample_record: Dict[str, Any]) -> str:
        """Generate partition path based on configuration.

        Args:
            sample_record: Sample record to extract partition info from.

        Returns:
            Partition path string.
        """
        timestamp = datetime.now(timezone.utc)
        base_prefix = self.settings.data_lake_prefix

        if self.settings.data_lake_partition_by == "date":
            partition = f"{base_prefix}/year={timestamp.year}/month={timestamp.month:02d}/day={timestamp.day:02d}"
        elif self.settings.data_lake_partition_by == "hour":
            partition = f"{base_prefix}/year={timestamp.year}/month={timestamp.month:02d}/day={timestamp.day:02d}/hour={timestamp.hour:02d}"
        elif self.settings.data_lake_partition_by == "model":
            partition = (
                f"{base_prefix}/model={self.settings.model_name}/"
                f"year={timestamp.year}/month={timestamp.month:02d}/day={timestamp.day:02d}"
            )
        else:
            partition = base_prefix

        # Add timestamp to filename for uniqueness
        filename = f"predictions_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.parquet"
        return f"{partition}/{filename}"

    async def _upload_to_s3(self, path: str, data: bytes):
        """Upload Parquet file to AWS S3.

        Args:
            path: S3 key path.
            data: Parquet file content.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.storage_client.put_object(
                Bucket=self.settings.data_lake_bucket,
                Key=path,
                Body=data,
                ContentType="application/x-parquet",
                Metadata={
                    "writer": "kubesentiment",
                    "version": self.settings.app_version,
                    "compression": self.settings.data_lake_compression,
                },
            ),
        )
        self.logger.debug(f"Uploaded to S3: s3://{self.settings.data_lake_bucket}/{path}")

    async def _upload_to_gcs(self, path: str, data: bytes):
        """Upload Parquet file to Google Cloud Storage.

        Args:
            path: GCS blob path.
            data: Parquet file content.
        """
        bucket = self.storage_client.bucket(self.settings.data_lake_bucket)
        blob = bucket.blob(path)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: blob.upload_from_string(
                data,
                content_type="application/x-parquet",
            ),
        )

        # Set metadata
        blob.metadata = {
            "writer": "kubesentiment",
            "version": self.settings.app_version,
            "compression": self.settings.data_lake_compression,
        }
        await loop.run_in_executor(None, blob.patch)

        self.logger.debug(f"Uploaded to GCS: gs://{self.settings.data_lake_bucket}/{path}")

    async def _upload_to_azure(self, path: str, data: bytes):
        """Upload Parquet file to Azure Blob Storage.

        Args:
            path: Blob path.
            data: Parquet file content.
        """
        container_client = self.storage_client.get_container_client(self.settings.data_lake_bucket)

        # Create container if it doesn't exist
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(None, container_client.create_container)
        except Exception:
            pass  # Container likely already exists

        blob_client = container_client.get_blob_client(path)
        await loop.run_in_executor(
            None,
            lambda: blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings={
                    "content_type": "application/x-parquet",
                },
                metadata={
                    "writer": "kubesentiment",
                    "version": self.settings.app_version,
                    "compression": self.settings.data_lake_compression,
                },
            ),
        )
        self.logger.debug(f"Uploaded to Azure: {self.settings.data_lake_bucket}/{path}")

    def get_stats(self) -> Dict[str, Any]:
        """Get current writer statistics.

        Returns:
            Dictionary with buffer size and status info.
        """
        return {
            "enabled": self.settings.data_lake_enabled,
            "initialized": self._initialized,
            "provider": self.settings.data_lake_provider,
            "buffer_size": len(self.buffer),
            "batch_size": self.settings.data_lake_batch_size,
            "batch_timeout_seconds": self.settings.data_lake_batch_timeout_seconds,
        }


# Singleton instance
_data_writer: Optional[DataLakeWriter] = None


def get_data_writer(settings: Settings) -> DataLakeWriter:
    """Get or create the global data writer instance.

    Args:
        settings: Application configuration settings.

    Returns:
        DataLakeWriter instance.
    """
    global _data_writer
    if _data_writer is None:
        _data_writer = DataLakeWriter(settings)
    return _data_writer
