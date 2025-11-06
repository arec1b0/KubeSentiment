"""
GPU Batch Optimizer for efficient batch inference.

This module provides GPU-optimized batch processing with dynamic batching,
multi-GPU support, and intelligent load balancing for maximum throughput.
"""

import os
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import asyncio
from dataclasses import dataclass
from enum import Enum

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LoadBalancingStrategy(str, Enum):
    """GPU load balancing strategies."""
    ROUND_ROBIN = "round-robin"
    LEAST_LOADED = "least-loaded"
    GPU_UTILIZATION = "gpu-utilization-based"


@dataclass
class GPUConfig:
    """GPU configuration for batch processing."""
    enabled: bool
    gpu_count: int
    batch_size: int
    max_batch_size: int
    dynamic_batching: bool
    multi_gpu_enabled: bool
    memory_fraction: float
    load_balancing_strategy: LoadBalancingStrategy


class GPUBatchOptimizer:
    """
    Optimizes batch inference for GPU workloads.

    Features:
    - Dynamic batch sizing based on GPU memory
    - Multi-GPU support with load balancing
    - Automatic batch aggregation for improved throughput
    - GPU memory management
    """

    def __init__(self, settings: Settings):
        """
        Initialize GPU batch optimizer.

        Args:
            settings: Application settings with GPU configuration
        """
        self.settings = settings
        self.logger = get_logger(__name__)

        # Parse GPU configuration from environment
        self.config = self._parse_gpu_config()

        # GPU state tracking
        self.gpu_loads: Dict[int, float] = {}
        self.current_gpu_index = 0

        # Initialize GPU if enabled
        if self.config.enabled:
            self._initialize_gpu()

    def _parse_gpu_config(self) -> GPUConfig:
        """Parse GPU configuration from environment variables."""
        return GPUConfig(
            enabled=os.getenv("ENABLE_GPU_OPTIMIZATION", "false").lower() == "true",
            gpu_count=int(os.getenv("GPU_COUNT", "1")),
            batch_size=int(os.getenv("GPU_BATCH_SIZE", "64")),
            max_batch_size=int(os.getenv("GPU_MAX_BATCH_SIZE", "128")),
            dynamic_batching=os.getenv("GPU_DYNAMIC_BATCHING", "true").lower() == "true",
            multi_gpu_enabled=os.getenv("MULTI_GPU_ENABLED", "false").lower() == "true",
            memory_fraction=float(os.getenv("GPU_MEMORY_FRACTION", "0.9")),
            load_balancing_strategy=LoadBalancingStrategy(
                os.getenv("GPU_LOAD_BALANCING_STRATEGY", "gpu-utilization-based")
            ),
        )

    def _initialize_gpu(self):
        """Initialize GPU resources and set memory limits."""
        try:
            import torch

            if not torch.cuda.is_available():
                self.logger.warning("GPU optimization enabled but CUDA not available")
                self.config.enabled = False
                return

            # Log GPU information
            gpu_count = torch.cuda.device_count()
            self.logger.info(f"Detected {gpu_count} GPU(s)")

            for i in range(gpu_count):
                gpu_name = torch.cuda.get_device_name(i)
                gpu_memory = torch.cuda.get_device_properties(i).total_memory / 1e9
                self.logger.info(f"GPU {i}: {gpu_name}, Memory: {gpu_memory:.2f} GB")
                self.gpu_loads[i] = 0.0

            # Set memory fraction to avoid OOM
            if self.config.memory_fraction < 1.0:
                torch.cuda.set_per_process_memory_fraction(
                    self.config.memory_fraction,
                    device=None  # Apply to all devices
                )
                self.logger.info(
                    f"Set GPU memory fraction to {self.config.memory_fraction}"
                )

            # Enable TF32 for Ampere+ GPUs (faster computation)
            if hasattr(torch.backends.cuda, 'matmul'):
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                self.logger.info("Enabled TF32 for faster computation")

        except ImportError:
            self.logger.warning("PyTorch not available, GPU optimization disabled")
            self.config.enabled = False
        except Exception as e:
            self.logger.error(f"Failed to initialize GPU: {e}")
            self.config.enabled = False

    def get_optimal_batch_size(
        self,
        num_samples: int,
        input_size: Optional[int] = None
    ) -> int:
        """
        Calculate optimal batch size based on GPU memory and input size.

        Args:
            num_samples: Number of samples to process
            input_size: Optional input size hint for dynamic sizing

        Returns:
            Optimal batch size for current GPU state
        """
        if not self.config.enabled or not self.config.dynamic_batching:
            return min(self.config.batch_size, num_samples)

        try:
            import torch

            # Get available GPU memory
            if torch.cuda.is_available():
                gpu_id = self._select_gpu()
                free_memory = torch.cuda.mem_get_info(gpu_id)[0]
                total_memory = torch.cuda.mem_get_info(gpu_id)[1]
                memory_usage = 1.0 - (free_memory / total_memory)

                # Adjust batch size based on memory usage
                if memory_usage > 0.85:
                    # High memory usage, reduce batch size
                    batch_size = max(self.config.batch_size // 2, 8)
                elif memory_usage < 0.5:
                    # Low memory usage, can increase batch size
                    batch_size = min(
                        self.config.max_batch_size,
                        int(self.config.batch_size * 1.5)
                    )
                else:
                    batch_size = self.config.batch_size

                return min(batch_size, num_samples)

        except Exception as e:
            self.logger.warning(f"Failed to calculate optimal batch size: {e}")

        return min(self.config.batch_size, num_samples)

    def _select_gpu(self) -> int:
        """
        Select GPU based on load balancing strategy.

        Returns:
            GPU device ID to use
        """
        if not self.config.multi_gpu_enabled or self.config.gpu_count == 1:
            return 0

        if self.config.load_balancing_strategy == LoadBalancingStrategy.ROUND_ROBIN:
            gpu_id = self.current_gpu_index
            self.current_gpu_index = (self.current_gpu_index + 1) % self.config.gpu_count
            return gpu_id

        elif self.config.load_balancing_strategy == LoadBalancingStrategy.LEAST_LOADED:
            # Select GPU with lowest tracked load
            return min(self.gpu_loads.items(), key=lambda x: x[1])[0]

        elif self.config.load_balancing_strategy == LoadBalancingStrategy.GPU_UTILIZATION:
            try:
                import torch

                # Select GPU with most free memory
                gpu_memories = []
                for i in range(self.config.gpu_count):
                    if torch.cuda.is_available():
                        free_mem = torch.cuda.mem_get_info(i)[0]
                        gpu_memories.append((i, free_mem))

                if gpu_memories:
                    return max(gpu_memories, key=lambda x: x[1])[0]

            except Exception as e:
                self.logger.warning(
                    f"Failed to get GPU utilization, falling back to round-robin: {e}"
                )

        # Fallback to round-robin
        gpu_id = self.current_gpu_index
        self.current_gpu_index = (self.current_gpu_index + 1) % self.config.gpu_count
        return gpu_id

    def distribute_batches(
        self,
        texts: List[str]
    ) -> List[tuple[int, List[str]]]:
        """
        Distribute batches across GPUs for multi-GPU inference.

        Args:
            texts: List of texts to process

        Returns:
            List of (gpu_id, batch_texts) tuples
        """
        if not self.config.multi_gpu_enabled or self.config.gpu_count == 1:
            # Single GPU, create batches
            batch_size = self.get_optimal_batch_size(len(texts))
            batches = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batches.append((0, batch))
            return batches

        # Multi-GPU distribution
        gpu_batches: List[tuple[int, List[str]]] = []
        batch_size = self.get_optimal_batch_size(len(texts))

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            gpu_id = self._select_gpu()
            gpu_batches.append((gpu_id, batch))

            # Update load tracking
            self.gpu_loads[gpu_id] = self.gpu_loads.get(gpu_id, 0.0) + len(batch)

        return gpu_batches

    async def process_batch_parallel(
        self,
        predict_fn,
        texts: List[str],
        max_workers: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Process batches in parallel across GPUs.

        Args:
            predict_fn: Prediction function to call for each batch
            texts: List of texts to process
            max_workers: Maximum number of parallel workers

        Returns:
            List of prediction results
        """
        if not self.config.enabled or not self.config.multi_gpu_enabled:
            # Single GPU or CPU, process normally
            return predict_fn(texts)

        # Distribute batches across GPUs
        gpu_batches = self.distribute_batches(texts)

        # Process batches in parallel
        max_workers = max_workers or min(self.config.gpu_count, len(gpu_batches))

        async def process_batch(gpu_id: int, batch_texts: List[str]):
            """Process a single batch on specified GPU."""
            try:
                import torch

                # Set GPU device
                with torch.cuda.device(gpu_id):
                    results = predict_fn(batch_texts)

                # Update load tracking
                self.gpu_loads[gpu_id] = max(
                    0.0,
                    self.gpu_loads.get(gpu_id, 0.0) - len(batch_texts)
                )

                return results

            except Exception as e:
                self.logger.error(f"Error processing batch on GPU {gpu_id}: {e}")
                # Fallback to CPU
                return predict_fn(batch_texts)

        # Execute batches in parallel
        tasks = [
            process_batch(gpu_id, batch_texts)
            for gpu_id, batch_texts in gpu_batches
        ]

        batch_results = await asyncio.gather(*tasks)

        # Flatten results
        all_results = []
        for results in batch_results:
            all_results.extend(results)

        return all_results

    def get_gpu_stats(self) -> Dict[str, Any]:
        """
        Get current GPU statistics.

        Returns:
            Dictionary with GPU stats
        """
        if not self.config.enabled:
            return {"enabled": False}

        try:
            import torch

            stats = {
                "enabled": True,
                "gpu_count": self.config.gpu_count,
                "multi_gpu_enabled": self.config.multi_gpu_enabled,
                "batch_size": self.config.batch_size,
                "gpus": []
            }

            for i in range(self.config.gpu_count):
                if torch.cuda.is_available():
                    gpu_info = {
                        "id": i,
                        "name": torch.cuda.get_device_name(i),
                        "memory_allocated_mb": torch.cuda.memory_allocated(i) / 1e6,
                        "memory_reserved_mb": torch.cuda.memory_reserved(i) / 1e6,
                        "load": self.gpu_loads.get(i, 0.0)
                    }

                    free_mem, total_mem = torch.cuda.mem_get_info(i)
                    gpu_info["memory_free_mb"] = free_mem / 1e6
                    gpu_info["memory_total_mb"] = total_mem / 1e6
                    gpu_info["memory_utilization_pct"] = (
                        (total_mem - free_mem) / total_mem * 100
                    )

                    stats["gpus"].append(gpu_info)

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get GPU stats: {e}")
            return {"enabled": True, "error": str(e)}

    def cleanup(self):
        """Cleanup GPU resources."""
        if not self.config.enabled:
            return

        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                self.logger.info("GPU cache cleared")

        except Exception as e:
            self.logger.error(f"Failed to cleanup GPU: {e}")
