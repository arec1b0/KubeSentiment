#!/usr/bin/env python3
"""Calculates the cost-effectiveness of different instance types for predictions.

This script analyzes the results of a benchmark run, combines them with cost
data for various instance types, and calculates metrics such as the cost per
1000 predictions. It then generates a JSON report and visualizations to help
in selecting the most cost-effective instance for deployment.
"""

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class InstanceCost:
    """Represents the cost and specifications of a cloud instance.

    Attributes:
        name: The name of the instance.
        type: The type or size of the instance (e.g., 't2.medium').
        cost_per_hour: The cost of running the instance for one hour, in USD.
        vcpu: The number of virtual CPUs.
        memory_gb: The amount of memory in GiB.
        gpu: The type of GPU, if any.
        gpu_memory_gb: The amount of GPU memory in GiB, if any.
    """

    name: str
    type: str
    cost_per_hour: float
    vcpu: int
    memory_gb: float
    gpu: Optional[str] = None
    gpu_memory_gb: Optional[float] = None


@dataclass
class BenchmarkCostAnalysis:
    """Contains the cost analysis for a single benchmark run.

    Attributes:
        instance_name: The name of the instance used for the benchmark.
        instance_type: The type of the instance.
        cost_per_hour: The hourly cost of the instance.
        requests_per_second: The average requests per second achieved.
        avg_latency_ms: The average latency in milliseconds.
        predictions_per_hour: The projected number of predictions per hour.
        cost_per_1000_predictions: The calculated cost per 1000 predictions.
        cost_efficiency_score: A score representing the cost efficiency.
        latency_efficiency_score: A score representing the latency efficiency.
        total_efficiency_score: An overall efficiency score.
    """

    instance_name: str
    instance_type: str
    cost_per_hour: float
    requests_per_second: float
    avg_latency_ms: float
    predictions_per_hour: float
    cost_per_1000_predictions: float
    cost_efficiency_score: float  # RPS / cost_per_hour
    latency_efficiency_score: float  # 1000 / avg_latency_ms
    total_efficiency_score: float


@dataclass
class CostComparisonReport:
    """Represents the final report comparing the costs of different instances.

    Attributes:
        timestamp: The time when the report was generated.
        total_predictions: The number of predictions used as a basis for cost
            calculation.
        analyses: A list of `BenchmarkCostAnalysis` objects.
        best_cost_efficiency: The name of the instance with the best cost
            efficiency.
        best_latency_efficiency: The name of the instance with the best
            latency.
        best_overall_efficiency: The name of the instance with the best
            overall efficiency.
        recommendations: A list of human-readable recommendations.
    """

    timestamp: str
    total_predictions: int
    analyses: List[BenchmarkCostAnalysis]
    best_cost_efficiency: str
    best_latency_efficiency: str
    best_overall_efficiency: str
    recommendations: List[str]


