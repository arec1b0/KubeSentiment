"""Metrics models for batch processing services."""

from dataclasses import dataclass


@dataclass
class ProcessingMetrics:
    """Holds metrics for the async batch processing service."""

    total_jobs: int = 0
    active_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    total_processing_time_seconds: float = 0.0
    average_processing_time_seconds: float = 0.0
    average_throughput_tps: float = 0.0
    queue_size: int = 0
    total_texts_processed: int = 0
    average_batch_size: float = 0.0
    processing_efficiency: float = 0.0

    def update_averages(self):
        """Updates calculated average metrics."""
        if self.completed_jobs > 0:
            self.average_processing_time_seconds = (
                self.total_processing_time_seconds / self.completed_jobs
            )
            if self.total_processing_time_seconds > 0:
                self.average_throughput_tps = (
                    self.total_texts_processed / self.total_processing_time_seconds
                )
            else:
                self.average_throughput_tps = 0.0
        else:
            self.average_processing_time_seconds = 0.0
            self.average_throughput_tps = 0.0

        if self.total_jobs > 0:
            self.processing_efficiency = (self.completed_jobs / self.total_jobs) * 100.0
        else:
            self.processing_efficiency = 0.0
