#!/usr/bin/env python3
"""
Analyze benchmark results to extract CPU and memory usage patterns
for Kubernetes resource right-sizing.

This script processes benchmark result files and generates recommendations
for CPU requests, CPU limits, and memory requests/limits based on:
- Average usage (for requests - allows bin-packing)
- Peak usage (for limits - handles bursts)
- P95/P99 percentiles (for safety margins)
"""

import argparse
import json
import logging
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_cpu(cpu_str: str) -> float:
    """Parse CPU string (e.g., '1000m', '1.5') to cores.

    Args:
        cpu_str: CPU string representation.

    Returns:
        Number of CPU cores as float.
    """
    if cpu_str.endswith("m"):
        return float(cpu_str[:-1]) / 1000
    return float(cpu_str)


def parse_memory(mem_str: str) -> float:
    """Parse memory string (e.g., '1Gi', '512Mi') to GB.

    Args:
        mem_str: Memory string representation.

    Returns:
        Memory size in Gigabytes (GB).
    """
    if mem_str.endswith("Gi"):
        return float(mem_str[:-2])
    elif mem_str.endswith("Mi"):
        return float(mem_str[:-2]) / 1024
    elif mem_str.endswith("Ki"):
        return float(mem_str[:-2]) / (1024**2)
    return float(mem_str) / (1024**3)  # bytes to GB


def format_cpu(cores: float) -> str:
    """Format CPU cores to Kubernetes format (millicores).

    Args:
        cores: Number of CPU cores.

    Returns:
        String representation in millicores (e.g., '500m').
    """
    millicores = int(cores * 1000)
    return f"{millicores}m"


def format_memory(gb: float) -> str:
    """Format memory GB to Kubernetes format.

    Args:
        gb: Memory size in GB.

    Returns:
        String representation (e.g., '1Gi' or '512Mi').
    """
    if gb < 1:
        return f"{int(gb * 1024)}Mi"
    return f"{gb:.1f}Gi"


