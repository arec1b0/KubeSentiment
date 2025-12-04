#!/usr/bin/env python3
"""
MLOps Sentiment Analysis - Resource Monitoring Script.

This script monitors system resources (CPU, Memory, Disk I/O, Network I/O) and,
if available, GPU metrics and Kubernetes pod metrics. It captures snapshots
at specified intervals and saves the data for performance analysis and
right-sizing.
"""

import asyncio
import psutil
import time
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import subprocess
import re

# Try importing libraries for GPU monitoring
try:
    import pynvml
    NVIDIA_GPU_AVAILABLE = True
except ImportError:
    NVIDIA_GPU_AVAILABLE = False
    logging.warning("pynvml not available - GPU monitoring will be disabled")

try:
    from kubernetes import client, config
    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    logging.warning("kubernetes library not available - K8s monitoring will be disabled")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ResourceMetrics:
    """Resource metrics at a specific point in time."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_sent_mb: float
    network_io_recv_mb: float
    gpu_utilization: Optional[float] = None
    gpu_memory_used_gb: Optional[float] = None
    gpu_memory_total_gb: Optional[float] = None
    gpu_temperature: Optional[float] = None
    gpu_power_draw: Optional[float] = None

@dataclass
class KubernetesMetrics:
    """Kubernetes pod metrics."""
    timestamp: float
    pod_name: str
    namespace: str
    cpu_usage: float
    memory_usage_gb: float
    cpu_limit: Optional[float] = None
    memory_limit_gb: Optional[float] = None
    restart_count: int = 0
    status: str = "Unknown"

class ResourceMonitor:
    """Class for monitoring system resources."""
    
    def __init__(self):
        """Initializes the ResourceMonitor."""
        self.monitoring = False
        self.metrics_history: List[ResourceMetrics] = []
        self.k8s_metrics_history: List[KubernetesMetrics] = []
        self.initial_disk_io = None
        self.initial_network_io = None
        
        # Initialize GPU monitoring
        if NVIDIA_GPU_AVAILABLE:
            try:
                pynvml.nvmlInit()
                self.gpu_count = pynvml.nvmlDeviceGetCount()
                logger.info("Initialized NVIDIA GPU monitoring", extra={"gpu_count": self.gpu_count})
            except Exception as e:
                logger.warning("Failed to initialize GPU monitoring", extra={"error": str(e)})
                self.gpu_count = 0
        else:
            self.gpu_count = 0
        
        # Initialize Kubernetes monitoring
        if KUBERNETES_AVAILABLE:
            try:
                config.load_incluster_config()  # For in-cluster
            except:
                try:
                    config.load_kube_config()  # For local usage
                    self.k8s_client = client.CoreV1Api()
                    self.k8s_metrics_client = client.CustomObjectsApi()
                    logger.info("Initialized Kubernetes monitoring")
                except Exception as e:
                    logger.warning("Failed to initialize Kubernetes monitoring", extra={"error": str(e)})
                    KUBERNETES_AVAILABLE = False
    
    def _get_gpu_metrics(self) -> Dict[str, Any]:
        """Get GPU metrics if available.

        Returns:
            Dictionary containing GPU metrics.
        """
        if not NVIDIA_GPU_AVAILABLE or self.gpu_count == 0:
            return {}
        
        try:
            # Take first GPU (can be expanded for multi-GPU)
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            # GPU Utilization
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            
            # GPU Memory
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            
            # Temperature
            temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            # Power Draw
            try:
                power_draw = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Watts
            except:
                power_draw = None
            
            return {
                'gpu_utilization': utilization.gpu,
                'gpu_memory_used_gb': memory_info.used / (1024**3),
                'gpu_memory_total_gb': memory_info.total / (1024**3),
                'gpu_temperature': temperature,
                'gpu_power_draw': power_draw
            }

        except Exception as e:
            logger.warning("Failed to get GPU metrics", extra={"error": str(e)})
            return {}
    
    def _get_kubernetes_metrics(self, namespace: str = "mlops-benchmark") -> List[KubernetesMetrics]:
        """Get Kubernetes pod metrics.

        Args:
            namespace: The Kubernetes namespace to query.

        Returns:
            List of KubernetesMetrics objects.
        """
        if not KUBERNETES_AVAILABLE:
            return []
        
        try:
            # Get list of pods
            pods = self.k8s_client.list_namespaced_pod(namespace=namespace)
            k8s_metrics = []
            
            for pod in pods.items:
                if pod.metadata.name.startswith('mlops-sentiment'):
                    # Get resource usage metrics
                    try:
                        # Use metrics API to get current usage
                        metrics = self.k8s_metrics_client.get_namespaced_custom_object(
                            group="metrics.k8s.io",
                            version="v1beta1",
                            namespace=namespace,
                            plural="pods",
                            name=pod.metadata.name
                        )
                        
                        # Parse metrics
                        containers = metrics.get('containers', [])
                        if containers:
                            container = containers[0]  # Take first container
                            
                            cpu_usage = self._parse_cpu_usage(container['usage']['cpu'])
                            memory_usage = self._parse_memory_usage(container['usage']['memory'])
                            
                            # Get resource limits
                            cpu_limit = None
                            memory_limit = None
                            
                            if pod.spec.containers:
                                resources = pod.spec.containers[0].resources
                                if resources and resources.limits:
                                    if 'cpu' in resources.limits:
                                        cpu_limit = self._parse_cpu_usage(resources.limits['cpu'])
                                    if 'memory' in resources.limits:
                                        memory_limit = self._parse_memory_usage(resources.limits['memory'])
                            
                            k8s_metric = KubernetesMetrics(
                                timestamp=time.time(),
                                pod_name=pod.metadata.name,
                                namespace=namespace,
                                cpu_usage=cpu_usage,
                                memory_usage_gb=memory_usage,
                                cpu_limit=cpu_limit,
                                memory_limit_gb=memory_limit,
                                restart_count=pod.status.container_statuses[0].restart_count if pod.status.container_statuses else 0,
                                status=pod.status.phase
                            )
                            
                            k8s_metrics.append(k8s_metric)

                    except Exception as e:
                        logger.warning(
                            "Failed to get metrics for pod",
                            extra={"pod_name": pod.metadata.name, "error": str(e)}
                        )

            return k8s_metrics

        except Exception as e:
            logger.warning("Failed to get Kubernetes metrics", extra={"error": str(e)})
            return []
    
    def _parse_cpu_usage(self, cpu_string: str) -> float:
        """Parse CPU usage from Kubernetes string format.

        Args:
            cpu_string: CPU usage string (e.g., "100m").

        Returns:
            CPU usage in cores.
        """
        if cpu_string.endswith('n'):
            return float(cpu_string[:-1]) / 1_000_000_000  # nanocores to cores
        elif cpu_string.endswith('m'):
            return float(cpu_string[:-1]) / 1000  # millicores to cores
        else:
            return float(cpu_string)
    
    def _parse_memory_usage(self, memory_string: str) -> float:
        """Parse Memory usage from Kubernetes string format.

        Args:
            memory_string: Memory usage string (e.g., "512Mi").

        Returns:
            Memory usage in GB.
        """
        if memory_string.endswith('Ki'):
            return float(memory_string[:-2]) / (1024**2)  # KiB to GB
        elif memory_string.endswith('Mi'):
            return float(memory_string[:-2]) / 1024  # MiB to GB
        elif memory_string.endswith('Gi'):
            return float(memory_string[:-2])  # GiB to GB
        else:
            return float(memory_string) / (1024**3)  # bytes to GB
    
    def _get_system_metrics(self) -> ResourceMetrics:
        """Get system metrics (host/node level).

        Returns:
            ResourceMetrics object.
        """
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        if self.initial_disk_io is None:
            self.initial_disk_io = disk_io
            disk_read_mb = 0
            disk_write_mb = 0
        else:
            disk_read_mb = (disk_io.read_bytes - self.initial_disk_io.read_bytes) / (1024**2)
            disk_write_mb = (disk_io.write_bytes - self.initial_disk_io.write_bytes) / (1024**2)
        
        # Network I/O
        network_io = psutil.net_io_counters()
        if self.initial_network_io is None:
            self.initial_network_io = network_io
            network_sent_mb = 0
            network_recv_mb = 0
        else:
            network_sent_mb = (network_io.bytes_sent - self.initial_network_io.bytes_sent) / (1024**2)
            network_recv_mb = (network_io.bytes_recv - self.initial_network_io.bytes_recv) / (1024**2)
        
        # GPU Metrics
        gpu_metrics = self._get_gpu_metrics()
        
        return ResourceMetrics(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            memory_used_gb=memory.used / (1024**3),
            memory_total_gb=memory.total / (1024**3),
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            network_io_sent_mb=network_sent_mb,
            network_io_recv_mb=network_recv_mb,
            **gpu_metrics
        )
    
    async def start_monitoring(self, interval: int = 5, namespace: str = "mlops-benchmark"):
        """Start resource monitoring loop.

        Args:
            interval: Monitoring interval in seconds.
            namespace: Kubernetes namespace to monitor.
        """
        self.monitoring = True
        logger.info("Starting resource monitoring", extra={"interval_seconds": interval})
        
        while self.monitoring:
            try:
                # System metrics
                system_metrics = self._get_system_metrics()
                self.metrics_history.append(system_metrics)
                
                # Kubernetes metrics
                k8s_metrics = self._get_kubernetes_metrics(namespace)
                self.k8s_metrics_history.extend(k8s_metrics)
                
                # Log current metrics
                logger.info(
                    "Resource metrics",
                    extra={
                        "cpu_percent": round(system_metrics.cpu_percent, 1),
                        "memory_percent": round(system_metrics.memory_percent, 1),
                        "memory_used_gb": round(system_metrics.memory_used_gb, 2),
                        "gpu_utilization": system_metrics.gpu_utilization or "N/A"
                    }
                )

                await asyncio.sleep(interval)

            except Exception as e:
                logger.error("Error during monitoring", extra={"error": str(e)}, exc_info=True)
                await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        self.monitoring = False
        logger.info("Stopped resource monitoring")
    
    def get_average_metrics(self) -> Dict[str, float]:
        """Calculate average metrics over the monitoring period.

        Returns:
            Dictionary containing average metric values.
        """
        if not self.metrics_history:
            return {}
        
        metrics = {
            'avg_cpu_percent': sum(m.cpu_percent for m in self.metrics_history) / len(self.metrics_history),
            'avg_memory_percent': sum(m.memory_percent for m in self.metrics_history) / len(self.metrics_history),
            'avg_memory_used_gb': sum(m.memory_used_gb for m in self.metrics_history) / len(self.metrics_history),
            'max_cpu_percent': max(m.cpu_percent for m in self.metrics_history),
            'max_memory_percent': max(m.memory_percent for m in self.metrics_history),
            'max_memory_used_gb': max(m.memory_used_gb for m in self.metrics_history),
        }
        
        # GPU metrics (if available)
        gpu_utilizations = [m.gpu_utilization for m in self.metrics_history if m.gpu_utilization is not None]
        if gpu_utilizations:
            metrics.update({
                'avg_gpu_utilization': sum(gpu_utilizations) / len(gpu_utilizations),
                'max_gpu_utilization': max(gpu_utilizations),
            })
        
        gpu_memory_used = [m.gpu_memory_used_gb for m in self.metrics_history if m.gpu_memory_used_gb is not None]
        if gpu_memory_used:
            metrics.update({
                'avg_gpu_memory_used_gb': sum(gpu_memory_used) / len(gpu_memory_used),
                'max_gpu_memory_used_gb': max(gpu_memory_used),
            })
        
        return metrics
    
    def save_metrics(self, output_path: str):
        """Save collected metrics to JSON files.

        Args:
            output_path: Path to the output JSON file.
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Save system metrics
        system_metrics_data = [asdict(m) for m in self.metrics_history]
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(system_metrics_data, f, indent=2, ensure_ascii=False)
        
        # Save Kubernetes metrics
        if self.k8s_metrics_history:
            k8s_output_path = output_path.replace('.json', '_k8s.json')
            k8s_metrics_data = [asdict(m) for m in self.k8s_metrics_history]
            with open(k8s_output_path, 'w', encoding='utf-8') as f:
                json.dump(k8s_metrics_data, f, indent=2, ensure_ascii=False)
        
        # Save averages
        avg_metrics = self.get_average_metrics()
        avg_output_path = output_path.replace('.json', '_summary.json')
        with open(avg_output_path, 'w', encoding='utf-8') as f:
            json.dump(avg_metrics, f, indent=2, ensure_ascii=False)

        logger.info("Metrics saved", extra={"output_path": output_path})