class CostCalculator:
    """Performs cost calculations based on benchmark results.

    This class loads instance cost data and benchmark results to perform a
    detailed cost analysis.

    Attributes:
        config: The configuration loaded from the YAML file.
        instance_costs: A dictionary of `InstanceCost` objects.
    """

    def __init__(self, config_path: str):
        """Initializes the `CostCalculator`.

        Args:
            config_path: The path to the benchmark configuration YAML file.
        """
        self.config = self._load_config(config_path)
        self.instance_costs = self._parse_instance_costs()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Loads the YAML configuration file.

        Args:
            config_path: The path to the configuration file.

        Returns:
            A dictionary containing the configuration.
        """
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _parse_instance_costs(self) -> Dict[str, InstanceCost]:
        """Parses the instance cost data from the configuration.

        Returns:
            A dictionary mapping instance names to `InstanceCost` objects.
        """
        instance_costs = {}

        # CPU instances
        for instance in self.config["instances"]["cpu"]:
            cost = InstanceCost(
                name=instance["name"],
                type=instance["type"],
                cost_per_hour=instance["cost_per_hour"],
                vcpu=instance["vcpu"],
                memory_gb=float(instance["memory"].replace("Gi", "")),
            )
            instance_costs[instance["name"]] = cost

        # GPU instances
        for instance in self.config["instances"]["gpu"]:
            cost = InstanceCost(
                name=instance["name"],
                type=instance["type"],
                cost_per_hour=instance["cost_per_hour"],
                vcpu=instance["vcpu"],
                memory_gb=float(instance["memory"].replace("Gi", "")),
                gpu=instance["gpu"],
                gpu_memory_gb=float(instance["gpu_memory"].replace("Gi", "")),
            )
            instance_costs[instance["name"]] = cost

        return instance_costs

    def calculate_cost_analysis(self, benchmark_results_path: str) -> List[BenchmarkCostAnalysis]:
        """Calculates cost analysis metrics from benchmark results.

        Args:
            benchmark_results_path: The path to the JSON file containing the
                benchmark results.

        Returns:
            A list of `BenchmarkCostAnalysis` objects.
        """
        analyses = []

        # Load benchmark results
        with open(benchmark_results_path, "r", encoding="utf-8") as f:
            results = json.load(f)

        # If it is a single result, wrap it in a list
        if isinstance(results, dict):
            results = [results]

        for result in results:
            instance_type = result["instance_type"]

            if instance_type not in self.instance_costs:
                logger.warning(
                    "Instance type not found in cost configuration",
                    extra={"instance_type": instance_type}
                )
                continue

            instance_cost = self.instance_costs[instance_type]

            # Calculate metrics
            rps = result["requests_per_second"]
            avg_latency = result["avg_latency"]
            predictions_per_hour = rps * 3600  # RPS * seconds in an hour

            # Cost per 1000 predictions
            if predictions_per_hour > 0:
                cost_per_1000_predictions = (
                    instance_cost.cost_per_hour * 1000
                ) / predictions_per_hour
            else:
                cost_per_1000_predictions = float("inf")

            # Efficiency
            cost_efficiency = (
                rps / instance_cost.cost_per_hour if instance_cost.cost_per_hour > 0 else 0
            )
            latency_efficiency = 1000 / avg_latency if avg_latency > 0 else 0
            total_efficiency = (
                (cost_efficiency * latency_efficiency) / cost_per_1000_predictions
                if cost_per_1000_predictions > 0
                else 0
            )

            analysis = BenchmarkCostAnalysis(
                instance_name=instance_cost.name,
                instance_type=instance_cost.type,
                cost_per_hour=instance_cost.cost_per_hour,
                requests_per_second=rps,
                avg_latency_ms=avg_latency,
                predictions_per_hour=predictions_per_hour,
                cost_per_1000_predictions=cost_per_1000_predictions,
                cost_efficiency_score=cost_efficiency,
                latency_efficiency_score=latency_efficiency,
                total_efficiency_score=total_efficiency,
            )

            analyses.append(analysis)

        return analyses

    def generate_cost_comparison_report(
        self, analyses: List[BenchmarkCostAnalysis], total_predictions: int = 1000
    ) -> CostComparisonReport:
        """Generates a comprehensive report comparing the costs of instances.

        Args:
            analyses: A list of `BenchmarkCostAnalysis` objects.
            total_predictions: The number of predictions to use as a basis for
                the report.

        Returns:
            A `CostComparisonReport` object.

        Raises:
            ValueError: If no analyses are provided.
        """

        if not analyses:
            raise ValueError("No analyses provided")

        # Find the best options
        best_cost = min(analyses, key=lambda x: x.cost_per_1000_predictions)
        best_latency = min(analyses, key=lambda x: x.avg_latency_ms)
        best_overall = max(analyses, key=lambda x: x.total_efficiency_score)

        # Generate recommendations
        recommendations = self._generate_recommendations(analyses)

        report = CostComparisonReport(
            timestamp=datetime.now().isoformat(),
            total_predictions=total_predictions,
            analyses=analyses,
            best_cost_efficiency=best_cost.instance_name,
            best_latency_efficiency=best_latency.instance_name,
            best_overall_efficiency=best_overall.instance_name,
            recommendations=recommendations,
        )

        return report

    def _generate_recommendations(self, analyses: List[BenchmarkCostAnalysis]) -> List[str]:
        """Generates human-readable recommendations based on the analysis.

        Args:
            analyses: A list of `BenchmarkCostAnalysis` objects.

        Returns:
            A list of recommendation strings.
        """
        recommendations = []

        # Sort by cost
        cost_sorted = sorted(analyses, key=lambda x: x.cost_per_1000_predictions)
        latency_sorted = sorted(analyses, key=lambda x: x.avg_latency_ms)
        efficiency_sorted = sorted(analyses, key=lambda x: x.total_efficiency_score, reverse=True)

        # Recommendations for cost
        cheapest = cost_sorted[0]
        most_expensive = cost_sorted[-1]

        cost_diff = most_expensive.cost_per_1000_predictions / cheapest.cost_per_1000_predictions

        recommendations.append(
            f"💰 The most economical option: {cheapest.instance_name} "
            f"(${cheapest.cost_per_1000_predictions:.4f} per 1000 predictions)"
        )

        if cost_diff > 2:
            recommendations.append(
                f"⚠️ The cost difference between the cheapest and most expensive instance is {cost_diff:.1f}x"
            )

        # Recommendations for latency
        fastest = latency_sorted[0]
        slowest = latency_sorted[-1]

        recommendations.append(
            f"⚡ The fastest option: {fastest.instance_name} "
            f"({fastest.avg_latency_ms:.2f}ms average latency)"
        )

        # Recommendations for overall efficiency
        most_efficient = efficiency_sorted[0]
        recommendations.append(f"🎯 Best price/performance balance: {most_efficient.instance_name}")

        # Specific recommendations
        gpu_analyses = [a for a in analyses if "gpu" in a.instance_name.lower()]
        cpu_analyses = [a for a in analyses if "cpu" in a.instance_name.lower()]

        if gpu_analyses and cpu_analyses:
            best_gpu = min(gpu_analyses, key=lambda x: x.cost_per_1000_predictions)
            best_cpu = min(cpu_analyses, key=lambda x: x.cost_per_1000_predictions)

            if best_cpu.cost_per_1000_predictions < best_gpu.cost_per_1000_predictions:
                savings = (
                    (best_gpu.cost_per_1000_predictions - best_cpu.cost_per_1000_predictions)
                    / best_gpu.cost_per_1000_predictions
                ) * 100
                recommendations.append(
                    f"💡 CPU instances are {savings:.1f}% more economical than GPU for this workload"
                )
            else:
                performance_gain = (
                    best_gpu.requests_per_second / best_cpu.requests_per_second - 1
                ) * 100
                recommendations.append(
                    f"🚀 GPU instances provide a {performance_gain:.1f}% performance increase"
                )

        # Recommendations for scaling
        high_rps_instances = [a for a in analyses if a.requests_per_second > 100]
        if high_rps_instances:
            recommendations.append(
                "📈 For high workloads (>100 RPS), it is recommended to use: "
                + ", ".join([a.instance_name for a in high_rps_instances[:3]])
            )

        return recommendations

    def save_cost_report(self, report: CostComparisonReport, output_path: str):
        """Saves the cost comparison report to a JSON file.

        Args:
            report: The `CostComparisonReport` to be saved.
            output_path: The path to the output JSON file.
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)

        logger.info("Cost report saved", extra={"output_path": output_path})

    def generate_cost_visualization(self, analyses: List[BenchmarkCostAnalysis], output_dir: str):
        """Generates and saves visualizations of the cost analysis.

        This method creates several plots to help in comparing the performance
        and cost of different instances, including bar charts and a bubble
        chart.

        Args:
            analyses: A list of `BenchmarkCostAnalysis` objects.
            output_dir: The directory where the plots will be saved.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Prepare data
        df = pd.DataFrame([asdict(a) for a in analyses])

        # Create a figure with multiple plots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))

        # Plot 1: Cost per 1000 predictions
        ax1 = axes[0, 0]
        bars1 = ax1.bar(df["instance_name"], df["cost_per_1000_predictions"])
        ax1.set_title("Cost per 1000 Predictions by Instance Type")
        ax1.set_xlabel("Instance Type")
        ax1.set_ylabel("Cost (USD)")
        ax1.tick_params(axis="x", rotation=45)

        # Add values on the bars
        for bar, value in zip(bars1, df["cost_per_1000_predictions"]):
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.001,
                f"${value:.4f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        # Plot 2: RPS vs Cost per hour
        ax2 = axes[0, 1]
        scatter = ax2.scatter(
            df["cost_per_hour"],
            df["requests_per_second"],
            s=100,
            alpha=0.7,
            c=df["avg_latency_ms"],
            cmap="viridis",
        )
        ax2.set_title("Performance vs. Cost")
        ax2.set_xlabel("Cost per Hour (USD)")
        ax2.set_ylabel("Requests per Second")

        # Add point labels
        for i, row in df.iterrows():
            ax2.annotate(
                row["instance_name"],
                (row["cost_per_hour"], row["requests_per_second"]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8,
            )

        # Color scale for latency
        cbar = plt.colorbar(scatter, ax=ax2)
        cbar.set_label("Average Latency (ms)")

        # Plot 3: Efficiency
        ax3 = axes[1, 0]
        efficiency_bars = ax3.bar(df["instance_name"], df["total_efficiency_score"])
        ax3.set_title("Overall Efficiency (Performance/Cost)")
        ax3.set_xlabel("Instance Type")
        ax3.set_ylabel("Efficiency Score")
        ax3.tick_params(axis="x", rotation=45)

        # Plot 4: Latency comparison
        ax4 = axes[1, 1]
        latency_bars = ax4.bar(df["instance_name"], df["avg_latency_ms"])
        ax4.set_title("Average Latency by Instance Type")
        ax4.set_xlabel("Instance Type")
        ax4.set_ylabel("Latency (ms)")
        ax4.tick_params(axis="x", rotation=45)

        # Add values on the bars
        for bar, value in zip(latency_bars, df["avg_latency_ms"]):
            ax4.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1,
                f"{value:.1f}ms",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        plt.tight_layout()
        plt.savefig(output_dir / "cost_analysis.png", dpi=300, bbox_inches="tight")
        plt.close()

        # Additional plot: Cost vs Performance (bubble chart)
        plt.figure(figsize=(12, 8))

        # Bubble size is proportional to efficiency
        sizes = [max(50, a.total_efficiency_score * 100) for a in analyses]

        scatter = plt.scatter(
            df["cost_per_1000_predictions"],
            df["requests_per_second"],
            s=sizes,
            alpha=0.6,
            c=df["avg_latency_ms"],
            cmap="RdYlBu_r",
        )

        plt.xlabel("Cost per 1000 Predictions (USD)")
        plt.ylabel("Requests per Second")
        plt.title("Cost and Performance Analysis\n(Bubble size = overall efficiency)")

        # Add labels
        for i, row in df.iterrows():
            plt.annotate(
                row["instance_name"],
                (row["cost_per_1000_predictions"], row["requests_per_second"]),
                xytext=(5, 5),
                textcoords="offset points",
            )

        # Color scale
        cbar = plt.colorbar(scatter)
        cbar.set_label("Average Latency (ms)")

        plt.grid(True, alpha=0.3)
        plt.savefig(output_dir / "cost_performance_bubble.png", dpi=300, bbox_inches="tight")
        plt.close()

        logger.info("Cost visualization saved", extra={"output_dir": str(output_dir)})

    def print_cost_summary(self, report: CostComparisonReport):
        """Prints a formatted summary of the cost analysis to the console.

        Args:
            report: The `CostComparisonReport` to be summarized.
        """
        print(f"\n{'='*80}")
        print("BENCHMARK COST ANALYSIS")
        print(f"{'='*80}")
        print(f"Analysis Date: {report.timestamp}")
        print(f"Number of Predictions: {report.total_predictions}")
        print(
            f"\n{'Instance':<15} {'Type':<15} {'$/Hour':<10} {'RPS':<8} {'Latency':<12} {'$/1000 Pred.':<12}"
        )
        print("-" * 80)

        for analysis in sorted(report.analyses, key=lambda x: x.cost_per_1000_predictions):
            print(
                f"{analysis.instance_name:<15} "
                f"{analysis.instance_type:<15} "
                f"${analysis.cost_per_hour:<9.3f} "
                f"{analysis.requests_per_second:<7.1f} "
                f"{analysis.avg_latency_ms:<11.1f}ms "
                f"${analysis.cost_per_1000_predictions:<11.4f}"
            )

        print(f"\n{'='*80}")
        print("RECOMMENDATIONS:")
        print(f"{'='*80}")

        for i, recommendation in enumerate(report.recommendations, 1):
            print(f"{i}. {recommendation}")

        print(f"\n🏆 Best for Cost: {report.best_cost_efficiency}")
        print(f"⚡ Best for Speed: {report.best_latency_efficiency}")
        print(f"🎯 Best Overall Balance: {report.best_overall_efficiency}")


def main():
    """The main entry point for the cost calculation script."""
    parser = argparse.ArgumentParser(description="Cost Calculator for MLOps Benchmarking")
    parser.add_argument(
        "--config",
        default="configs/benchmark-config.yaml",
        help="Path to benchmark configuration file",
    )
    parser.add_argument("--results", required=True, help="Path to benchmark results JSON file(s)")
    parser.add_argument(
        "--predictions", type=int, default=1000, help="Number of predictions for cost calculation"
    )
    parser.add_argument(
        "--output", default="results/cost_analysis.json", help="Output file for cost analysis"
    )
    parser.add_argument(
        "--report-dir", default="results/cost_reports", help="Directory for generated reports"
    )

    args = parser.parse_args()

    # Create the calculator
    calculator = CostCalculator(args.config)

    try:
        # Calculate cost analysis
        analyses = calculator.calculate_cost_analysis(args.results)

        if not analyses:
            logger.error("No valid analyses generated")
            return

        # Generate report
        report = calculator.generate_cost_comparison_report(analyses, args.predictions)

        # Save report
        calculator.save_cost_report(report, args.output)

        # Generate visualization
        calculator.generate_cost_visualization(analyses, args.report_dir)

        # Print summary
        calculator.print_cost_summary(report)

    except Exception as e:
        logger.error("Cost calculation failed", extra={"error": str(e)}, exc_info=True)
        raise


if __name__ == "__main__":
    main()