def analyze_resource_metrics(
    resource_file: Path,
    current_cpu_limit: Optional[str] = None,
    current_memory_limit: Optional[str] = None,
) -> Dict:
    """Analyze resource metrics from benchmark results.

    Args:
        resource_file: Path to resource metrics JSON file
        current_cpu_limit: Current CPU limit (for comparison)
        current_memory_limit: Current memory limit (for comparison)

    Returns:
        Dictionary with analysis results and recommendations
    """
    with open(resource_file, "r") as f:
        data = json.load(f)

    if not data:
        raise ValueError(f"No data found in {resource_file}")

    # Extract metrics
    cpu_percentages = [m.get("cpu_percent", 0) for m in data if "cpu_percent" in m]
    memory_percentages = [m.get("memory_percent", 0) for m in data if "memory_percent" in m]
    memory_used_gb = [m.get("memory_used_gb", 0) for m in data if "memory_used_gb" in m]

    # Get current limits in cores/GB for comparison
    current_cpu_cores = parse_cpu(current_cpu_limit) if current_cpu_limit else None
    current_mem_gb = parse_memory(current_memory_limit) if current_memory_limit else None

    # Calculate statistics
    cpu_avg = statistics.mean(cpu_percentages) if cpu_percentages else 0
    cpu_p95 = (
        statistics.quantiles(cpu_percentages, n=20)[18]
        if len(cpu_percentages) > 20
        else max(cpu_percentages) if cpu_percentages else 0
    )
    cpu_p99 = (
        statistics.quantiles(cpu_percentages, n=100)[98]
        if len(cpu_percentages) > 100
        else max(cpu_percentages) if cpu_percentages else 0
    )
    cpu_max = max(cpu_percentages) if cpu_percentages else 0

    mem_avg = statistics.mean(memory_percentages) if memory_percentages else 0
    mem_p95 = (
        statistics.quantiles(memory_percentages, n=20)[18]
        if len(memory_percentages) > 20
        else max(memory_percentages) if memory_percentages else 0
    )
    mem_p99 = (
        statistics.quantiles(memory_percentages, n=100)[98]
        if len(memory_percentages) > 100
        else max(memory_percentages) if memory_percentages else 0
    )
    mem_max = max(memory_percentages) if memory_percentages else 0

    # Calculate absolute memory usage
    mem_used_avg_gb = statistics.mean(memory_used_gb) if memory_used_gb else 0
    mem_used_p95_gb = (
        statistics.quantiles(memory_used_gb, n=20)[18]
        if len(memory_used_gb) > 20
        else max(memory_used_gb) if memory_used_gb else 0
    )
    mem_used_max_gb = max(memory_used_gb) if memory_used_gb else 0

    # Derive recommendations
    # CPU: requests = average (allows bin-packing), limits = P95 + 20% buffer for bursts
    if current_cpu_cores:
        cpu_request_cores = (
            current_cpu_cores * (cpu_avg / 100) if cpu_avg > 0 else current_cpu_cores * 0.5
        )
        cpu_limit_cores = (
            current_cpu_cores * (cpu_p95 / 100) * 1.2 if cpu_p95 > 0 else current_cpu_cores * 1.2
        )
    else:
        # Fallback: assume 1 core base
        cpu_request_cores = 0.5  # 50% average usage
        cpu_limit_cores = 1.0  # 100% limit

    # Memory: requests = limits = P95 + 10% buffer (avoid OOM kills)
    if current_mem_gb:
        mem_request_gb = (
            current_mem_gb * (mem_p95 / 100) * 1.1 if mem_p95 > 0 else current_mem_gb * 0.8
        )
        mem_limit_gb = mem_request_gb  # Equal to avoid OOM
    else:
        # Fallback: use absolute memory usage
        mem_request_gb = mem_used_p95_gb * 1.1 if mem_used_p95_gb > 0 else 0.5
        mem_limit_gb = mem_request_gb

    # Ensure minimums
    cpu_request_cores = max(cpu_request_cores, 0.1)  # At least 100m
    cpu_limit_cores = max(cpu_limit_cores, cpu_request_cores * 1.1)  # At least 10% above request
    mem_request_gb = max(mem_request_gb, 0.25)  # At least 256Mi
    mem_limit_gb = max(mem_limit_gb, mem_request_gb)

    return {
        "statistics": {
            "cpu": {
                "avg_percent": cpu_avg,
                "p95_percent": cpu_p95,
                "p99_percent": cpu_p99,
                "max_percent": cpu_max,
                "samples": len(cpu_percentages),
            },
            "memory": {
                "avg_percent": mem_avg,
                "p95_percent": mem_p95,
                "p99_percent": mem_p99,
                "max_percent": mem_max,
                "avg_used_gb": mem_used_avg_gb,
                "p95_used_gb": mem_used_p95_gb,
                "max_used_gb": mem_used_max_gb,
                "samples": len(memory_percentages),
            },
        },
        "recommendations": {
            "cpu": {
                "request": format_cpu(cpu_request_cores),
                "limit": format_cpu(cpu_limit_cores),
                "request_cores": cpu_request_cores,
                "limit_cores": cpu_limit_cores,
            },
            "memory": {
                "request": format_memory(mem_request_gb),
                "limit": format_memory(mem_limit_gb),
                "request_gb": mem_request_gb,
                "limit_gb": mem_limit_gb,
            },
        },
        "current": {"cpu_limit": current_cpu_limit, "memory_limit": current_memory_limit},
        "utilization": {
            "cpu_request_utilization": (
                (cpu_request_cores / cpu_limit_cores * 100) if cpu_limit_cores > 0 else 0
            ),
            "memory_request_utilization": (
                (mem_request_gb / mem_limit_gb * 100) if mem_limit_gb > 0 else 0
            ),
        },
    }


def generate_helm_values_recommendation(analysis: Dict, environment: str = "production") -> str:
    """Generate Helm values snippet with recommended resources.

    Args:
        analysis: Analysis result dictionary.
        environment: Target environment name.

    Returns:
        YAML snippet for Helm values.
    """
    rec = analysis["recommendations"]

    return f"""# Resource recommendations for {environment} environment
# Based on benchmark analysis
deployment:
  resources:
    limits:
      cpu: {rec['cpu']['limit']}
      memory: {rec['memory']['limit']}
    requests:
      cpu: {rec['cpu']['request']}
      memory: {rec['memory']['request']}
"""