async def main():
    """Main entry point for the resource monitor."""
    parser = argparse.ArgumentParser(description='Resource Monitoring for MLOps Benchmarking')
    parser.add_argument('--interval', type=int, default=5,
                       help='Monitoring interval in seconds')
    parser.add_argument('--duration', type=int, default=300,
                       help='Monitoring duration in seconds')
    parser.add_argument('--namespace', default='mlops-benchmark',
                       help='Kubernetes namespace to monitor')
    parser.add_argument('--output', default='results/resource_metrics.json',
                       help='Output file for metrics')
    
    args = parser.parse_args()
    
    # Create monitor
    monitor = ResourceMonitor()
    
    try:
        # Start monitoring in background
        monitoring_task = asyncio.create_task(
            monitor.start_monitoring(args.interval, args.namespace)
        )
        
        # Wait for duration
        await asyncio.sleep(args.duration)
        
        # Stop monitoring
        monitor.stop_monitoring()
        await monitoring_task
        
        # Save results
        monitor.save_metrics(args.output)
        
        # Print summary
        avg_metrics = monitor.get_average_metrics()
        print(f"\n{'='*50}")
        print("RESOURCE MONITORING SUMMARY")
        print(f"{'='*50}")
        print(f"Duration: {args.duration}s")
        print(f"Samples collected: {len(monitor.metrics_history)}")
        print(f"Average CPU: {avg_metrics.get('avg_cpu_percent', 0):.1f}%")
        print(f"Average Memory: {avg_metrics.get('avg_memory_percent', 0):.1f}%")
        print(f"Max CPU: {avg_metrics.get('max_cpu_percent', 0):.1f}%")
        print(f"Max Memory: {avg_metrics.get('max_memory_percent', 0):.1f}%")
        
        if 'avg_gpu_utilization' in avg_metrics:
            print(f"Average GPU: {avg_metrics['avg_gpu_utilization']:.1f}%")
            print(f"Max GPU: {avg_metrics['max_gpu_utilization']:.1f}%")

    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
        monitor.stop_monitoring()
    except Exception as e:
        logger.error("Monitoring failed", extra={"error": str(e)}, exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
