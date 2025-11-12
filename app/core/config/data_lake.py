"""Data lake integration configuration for cloud storage."""

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class DataLakeConfig(BaseSettings):
    """Data lake integration configuration for streaming predictions to cloud storage.

    Attributes:
        data_lake_enabled: Enable data lake integration.
        data_lake_provider: Cloud storage provider (s3, gcs, or azure).
        data_lake_bucket: Storage bucket/container name.
        data_lake_prefix: Path prefix for stored predictions.
        data_lake_batch_size: Number of predictions to batch before writing.
        data_lake_batch_timeout_seconds: Maximum seconds to wait before flushing batch.
        data_lake_compression: Parquet compression codec.
        data_lake_partition_by: Partition strategy (date, hour, or model).
        data_lake_s3_region: AWS region for S3.
        data_lake_s3_endpoint_url: Custom S3 endpoint URL (for S3-compatible storage).
        data_lake_gcs_project: GCP project ID for GCS.
        data_lake_gcs_credentials_path: Path to GCP service account credentials JSON.
        data_lake_azure_account_name: Azure storage account name.
        data_lake_azure_account_key: Azure storage account key.
        data_lake_azure_connection_string: Azure storage connection string.
        data_lake_enable_athena: Add metadata for AWS Athena compatibility.
        data_lake_enable_bigquery: Add metadata for BigQuery compatibility.
        data_lake_enable_synapse: Add metadata for Azure Synapse compatibility.
    """

    # Core settings
    data_lake_enabled: bool = Field(
        default=False,
        description="Enable data lake integration for streaming predictions",
    )
    data_lake_provider: str = Field(
        default="s3",
        description="Cloud storage provider: s3, gcs, or azure",
        pattern=r"^(s3|gcs|azure)$",
    )
    data_lake_bucket: Optional[str] = Field(
        default=None,
        description="Storage bucket/container name (e.g., my-predictions-bucket)",
    )
    data_lake_prefix: str = Field(
        default="predictions",
        description="Path prefix for stored predictions",
        min_length=1,
    )

    # Batch and performance settings
    data_lake_batch_size: int = Field(
        default=100,
        description="Number of predictions to batch before writing",
        ge=1,
        le=1000,
    )
    data_lake_batch_timeout_seconds: int = Field(
        default=30,
        description="Maximum seconds to wait before flushing batch",
        ge=5,
        le=300,
    )
    data_lake_compression: str = Field(
        default="snappy",
        description="Parquet compression codec: snappy, gzip, lz4, zstd, or none",
        pattern=r"^(snappy|gzip|lz4|zstd|none)$",
    )
    data_lake_partition_by: str = Field(
        default="date",
        description="Partition strategy: date, hour, or model",
        pattern=r"^(date|hour|model)$",
    )

    # AWS S3 settings
    data_lake_s3_region: str = Field(
        default="us-east-1",
        description="AWS region for S3",
    )
    data_lake_s3_endpoint_url: Optional[str] = Field(
        default=None,
        description="Custom S3 endpoint URL (for S3-compatible storage)",
    )

    # GCP settings
    data_lake_gcs_project: Optional[str] = Field(
        default=None,
        description="GCP project ID for GCS",
    )
    data_lake_gcs_credentials_path: Optional[str] = Field(
        default=None,
        description="Path to GCP service account credentials JSON",
    )

    # Azure settings
    data_lake_azure_account_name: Optional[str] = Field(
        default=None,
        description="Azure storage account name",
    )
    data_lake_azure_account_key: Optional[str] = Field(
        default=None,
        description="Azure storage account key",
        exclude=True,
    )
    data_lake_azure_connection_string: Optional[str] = Field(
        default=None,
        description="Azure storage connection string",
        exclude=True,
    )

    # Query engine integration hints
    data_lake_enable_athena: bool = Field(
        default=False,
        description="Add metadata for AWS Athena compatibility",
    )
    data_lake_enable_bigquery: bool = Field(
        default=False,
        description="Add metadata for BigQuery compatibility",
    )
    data_lake_enable_synapse: bool = Field(
        default=False,
        description="Add metadata for Azure Synapse compatibility",
    )

    class Config:
        """Pydantic configuration."""

        env_prefix = "MLOPS_"
        env_file = ".env"
        case_sensitive = False