def main():
    """Main entry point for the analysis script."""
    parser = argparse.ArgumentParser(
        description="Analyze benchmark results for resource right-sizing"
    )
    parser.add_argument(
        "--resource-file", type=Path, required=True, help="Path to resource metrics JSON file"
    )
    parser.add_argument("--current-cpu-limit", type=str, help='Current CPU limit (e.g., "1000m")')
    parser.add_argument(
        "--current-memory-limit", type=str, help='Current memory limit (e.g., "1Gi")'
    )
    parser.add_argument("--output", type=Path, help="Output file for analysis results (JSON)")
    parser.add_argument("--helm-values", action="store_true", help="Generate Helm values snippet")
    parser.add_argument(
        "--environment",
        type=str,
        default="production",
        help="Environment name for Helm values (default: production)",
    )

    args = parser.parse_args()

    if not args.resource_file.exists():
        logger.error(f"Resource file not found: {args.resource_file}")
        return 1

    try:
        analysis = analyze_resource_metrics(
            args.resource_file, args.current_cpu_limit, args.current_memory_limit
        )

        # Print summary
        print("\n" + "=" * 60)
        print("RESOURCE ANALYSIS SUMMARY")
        print("=" * 60)

        stats = analysis["statistics"]
        rec = analysis["recommendations"]

        print(f"\nCPU Statistics:")
        print(f"  Average: {stats['cpu']['avg_percent']:.1f}%")
        print(f"  P95:     {stats['cpu']['p95_percent']:.1f}%")
        print(f"  P99:     {stats['cpu']['p99_percent']:.1f}%")
        print(f"  Max:     {stats['cpu']['max_percent']:.1f}%")
        print(f"  Samples: {stats['cpu']['samples']}")

        print(f"\nCPU Recommendations:")
        print(f"  Request: {rec['cpu']['request']} ({rec['cpu']['request_cores']:.2f} cores)")
        print(f"  Limit:   {rec['cpu']['limit']} ({rec['cpu']['limit_cores']:.2f} cores)")

        print(f"\nMemory Statistics:")
        print(f"  Average: {stats['memory']['avg_percent']:.1f}%")
        print(f"  P95:     {stats['memory']['p95_percent']:.1f}%")
        print(f"  Max:     {stats['memory']['max_percent']:.1f}%")
        print(f"  Avg Used: {stats['memory']['avg_used_gb']:.2f} GB")
        print(f"  P95 Used: {stats['memory']['p95_used_gb']:.2f} GB")
        print(f"  Max Used: {stats['memory']['max_used_gb']:.2f} GB")

        print(f"\nMemory Recommendations:")
        print(f"  Request: {rec['memory']['request']} ({rec['memory']['request_gb']:.2f} GB)")
        print(f"  Limit:   {rec['memory']['limit']} ({rec['memory']['limit_gb']:.2f} GB)")

        if args.current_cpu_limit or args.current_memory_limit:
            print(f"\nCurrent Settings:")
            if args.current_cpu_limit:
                print(f"  CPU Limit: {args.current_cpu_limit}")
            if args.current_memory_limit:
                print(f"  Memory Limit: {args.current_memory_limit}")

        print(f"\nUtilization:")
        print(
            f"  CPU Request Utilization: {analysis['utilization']['cpu_request_utilization']:.1f}%"
        )
        print(
            f"  Memory Request Utilization: {analysis['utilization']['memory_request_utilization']:.1f}%"
        )

        # Generate Helm values if requested
        if args.helm_values:
            print("\n" + "=" * 60)
            print("HELM VALUES RECOMMENDATION")
            print("=" * 60)
            print(generate_helm_values_recommendation(analysis, args.environment))

        # Save to file if specified
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w") as f:
                json.dump(analysis, f, indent=2)
            print(f"\nAnalysis saved to: {args.output}")

        return 0

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main())
