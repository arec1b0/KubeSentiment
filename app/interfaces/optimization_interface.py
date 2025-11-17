"""
Interface for GPU Batch Optimizer

Defines the contract for GPU optimization services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Awaitable, Optional


class IGPUBatchOptimizer(ABC):
    """
    Interface for GPU optimization services.

    Provides GPU-aware batch processing and multi-GPU distribution.
    """

    @abstractmethod
    def get_optimal_batch_size(self, num_samples: int, input_size: Optional[int] = None) -> int:
        """
        Calculate optimal batch size based on GPU memory and input size.

        Args:
            num_samples: Number of samples to process
            input_size: Input tensor size per sample

        Returns:
            Optimal batch size for current GPU configuration

        Raises:
            RuntimeError: If GPU is not available or memory check fails
        """
        pass

    @abstractmethod
    def distribute_batches(self, texts: List[str]) -> List[List[str]]:
        """
        Distribute texts across available GPUs.

        Args:
            texts: List of texts to distribute

        Returns:
            List of batches, one per GPU

        Raises:
            RuntimeError: If GPU distribution fails
        """
        pass

    @abstractmethod
    async def process_batch_parallel(
        self,
        predict_fn: Callable[[List[str]], Awaitable[List[Dict[str, Any]]]],
        texts: List[str],
        max_workers: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Process batch in parallel across multiple GPUs.

        Args:
            predict_fn: Async prediction function
            texts: List of texts to process
            max_workers: Maximum parallel workers (None for auto)

        Returns:
            List of prediction results

        Raises:
            RuntimeError: If parallel processing fails
        """
        pass

    @abstractmethod
    def get_gpu_stats(self) -> Dict[str, Any]:
        """
        Get GPU utilization statistics.

        Returns:
            Dictionary containing:
                - gpu_count: Number of available GPUs
                - gpu_memory: Memory stats per GPU
                - gpu_utilization: Utilization percentage per GPU
                - load_per_gpu: Current load distribution
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up GPU resources and clear cache.
        """
        pass
