#!/usr/bin/env python3
"""A comprehensive report generator for benchmark results.

This script consolidates data from performance, cost, and resource monitoring
runs to generate a single, interactive HTML report. It uses Plotly for rich,
interactive visualizations and Jinja2 for templating the final HTML output,
providing a holistic view of the model's performance characteristics across
different instance types.
"""

import argparse
import base64
import json
import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import yaml
from jinja2 import Template
from plotly.subplots import make_subplots

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class BenchmarkReportGenerator:
    """Generates a comprehensive HTML report from benchmark data.

    This class loads performance, cost, and resource utilization data,
    creates various comparison charts, and compiles them into a single,
    shareable HTML file.

    Attributes:
        results_dir: The directory containing the benchmark result files.
        benchmark_data: A list of dictionaries with performance metrics.
        cost_data: A list of dictionaries with cost analysis results.
        resource_data: A list of dictionaries with resource usage metrics.
    """

    def __init__(self, results_dir: str):
        """Initializes the `BenchmarkReportGenerator`.

        Args:
            results_dir: The path to the directory containing benchmark
                results.
        """
        self.results_dir = Path(results_dir)
        self.benchmark_data: List[Dict[str, Any]] = []
        self.cost_data: List[Dict[str, Any]] = []
        self.resource_data: List[Dict[str, Any]] = []

    def load_data(self):
        """Loads all benchmark data from the results directory.

        This method reads consolidated performance results, cost analysis
        data, and resource metrics from their respective JSON files.
        """
        logger.info("Loading benchmark data...")

        # Load benchmark results
        consolidated_file = self.results_dir / "consolidated_results.json"
        if consolidated_file.exists():
            with open(consolidated_file, "r", encoding="utf-8") as f:
                self.benchmark_data = json.load(f)

        # Load cost data
        cost_file = self.results_dir / "cost_analysis.json"
        if cost_file.exists():
            with open(cost_file, "r", encoding="utf-8") as f:
                cost_analysis = json.load(f)
                self.cost_data = cost_analysis.get("analyses", [])

        # Load resource data
        for resource_file in self.results_dir.glob("resource_metrics_*.json"):
            with open(resource_file, "r", encoding="utf-8") as f:
                resource_data = json.load(f)
                instance_name = resource_file.stem.replace("resource_metrics_", "")
                self.resource_data.append({"instance": instance_name, "metrics": resource_data})

        logger.info(
            f"Loaded: {len(self.benchmark_data)} benchmarks, "
            f"{len(self.cost_data)} cost analyses, "
            f"{len(self.resource_data)} resource metric sets"
        )

    def create_performance_comparison_chart(self) -> str:
        """Creates an interactive performance comparison chart.

        This method generates a multi-plot figure comparing RPS, latency,
        and efficiency across different instance types.

        Returns:
            An HTML string representing the Plotly chart. Returns an empty
            string if no benchmark data is available.
        """
        if not self.benchmark_data:
            return ""

        df = pd.DataFrame(self.benchmark_data)

        # Create a subplot with multiple charts
        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "RPS by Instance",
                "Latency by Instance",
                "Latency Percentiles",
                "Efficiency",
            ),
            specs=[
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"secondary_y": False}, {"secondary_y": False}],
            ],
        )

        # Chart 1: RPS
        fig.add_trace(
            go.Bar(
                x=df["instance_type"],
                y=df["requests_per_second"],
                name="RPS",
                marker_color="lightblue",
            ),
            row=1,
            col=1,
        )

        # Chart 2: Latency
        fig.add_trace(
            go.Bar(
                x=df["instance_type"],
                y=df["avg_latency"],
                name="Avg Latency (ms)",
                marker_color="lightcoral",
            ),
            row=1,
            col=2,
        )

        # Chart 3: Latency Percentiles
        latency_percentiles = ["p50_latency", "p90_latency", "p95_latency", "p99_latency"]
        for percentile in latency_percentiles:
            if percentile in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["instance_type"],
                        y=df[percentile],
                        mode="lines+markers",
                        name=percentile.replace("_latency", "").upper(),
                        line=dict(width=2),
                    ),
                    row=2,
                    col=1,
                )

        # Chart 4: Efficiency (RPS/cost)
        if self.cost_data:
            cost_df = pd.DataFrame(self.cost_data)
            efficiency = cost_df["requests_per_second"] / cost_df["cost_per_hour"]
            fig.add_trace(
                go.Bar(
                    x=cost_df["instance_name"],
                    y=efficiency,
                    name="RPS/Cost Efficiency",
                    marker_color="lightgreen",
                ),
                row=2,
                col=2,
            )

        fig.update_layout(height=800, title_text="Instance Performance Comparison", showlegend=True)

        # Save as HTML
        html_str = fig.to_html(include_plotlyjs="cdn")
        return html_str

    def create_cost_analysis_chart(self) -> str:
        """Creates an interactive cost analysis bubble chart.

        This chart visualizes the trade-offs between cost, performance (RPS),
        and latency. The size of each bubble represents the overall
        efficiency score.

        Returns:
            An HTML string of the Plotly chart, or an empty string if no
            cost data is available.
        """
        if not self.cost_data:
            return ""

        df = pd.DataFrame(self.cost_data)

        # Create bubble chart
        fig = go.Figure()

        # Bubble size is proportional to total efficiency
        sizes = df["total_efficiency_score"] * 50

        fig.add_trace(
            go.Scatter(
                x=df["cost_per_1000_predictions"],
                y=df["requests_per_second"],
                mode="markers",
                marker=dict(
                    size=sizes,
                    color=df["avg_latency_ms"],
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="Latency (ms)"),
                    line=dict(width=2, color="DarkSlateGrey"),
                ),
                text=df["instance_name"],
                textposition="middle center",
                hovertemplate="<b>%{text}</b><br>"
                + "Cost per 1k Pred: $%{x:.4f}<br>"
                + "RPS: %{y:.1f}<br>"
                + "Latency: %{marker.color:.1f}ms<br>"
                + "<extra></extra>",
            )
        )

        fig.update_layout(
            title="Cost vs. Performance Analysis<br><sub>Bubble size = Total Efficiency</sub>",
            xaxis_title="Cost per 1000 Predictions (USD)",
            yaxis_title="Requests per Second (RPS)",
            width=800,
            height=600,
        )

        return fig.to_html(include_plotlyjs="cdn")

    def create_resource_utilization_chart(self) -> str:
        """Creates an interactive chart for resource utilization.

        This method generates a multi-plot figure showing CPU, memory, and
        GPU utilization over time for each tested instance, along with a
        summary bar chart of average usage.

        Returns:
            An HTML string of the Plotly chart, or an empty string if no
            resource data is available.
        """
        if not self.resource_data:
            return ""

        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "CPU Utilization",
                "Memory Utilization",
                "GPU Utilization",
                "Resource Summary",
            ),
            specs=[
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"secondary_y": False}, {"secondary_y": False}],
            ],
        )

        colors = px.colors.qualitative.Set1

        for i, resource_set in enumerate(self.resource_data):
            instance = resource_set["instance"]
            metrics = resource_set["metrics"]

            if not metrics:
                continue

            # Extract time series
            timestamps = [m.get("timestamp", 0) for m in metrics]
            cpu_usage = [m.get("cpu_percent", 0) for m in metrics]
            memory_usage = [m.get("memory_percent", 0) for m in metrics]
            gpu_usage = [
                m.get("gpu_utilization", 0) for m in metrics if m.get("gpu_utilization") is not None
            ]

            color = colors[i % len(colors)]

            # CPU chart
            fig.add_trace(
                go.Scatter(
                    x=list(range(len(cpu_usage))),
                    y=cpu_usage,
                    mode="lines",
                    name=f"{instance} CPU",
                    line=dict(color=color, width=2),
                ),
                row=1,
                col=1,
            )

            # Memory chart
            fig.add_trace(
                go.Scatter(
                    x=list(range(len(memory_usage))),
                    y=memory_usage,
                    mode="lines",
                    name=f"{instance} Memory",
                    line=dict(color=color, width=2, dash="dash"),
                ),
                row=1,
                col=2,
            )

            # GPU chart (if data exists)
            if gpu_usage:
                fig.add_trace(
                    go.Scatter(
                        x=list(range(len(gpu_usage))),
                        y=gpu_usage,
                        mode="lines",
                        name=f"{instance} GPU",
                        line=dict(color=color, width=2, dash="dot"),
                    ),
                    row=2,
                    col=1,
                )

        # Summary chart of average values
        avg_data = []
        for resource_set in self.resource_data:
            instance = resource_set["instance"]
            metrics = resource_set["metrics"]

            if metrics:
                avg_cpu = np.mean([m.get("cpu_percent", 0) for m in metrics])
                avg_memory = np.mean([m.get("memory_percent", 0) for m in metrics])
                gpu_values = [
                    m.get("gpu_utilization", 0)
                    for m in metrics
                    if m.get("gpu_utilization") is not None
                ]
                avg_gpu = np.mean(gpu_values) if gpu_values else 0

                avg_data.append(
                    {"instance": instance, "cpu": avg_cpu, "memory": avg_memory, "gpu": avg_gpu}
                )

        if avg_data:
            avg_df = pd.DataFrame(avg_data)

            fig.add_trace(
                go.Bar(
                    x=avg_df["instance"],
                    y=avg_df["cpu"],
                    name="Avg CPU %",
                    marker_color="lightblue",
                ),
                row=2,
                col=2,
            )

            fig.add_trace(
                go.Bar(
                    x=avg_df["instance"],
                    y=avg_df["memory"],
                    name="Avg Memory %",
                    marker_color="lightcoral",
                ),
                row=2,
                col=2,
            )

            # GPU only if data exists
            if avg_df["gpu"].sum() > 0:
                fig.add_trace(
                    go.Bar(
                        x=avg_df["instance"],
                        y=avg_df["gpu"],
                        name="Avg GPU %",
                        marker_color="lightgreen",
                    ),
                    row=2,
                    col=2,
                )

        fig.update_layout(
            height=800, title_text="Resource Utilization During Benchmark", showlegend=True
        )

        return fig.to_html(include_plotlyjs="cdn")

    def generate_summary_statistics(self) -> Dict[str, Any]:
        """Generates a dictionary of summary statistics.

        This method calculates key highlights from the benchmark results,
        such as the best performing instance for RPS, the instance with the
        lowest latency, and the most cost-effective option.

        Returns:
            A dictionary containing summary statistics.
        """
        stats = {
            "total_benchmarks": len(self.benchmark_data),
            "total_instances_tested": len(set(b["instance_type"] for b in self.benchmark_data)),
            "best_performance": {},
            "cost_efficiency": {},
            "resource_usage": {},
        }

        if self.benchmark_data:
            # Best performance
            best_rps = max(self.benchmark_data, key=lambda x: x["requests_per_second"])
            best_latency = min(self.benchmark_data, key=lambda x: x["avg_latency"])

            stats["best_performance"] = {
                "highest_rps": {
                    "instance": best_rps["instance_type"],
                    "value": best_rps["requests_per_second"],
                },
                "lowest_latency": {
                    "instance": best_latency["instance_type"],
                    "value": best_latency["avg_latency"],
                },
            }

        if self.cost_data:
            # Cost efficiency
            best_cost = min(self.cost_data, key=lambda x: x["cost_per_1000_predictions"])
            best_efficiency = max(self.cost_data, key=lambda x: x["total_efficiency_score"])

            stats["cost_efficiency"] = {
                "most_cost_effective": {
                    "instance": best_cost["instance_name"],
                    "cost_per_1000": best_cost["cost_per_1000_predictions"],
                },
                "best_overall_efficiency": {
                    "instance": best_efficiency["instance_name"],
                    "score": best_efficiency["total_efficiency_score"],
                },
            }

        return stats

    def generate_html_report(self, output_path: str):
        """Generates the final HTML report.

        This method orchestrates the creation of all charts and summary
        statistics, renders them into an HTML template using Jinja2, and
        saves the result to a file.

        Args:
            output_path: The path to save the final HTML report.
        """
        logger.info("Generating HTML report...")

        # Create charts
        performance_chart = self.create_performance_comparison_chart()
        cost_chart = self.create_cost_analysis_chart()
        resource_chart = self.create_resource_utilization_chart()

        # Generate statistics
        stats = self.generate_summary_statistics()

        # HTML template
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MLOps Sentiment Analysis - Benchmark Report</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        .chart-container {
            margin: 30px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
            overflow: hidden;
        }
        .recommendations {
            background-color: #e8f5e8;
            border-left: 5px solid #27ae60;
            padding: 20px;
            margin: 20px 0;
        }
        .warning {
            background-color: #fff3cd;
            border-left: 5px solid #ffc107;
            padding: 20px;
            margin: 20px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 MLOps Sentiment Analysis<br>Benchmark Report</h1>

        <div class="stats-grid">
            <div class="stat-card">
                <div>Total Benchmarks</div>
                <div class="stat-value">{{ stats.total_benchmarks }}</div>
            </div>
            <div class="stat-card">
                <div>Instances Tested</div>
                <div class="stat-value">{{ stats.total_instances_tested }}</div>
            </div>
            {% if stats.best_performance.highest_rps %}
            <div class="stat-card">
                <div>Best RPS</div>
                <div class="stat-value">{{ "%.1f"|format(stats.best_performance.highest_rps.value) }}</div>
                <div>{{ stats.best_performance.highest_rps.instance }}</div>
            </div>
            {% endif %}
            {% if stats.cost_efficiency.most_cost_effective %}
            <div class="stat-card">
                <div>Most Cost-Effective</div>
                <div class="stat-value">${{ "%.4f"|format(stats.cost_efficiency.most_cost_effective.cost_per_1000) }}</div>
                <div>{{ stats.cost_efficiency.most_cost_effective.instance }}</div>
            </div>
            {% endif %}
        </div>

        <h2>📊 Performance Comparison</h2>
        <div class="chart-container">
            {{ performance_chart|safe }}
        </div>

        {% if cost_chart %}
        <h2>💰 Cost Analysis</h2>
        <div class="chart-container">
            {{ cost_chart|safe }}
        </div>
        {% endif %}

        {% if resource_chart %}
        <h2>🖥️ Resource Utilization</h2>
        <div class="chart-container">
            {{ resource_chart|safe }}
        </div>
        {% endif %}

        <h2>📋 Detailed Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Instance</th>
                    <th>Users</th>
                    <th>RPS</th>
                    <th>Avg Latency (ms)</th>
                    <th>P95 Latency (ms)</th>
                    <th>Successful Requests</th>
                    <th>Errors (%)</th>
                </tr>
            </thead>
            <tbody>
                {% for benchmark in benchmark_data %}
                <tr>
                    <td>{{ benchmark.instance_type }}</td>
                    <td>{{ benchmark.concurrent_users }}</td>
                    <td>{{ "%.2f"|format(benchmark.requests_per_second) }}</td>
                    <td>{{ "%.2f"|format(benchmark.avg_latency) }}</td>
                    <td>{{ "%.2f"|format(benchmark.p95_latency) }}</td>
                    <td>{{ benchmark.successful_requests }}</td>
                    <td>{{ "%.2f"|format(benchmark.error_rate) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        {% if cost_data %}
        <h2>💵 Cost Breakdown</h2>
        <table>
            <thead>
                <tr>
                    <th>Instance</th>
                    <th>Cost/Hour ($)</th>
                    <th>Cost per 1k Pred. ($)</th>
                    <th>RPS</th>
                    <th>Efficiency Score</th>
                </tr>
            </thead>
            <tbody>
                {% for cost in cost_data %}
                <tr>
                    <td>{{ cost.instance_name }}</td>
                    <td>${{ "%.3f"|format(cost.cost_per_hour) }}</td>
                    <td>${{ "%.4f"|format(cost.cost_per_1000_predictions) }}</td>
                    <td>{{ "%.2f"|format(cost.requests_per_second) }}</td>
                    <td>{{ "%.2f"|format(cost.total_efficiency_score) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        <div class="recommendations">
            <h3>🎯 Recommendations</h3>
            <ul>
                {% if stats.best_performance.highest_rps %}
                <li><strong>For High Throughput:</strong> Use {{ stats.best_performance.highest_rps.instance }} ({{ "%.1f"|format(stats.best_performance.highest_rps.value) }} RPS)</li>
                {% endif %}
                {% if stats.best_performance.lowest_latency %}
                <li><strong>For Low Latency:</strong> Use {{ stats.best_performance.lowest_latency.instance }} ({{ "%.1f"|format(stats.best_performance.lowest_latency.value) }}ms)</li>
                {% endif %}
                {% if stats.cost_efficiency.most_cost_effective %}
                <li><strong>For Cost Savings:</strong> Use {{ stats.cost_efficiency.most_cost_effective.instance }} (${{ "%.4f"|format(stats.cost_efficiency.most_cost_effective.cost_per_1000) }} per 1k predictions)</li>
                {% endif %}
                <li><strong>Monitoring:</strong> Set up alerts for latency >500ms and an error rate >5%</li>
                <li><strong>Autoscaling:</strong> Use HPA with CPU and custom metrics for dynamic scaling</li>
            </ul>
        </div>

        <div class="footer">
            <p>Report generated on: {{ generation_time }}</p>
            <p>MLOps Sentiment Analysis Benchmarking Framework</p>
        </div>
    </div>
</body>
</html>
        """

        # Render the template
        template = Template(html_template)
        html_content = template.render(
            stats=stats,
            benchmark_data=self.benchmark_data,
            cost_data=self.cost_data,
            performance_chart=performance_chart,
            cost_chart=cost_chart,
            resource_chart=resource_chart,
            generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        # Save the file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"HTML report saved to: {output_path}")


def main():
    """The main entry point for the report generation script."""
    parser = argparse.ArgumentParser(description="Comprehensive Benchmark Report Generator")
    parser.add_argument(
        "--results-dir", default="results", help="Directory containing benchmark results"
    )
    parser.add_argument(
        "--output", default="benchmark_comprehensive_report.html", help="Output HTML file path"
    )

    args = parser.parse_args()

    # Create the report generator
    generator = BenchmarkReportGenerator(args.results_dir)

    try:
        # Load the data
        generator.load_data()

        # Generate the HTML report
        generator.generate_html_report(args.output)

        logger.info(f"✅ Comprehensive report created: {args.output}")

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise


if __name__ == "__main__":
    main()
    main()
