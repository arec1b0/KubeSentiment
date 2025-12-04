"""
KubeSentiment Python SDK

Official Python client library for KubeSentiment API.

Example usage:
    >>> from kubesentiment_sdk import KubeSentimentClient
    >>> client = KubeSentimentClient(base_url="http://localhost:8000", api_key="your-key")
    >>> result = client.predict("This is amazing!")
    >>> print(result.label, result.confidence)
    POSITIVE 0.9876
"""

import requests
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import time


__version__ = "1.0.0"


class PredictionLabel(str, Enum):
    """Sentiment prediction labels."""
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class Priority(str, Enum):
    """Batch job priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class JobStatus(str, Enum):
    """Batch job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PredictionResult:
    """Single prediction result."""
    label: str
    confidence: float
    inference_time_ms: float
    model_name: str
    backend: str
    cached: bool
    text_length: Optional[int] = None
    explanation: Optional[Dict[str, Any]] = None

    @property
    def is_positive(self) -> bool:
        """Check if prediction is positive."""
        return self.label == PredictionLabel.POSITIVE.value

    @property
    def is_negative(self) -> bool:
        """Check if prediction is negative."""
        return self.label == PredictionLabel.NEGATIVE.value

    @property
    def is_confident(self, threshold: float = 0.8) -> bool:
        """Check if prediction confidence exceeds threshold."""
        return self.confidence >= threshold


@dataclass
class BatchJob:
    """Batch prediction job."""
    job_id: str
    status: str
    created_at: str
    priority: str
    total_texts: int
    processed: Optional[int] = None
    results: Optional[List[PredictionResult]] = None
    error: Optional[str] = None


class KubeSentimentError(Exception):
    """Base exception for KubeSentiment SDK."""
    pass


class APIError(KubeSentimentError):
    """API request failed."""
    def __init__(self, status_code: int, message: str):
        """Initialize the APIError.

        Args:
            status_code: The HTTP status code returned by the API.
            message: The error message returned by the API.
        """
        self.status_code = status_code
        self.message = message
        super().__init__(f"API Error {status_code}: {message}")


