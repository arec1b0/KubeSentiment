"""
Advanced Metrics and KPIs for KubeSentiment.

This module provides comprehensive metrics beyond basic observability:
- Business metrics (accuracy trends, user satisfaction)
- Quality metrics (confidence distribution, rejection rates)
- Cost metrics (inference cost, ROI tracking)
- Performance metrics (latency percentiles, throughput)
- Custom SLO/SLA tracking
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
import threading

from prometheus_client import Counter, Histogram, Gauge, Summary

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PredictionRecord:
    """Record of a single prediction for analytics."""
    timestamp: datetime
    text_length: int
    confidence: float
    prediction: str
    latency_ms: float
    backend: str
    cached: bool
    cost_estimate: float = 0.0


class AdvancedMetricsCollector:
    """
    Advanced metrics collector for comprehensive KPI tracking.

    Features:
    - Business metrics: prediction quality, user engagement
    - Quality metrics: confidence trends, low-confidence alerts
    - Cost metrics: per-prediction cost, monthly burn rate
    - Performance metrics: detailed latency breakdown
    - SLO tracking: availability, latency targets

    Example:
        >>> metrics = AdvancedMetricsCollector()
        >>> metrics.record_prediction(
        ...     text_length=50,
        ...     confidence=0.95,
        ...     prediction="POSITIVE",
        ...     latency_ms=25.5,
        ...     backend="onnx",
        ...     cached=False
        ... )
        >>> kpis = metrics.get_business_kpis()
    """

    def __init__(
        self,
        enable_detailed_tracking: bool = True,
        history_window_hours: int = 24,
        cost_per_1k_predictions: float = 0.01
    ):
        """
        Initialize advanced metrics collector.

        Args:
            enable_detailed_tracking: Enable detailed per-prediction tracking
            history_window_hours: Hours of history to keep in memory
            cost_per_1k_predictions: Cost per 1000 predictions (USD)
        """
        self.enable_detailed_tracking = enable_detailed_tracking
        self.history_window_hours = history_window_hours
        self.cost_per_1k_predictions = cost_per_1k_predictions

        # Prediction history
        self.prediction_history: deque = deque(maxlen=10000)

        # Counters by category
        self.predictions_by_label = defaultdict(int)
        self.predictions_by_confidence_bucket = defaultdict(int)
        self.predictions_by_backend = defaultdict(int)

        # Quality tracking
        self.low_confidence_predictions = deque(maxlen=1000)
        self.high_confidence_predictions = deque(maxlen=1000)

        # Performance tracking
        self.latency_by_backend = defaultdict(list)

        # Cost tracking
        self.total_cost = 0.0
        self.cost_by_day = defaultdict(float)

        # Thread safety
        self._lock = threading.Lock()

        # Prometheus metrics
        self._init_prometheus_metrics()

        logger.info("Advanced metrics collector initialized")

    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics."""
        # Business metrics
        self.business_predictions_total = Counter(
            'sentiment_business_predictions_total',
            'Total predictions by label and confidence bucket',
            ['label', 'confidence_bucket']
        )

        self.business_confidence_distribution = Histogram(
            'sentiment_business_confidence_distribution',
            'Distribution of prediction confidence scores',
            buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]
        )

        # Quality metrics
        self.quality_low_confidence_total = Counter(
            'sentiment_quality_low_confidence_total',
            'Total low confidence predictions (<0.6)',
            ['label']
        )

        self.quality_rejection_rate = Gauge(
            'sentiment_quality_rejection_rate',
            'Percentage of predictions below confidence threshold'
        )

        # Cost metrics
        self.cost_total_usd = Counter(
            'sentiment_cost_total_usd',
            'Total inference cost in USD'
        )

        self.cost_per_prediction_usd = Gauge(
            'sentiment_cost_per_prediction_usd',
            'Average cost per prediction in USD'
        )

        self.cost_monthly_burn_rate_usd = Gauge(
            'sentiment_cost_monthly_burn_rate_usd',
            'Estimated monthly cost burn rate in USD'
        )

        # Performance metrics
        self.performance_latency_detailed = Histogram(
            'sentiment_performance_latency_detailed_ms',
            'Detailed latency distribution',
            ['backend', 'cached'],
            buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
        )

        self.performance_throughput = Gauge(
            'sentiment_performance_throughput_rps',
            'Current throughput in requests per second'
        )

        # SLO metrics
        self.slo_availability = Gauge(
            'sentiment_slo_availability_percent',
            'Service availability percentage'
        )

        self.slo_latency_p95_ms = Gauge(
            'sentiment_slo_latency_p95_ms',
            'P95 latency in milliseconds'
        )

        self.slo_latency_p99_ms = Gauge(
            'sentiment_slo_latency_p99_ms',
            'P99 latency in milliseconds'
        )

        # User engagement metrics
        self.engagement_unique_texts_total = Gauge(
            'sentiment_engagement_unique_texts_total',
            'Number of unique texts analyzed'
        )

        self.engagement_avg_text_length = Gauge(
            'sentiment_engagement_avg_text_length',
            'Average text length in characters'
        )

    def record_prediction(
        self,
        text_length: int,
        confidence: float,
        prediction: str,
        latency_ms: float,
        backend: str = "pytorch",
        cached: bool = False,
        text_hash: Optional[str] = None
    ) -> None:
        """
        Record a prediction for metrics tracking.

        Args:
            text_length: Length of input text
            confidence: Prediction confidence
            prediction: Predicted label
            latency_ms: Inference latency in milliseconds
            backend: Model backend used
            cached: Whether result was cached
            text_hash: Optional hash of text for uniqueness tracking
        """
        with self._lock:
            # Create prediction record
            cost = self.cost_per_1k_predictions / 1000
            record = PredictionRecord(
                timestamp=datetime.utcnow(),
                text_length=text_length,
                confidence=confidence,
                prediction=prediction,
                latency_ms=latency_ms,
                backend=backend,
                cached=cached,
                cost_estimate=cost
            )

            # Store in history
            if self.enable_detailed_tracking:
                self.prediction_history.append(record)

            # Update counters
            self.predictions_by_label[prediction] += 1

            # Confidence bucket
            confidence_bucket = self._get_confidence_bucket(confidence)
            self.predictions_by_confidence_bucket[confidence_bucket] += 1

            # Backend counter
            self.predictions_by_backend[backend] += 1

            # Track low/high confidence
            if confidence < 0.6:
                self.low_confidence_predictions.append(record)
                self.quality_low_confidence_total.labels(label=prediction).inc()
            elif confidence >= 0.9:
                self.high_confidence_predictions.append(record)

            # Track latency by backend
            self.latency_by_backend[backend].append(latency_ms)
            if len(self.latency_by_backend[backend]) > 1000:
                self.latency_by_backend[backend] = self.latency_by_backend[backend][-1000:]

            # Update cost
            self.total_cost += cost
            day_key = datetime.utcnow().strftime("%Y-%m-%d")
            self.cost_by_day[day_key] += cost

            # Update Prometheus metrics
            self.business_predictions_total.labels(
                label=prediction,
                confidence_bucket=confidence_bucket
            ).inc()

            self.business_confidence_distribution.observe(confidence)

            self.performance_latency_detailed.labels(
                backend=backend,
                cached=str(cached)
            ).observe(latency_ms)

            self.cost_total_usd.inc(cost)

    def _get_confidence_bucket(self, confidence: float) -> str:
        """Categorize confidence into buckets."""
        if confidence >= 0.95:
            return "very_high"
        elif confidence >= 0.80:
            return "high"
        elif confidence >= 0.60:
            return "medium"
        elif confidence >= 0.50:
            return "low"
        else:
            return "very_low"

    def get_business_kpis(self) -> Dict[str, Any]:
        """
        Get business-focused KPIs.

        Returns:
            Dictionary of business KPIs
        """
        with self._lock:
            total_predictions = sum(self.predictions_by_label.values())

            if total_predictions == 0:
                return {"total_predictions": 0}

            # Calculate metrics
            positive_ratio = self.predictions_by_label.get("POSITIVE", 0) / total_predictions
            negative_ratio = self.predictions_by_label.get("NEGATIVE", 0) / total_predictions

            # Confidence statistics
            confidences = [r.confidence for r in self.prediction_history]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # High quality predictions (confidence > 0.8)
            high_quality_count = len([c for c in confidences if c >= 0.8])
            high_quality_ratio = high_quality_count / len(confidences) if confidences else 0.0

            return {
                "total_predictions": total_predictions,
                "positive_ratio": round(positive_ratio, 4),
                "negative_ratio": round(negative_ratio, 4),
                "avg_confidence": round(avg_confidence, 4),
                "high_quality_ratio": round(high_quality_ratio, 4),
                "predictions_by_label": dict(self.predictions_by_label),
                "predictions_by_confidence": dict(self.predictions_by_confidence_bucket)
            }

    def get_quality_metrics(self) -> Dict[str, Any]:
        """
        Get model quality metrics.

        Returns:
            Dictionary of quality metrics
        """
        with self._lock:
            total = len(self.prediction_history)

            if total == 0:
                return {"total_predictions": 0}

            # Low confidence rate
            low_conf_rate = len(self.low_confidence_predictions) / total if total else 0.0

            # Confidence distribution
            confidences = [r.confidence for r in self.prediction_history]
            confidence_std = self._calculate_std(confidences) if len(confidences) > 1 else 0.0

            # Calculate percentiles
            p50_confidence = self._calculate_percentile(confidences, 50)
            p95_confidence = self._calculate_percentile(confidences, 95)
            p99_confidence = self._calculate_percentile(confidences, 99)

            # Update Prometheus gauge
            self.quality_rejection_rate.set(low_conf_rate * 100)

            return {
                "total_predictions": total,
                "low_confidence_rate": round(low_conf_rate, 4),
                "low_confidence_count": len(self.low_confidence_predictions),
                "confidence_std": round(confidence_std, 4),
                "confidence_p50": round(p50_confidence, 4),
                "confidence_p95": round(p95_confidence, 4),
                "confidence_p99": round(p99_confidence, 4)
            }

    def get_cost_metrics(self) -> Dict[str, Any]:
        """
        Get cost and efficiency metrics.

        Returns:
            Dictionary of cost metrics
        """
        with self._lock:
            total_predictions = sum(self.predictions_by_label.values())

            # Cost per prediction
            cost_per_pred = self.total_cost / total_predictions if total_predictions else 0.0

            # Estimated monthly cost (based on last 24h)
            recent_cost = sum(
                r.cost_estimate for r in self.prediction_history
                if r.timestamp > datetime.utcnow() - timedelta(hours=24)
            )
            monthly_estimate = recent_cost * 30

            # Cache efficiency (cost savings)
            cached_count = len([r for r in self.prediction_history if r.cached])
            cache_savings_pct = (cached_count / total_predictions * 100) if total_predictions else 0.0

            # Update Prometheus gauges
            self.cost_per_prediction_usd.set(cost_per_pred)
            self.cost_monthly_burn_rate_usd.set(monthly_estimate)

            return {
                "total_cost_usd": round(self.total_cost, 6),
                "cost_per_prediction_usd": round(cost_per_pred, 6),
                "monthly_estimate_usd": round(monthly_estimate, 2),
                "total_predictions": total_predictions,
                "cached_predictions": cached_count,
                "cache_savings_percent": round(cache_savings_pct, 2),
                "cost_by_day": {k: round(v, 6) for k, v in self.cost_by_day.items()}
            }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get detailed performance metrics.

        Returns:
            Dictionary of performance metrics
        """
        with self._lock:
            if not self.prediction_history:
                return {"total_predictions": 0}

            # Overall latency statistics
            latencies = [r.latency_ms for r in self.prediction_history]

            p50 = self._calculate_percentile(latencies, 50)
            p95 = self._calculate_percentile(latencies, 95)
            p99 = self._calculate_percentile(latencies, 99)
            avg = sum(latencies) / len(latencies)

            # Latency by backend
            latency_by_backend = {}
            for backend, latency_list in self.latency_by_backend.items():
                if latency_list:
                    latency_by_backend[backend] = {
                        "avg": round(sum(latency_list) / len(latency_list), 2),
                        "p95": round(self._calculate_percentile(latency_list, 95), 2),
                        "count": len(latency_list)
                    }

            # Throughput (requests per second over last minute)
            recent_predictions = [
                r for r in self.prediction_history
                if r.timestamp > datetime.utcnow() - timedelta(seconds=60)
            ]
            throughput = len(recent_predictions) / 60.0

            # Update Prometheus gauges
            self.slo_latency_p95_ms.set(p95)
            self.slo_latency_p99_ms.set(p99)
            self.performance_throughput.set(throughput)

            return {
                "total_predictions": len(latencies),
                "latency_avg_ms": round(avg, 2),
                "latency_p50_ms": round(p50, 2),
                "latency_p95_ms": round(p95, 2),
                "latency_p99_ms": round(p99, 2),
                "latency_by_backend": latency_by_backend,
                "throughput_rps": round(throughput, 2)
            }

    def get_slo_compliance(
        self,
        availability_target: float = 99.9,
        latency_p95_target_ms: float = 100,
        latency_p99_target_ms: float = 250
    ) -> Dict[str, Any]:
        """
        Check SLO compliance.

        Args:
            availability_target: Target availability percentage
            latency_p95_target_ms: Target P95 latency in ms
            latency_p99_target_ms: Target P99 latency in ms

        Returns:
            Dictionary with SLO compliance status
        """
        with self._lock:
            if not self.prediction_history:
                return {"compliant": False, "reason": "No data"}

            # Calculate availability (assume all successful for now)
            availability = 100.0  # In real scenario, track failures

            # Calculate latencies
            latencies = [r.latency_ms for r in self.prediction_history]
            p95 = self._calculate_percentile(latencies, 95)
            p99 = self._calculate_percentile(latencies, 99)

            # Check compliance
            availability_ok = availability >= availability_target
            p95_ok = p95 <= latency_p95_target_ms
            p99_ok = p99 <= latency_p99_target_ms

            compliant = availability_ok and p95_ok and p99_ok

            # Update Prometheus gauge
            self.slo_availability.set(availability)

            return {
                "compliant": compliant,
                "availability": {
                    "current": round(availability, 2),
                    "target": availability_target,
                    "ok": availability_ok
                },
                "latency_p95": {
                    "current_ms": round(p95, 2),
                    "target_ms": latency_p95_target_ms,
                    "ok": p95_ok
                },
                "latency_p99": {
                    "current_ms": round(p99, 2),
                    "target_ms": latency_p99_target_ms,
                    "ok": p99_ok
                }
            }

    def _calculate_percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a list."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int((percentile / 100.0) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _calculate_std(self, data: List[float]) -> float:
        """Calculate standard deviation."""
        if len(data) < 2:
            return 0.0
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        return variance ** 0.5


# Global metrics collector instance
_metrics_collector: Optional[AdvancedMetricsCollector] = None


def get_advanced_metrics_collector() -> Optional[AdvancedMetricsCollector]:
    """Get the global advanced metrics collector instance."""
    return _metrics_collector


def initialize_advanced_metrics_collector(
    enable_detailed_tracking: bool = True,
    cost_per_1k_predictions: float = 0.01
) -> AdvancedMetricsCollector:
    """Initialize the global advanced metrics collector instance."""
    global _metrics_collector
    _metrics_collector = AdvancedMetricsCollector(
        enable_detailed_tracking=enable_detailed_tracking,
        cost_per_1k_predictions=cost_per_1k_predictions
    )
    return _metrics_collector