class KubeSentimentClient:
    """
    Official Python client for KubeSentiment API.

    Args:
        base_url: Base URL of the KubeSentiment API (e.g., "http://localhost:8000")
        api_key: Optional API key for authentication
        timeout: Request timeout in seconds (default: 30)

    Example:
        >>> client = KubeSentimentClient(base_url="http://localhost:8000")
        >>> result = client.predict("I love this product!")
        >>> print(f"{result.label}: {result.confidence:.2%}")
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = True
    ):
        """Initializes the KubeSentiment client.

        Args:
            base_url: Base URL of the KubeSentiment API (e.g., "http://localhost:8000").
            api_key: Optional API key for authentication.
            timeout: Request timeout in seconds (default: 30).
            verify_ssl: Whether to verify SSL certificates (default: True).
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # Setup session
        self.session = requests.Session()
        if api_key:
            self.session.headers['X-API-Key'] = api_key
        self.session.headers['User-Agent'] = f'kubesentiment-sdk/{__version__}'

    def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to API.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint path.
            json: JSON body for the request.
            params: Query parameters.

        Returns:
            The parsed JSON response.

        Raises:
            APIError: If the API returns an error status code.
            KubeSentimentError: If the request fails due to network issues.
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json,
                params=params,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            try:
                error_detail = e.response.json().get('detail', str(e))
            except:
                error_detail = str(e)
            raise APIError(e.response.status_code, error_detail)
        except requests.exceptions.RequestException as e:
            raise KubeSentimentError(f"Request failed: {e}")

    def predict(
        self,
        text: str,
        explain: bool = False,
        timeout: Optional[int] = None
    ) -> PredictionResult:
        """
        Predict sentiment for a single text.

        Args:
            text: Input text to analyze
            explain: Whether to include model explanation
            timeout: Request timeout (overrides default)

        Returns:
            PredictionResult object

        Example:
            >>> result = client.predict("This is great!")
            >>> print(result.label, result.confidence)
        """
        # Use original timeout if not overridden
        original_timeout = self.timeout
        if timeout:
            self.timeout = timeout

        try:
            response = self._request(
                'POST',
                '/api/v1/predict',
                json={'text': text, 'explain': explain}
            )

            return PredictionResult(
                label=response['label'],
                confidence=response['score'],
                inference_time_ms=response.get('inference_time_ms', 0),
                model_name=response.get('model_name', 'unknown'),
                backend=response.get('backend', 'unknown'),
                cached=response.get('cached', False),
                text_length=response.get('text_length'),
                explanation=response.get('explanation')
            )
        finally:
            self.timeout = original_timeout

    def batch_predict(
        self,
        texts: List[str],
        priority: Priority = Priority.MEDIUM,
        wait: bool = False,
        poll_interval: int = 2
    ) -> BatchJob:
        """
        Submit batch prediction job.

        Args:
            texts: List of texts to analyze
            priority: Job priority (high, medium, low)
            wait: Whether to wait for job completion
            poll_interval: Polling interval in seconds (if wait=True)

        Returns:
            BatchJob object

        Example:
            >>> texts = ["Great product!", "Terrible service"]
            >>> job = client.batch_predict(texts, wait=True)
            >>> for result in job.results:
            ...     print(result.label)
        """
        response = self._request(
            'POST',
            '/api/v1/batch/predict',
            json={'texts': texts, 'priority': priority.value}
        )

        job = BatchJob(
            job_id=response['job_id'],
            status=response['status'],
            created_at=response['created_at'],
            priority=response['priority'],
            total_texts=response['total_texts']
        )

        if wait:
            return self.wait_for_job(job.job_id, poll_interval=poll_interval)

        return job

    def get_batch_status(self, job_id: str) -> BatchJob:
        """
        Get status of batch job.

        Args:
            job_id: Batch job ID

        Returns:
            BatchJob object
        """
        response = self._request('GET', f'/api/v1/batch/status/{job_id}')

        return BatchJob(
            job_id=response['job_id'],
            status=response['status'],
            created_at=response['created_at'],
            priority=response['priority'],
            total_texts=response['total_texts'],
            processed=response.get('processed')
        )

    def get_batch_results(self, job_id: str) -> BatchJob:
        """
        Get results of completed batch job.

        Args:
            job_id: Batch job ID

        Returns:
            BatchJob object with results
        """
        response = self._request('GET', f'/api/v1/batch/results/{job_id}')

        results = []
        if 'results' in response:
            for r in response['results']:
                results.append(PredictionResult(
                    label=r['label'],
                    confidence=r['score'],
                    inference_time_ms=r.get('inference_time_ms', 0),
                    model_name=r.get('model_name', 'unknown'),
                    backend=r.get('backend', 'unknown'),
                    cached=r.get('cached', False)
                ))

        return BatchJob(
            job_id=response['job_id'],
            status=response['status'],
            created_at=response['created_at'],
            priority=response['priority'],
            total_texts=response['total_texts'],
            results=results
        )

    def wait_for_job(
        self,
        job_id: str,
        poll_interval: int = 2,
        max_wait: int = 300
    ) -> BatchJob:
        """
        Wait for batch job to complete.

        Args:
            job_id: Batch job ID
            poll_interval: Polling interval in seconds
            max_wait: Maximum wait time in seconds

        Returns:
            Completed BatchJob object

        Raises:
            TimeoutError: If job doesn't complete within max_wait
        """
        start_time = time.time()

        while True:
            job = self.get_batch_status(job_id)

            if job.status == JobStatus.COMPLETED.value:
                return self.get_batch_results(job_id)
            elif job.status == JobStatus.FAILED.value:
                raise KubeSentimentError(f"Batch job failed: {job.error}")

            if time.time() - start_time > max_wait:
                raise TimeoutError(f"Job did not complete within {max_wait} seconds")

            time.sleep(poll_interval)

    def cancel_batch_job(self, job_id: str) -> bool:
        """
        Cancel a batch job.

        Args:
            job_id: Batch job ID

        Returns:
            True if cancelled successfully
        """
        try:
            self._request('DELETE', f'/api/v1/batch/{job_id}')
            return True
        except APIError:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model information
        """
        return self._request('GET', '/api/v1/model-info')

    def health_check(self) -> Dict[str, Any]:
        """
        Check service health.

        Returns:
            Health status dictionary
        """
        return self._request('GET', '/api/v1/health')

    def get_metrics(self) -> str:
        """
        Get Prometheus metrics.

        Returns:
            Metrics in Prometheus format
        """
        url = f"{self.base_url}/api/v1/metrics"
        response = self.session.get(url, timeout=self.timeout, verify=self.verify_ssl)
        response.raise_for_status()
        return response.text

    def get_drift_summary(self) -> Dict[str, Any]:
        """
        Get drift detection summary.

        Returns:
            Drift detection statistics
        """
        return self._request('GET', '/api/v1/monitoring/drift')

    def get_business_kpis(self) -> Dict[str, Any]:
        """
        Get business KPIs.

        Returns:
            Business metrics dictionary
        """
        return self._request('GET', '/api/v1/monitoring/kpis/business')

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Convenience function
def predict(text: str, base_url: str = "http://localhost:8000", api_key: Optional[str] = None) -> PredictionResult:
    """
    Quick prediction function.

    Example:
        >>> from kubesentiment_sdk import predict
        >>> result = predict("I love this!")
        >>> print(result.label)
    """
    with KubeSentimentClient(base_url=base_url, api_key=api_key) as client:
        return client.predict(text)
