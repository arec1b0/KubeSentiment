#!/usr/bin/env python3
"""
MLOps Sentiment Analysis - Comprehensive Report Generator
Генерация комплексных отчетов по результатам бенчмаркинга
"""

import json
import yaml
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from jinja2 import Template
import base64
from io import BytesIO

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BenchmarkReportGenerator:
    """Генератор комплексных отчетов по бенчмаркингу"""
    
    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.benchmark_data = []
        self.cost_data = []
        self.resource_data = []
        
    def load_data(self):
        """Загрузка всех данных бенчмарка"""
        logger.info("Загрузка данных бенчмарка...")
        
        # Загружаем результаты бенчмарков
        consolidated_file = self.results_dir / "consolidated_results.json"
        if consolidated_file.exists():
            with open(consolidated_file, 'r', encoding='utf-8') as f:
                self.benchmark_data = json.load(f)
        
        # Загружаем данные о стоимости
        cost_file = self.results_dir / "cost_analysis.json"
        if cost_file.exists():
            with open(cost_file, 'r', encoding='utf-8') as f:
                cost_analysis = json.load(f)
                self.cost_data = cost_analysis.get('analyses', [])
        
        # Загружаем данные о ресурсах
        for resource_file in self.results_dir.glob("resource_metrics_*.json"):
            with open(resource_file, 'r', encoding='utf-8') as f:
                resource_data = json.load(f)
                instance_name = resource_file.stem.replace('resource_metrics_', '')
                self.resource_data.append({
                    'instance': instance_name,
                    'metrics': resource_data
                })
        
        logger.info(f"Загружено: {len(self.benchmark_data)} бенчмарков, "
                   f"{len(self.cost_data)} анализов стоимости, "
                   f"{len(self.resource_data)} наборов метрик ресурсов")
    
    def create_performance_comparison_chart(self) -> str:
        """Создание графика сравнения производительности"""
        if not self.benchmark_data:
            return ""
        
        df = pd.DataFrame(self.benchmark_data)
        
        # Создаем subplot с несколькими графиками
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('RPS по инстансам', 'Латентность по инстансам', 
                          'Процентили латентности', 'Эффективность'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # График 1: RPS
        fig.add_trace(
            go.Bar(
                x=df['instance_type'],
                y=df['requests_per_second'],
                name='RPS',
                marker_color='lightblue'
            ),
            row=1, col=1
        )
        
        # График 2: Латентность
        fig.add_trace(
            go.Bar(
                x=df['instance_type'],
                y=df['avg_latency'],
                name='Avg Latency (ms)',
                marker_color='lightcoral'
            ),
            row=1, col=2
        )
        
        # График 3: Процентили латентности
        latency_percentiles = ['p50_latency', 'p90_latency', 'p95_latency', 'p99_latency']
        for percentile in latency_percentiles:
            if percentile in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df['instance_type'],
                        y=df[percentile],
                        mode='lines+markers',
                        name=percentile.replace('_latency', '').upper(),
                        line=dict(width=2)
                    ),
                    row=2, col=1
                )
        
        # График 4: Эффективность (RPS/стоимость)
        if self.cost_data:
            cost_df = pd.DataFrame(self.cost_data)
            efficiency = cost_df['requests_per_second'] / cost_df['cost_per_hour']
            fig.add_trace(
                go.Bar(
                    x=cost_df['instance_name'],
                    y=efficiency,
                    name='RPS/Cost Efficiency',
                    marker_color='lightgreen'
                ),
                row=2, col=2
            )
        
        fig.update_layout(
            height=800,
            title_text="Сравнение производительности инстансов",
            showlegend=True
        )
        
        # Сохраняем как HTML
        html_str = fig.to_html(include_plotlyjs='cdn')
        return html_str
    
    def create_cost_analysis_chart(self) -> str:
        """Создание графика анализа стоимости"""
        if not self.cost_data:
            return ""
        
        df = pd.DataFrame(self.cost_data)
        
        # Создаем bubble chart
        fig = go.Figure()
        
        # Размер пузырьков пропорционален общей эффективности
        sizes = df['total_efficiency_score'] * 50
        
        fig.add_trace(go.Scatter(
            x=df['cost_per_1000_predictions'],
            y=df['requests_per_second'],
            mode='markers',
            marker=dict(
                size=sizes,
                color=df['avg_latency_ms'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Латентность (ms)"),
                line=dict(width=2, color='DarkSlateGrey')
            ),
            text=df['instance_name'],
            textposition="middle center",
            hovertemplate='<b>%{text}</b><br>' +
                         'Стоимость 1000 пред.: $%{x:.4f}<br>' +
                         'RPS: %{y:.1f}<br>' +
                         'Латентность: %{marker.color:.1f}ms<br>' +
                         '<extra></extra>'
        ))
        
        fig.update_layout(
            title='Анализ стоимости и производительности<br><sub>Размер пузырька = общая эффективность</sub>',
            xaxis_title='Стоимость 1000 предсказаний (USD)',
            yaxis_title='Запросов в секунду (RPS)',
            width=800,
            height=600
        )
        
        return fig.to_html(include_plotlyjs='cdn')
    
    def create_resource_utilization_chart(self) -> str:
        """Создание графика утилизации ресурсов"""
        if not self.resource_data:
            return ""
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('CPU Utilization', 'Memory Utilization', 
                          'GPU Utilization', 'Resource Summary'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        colors = px.colors.qualitative.Set1
        
        for i, resource_set in enumerate(self.resource_data):
            instance = resource_set['instance']
            metrics = resource_set['metrics']
            
            if not metrics:
                continue
            
            # Извлекаем временные ряды
            timestamps = [m.get('timestamp', 0) for m in metrics]
            cpu_usage = [m.get('cpu_percent', 0) for m in metrics]
            memory_usage = [m.get('memory_percent', 0) for m in metrics]
            gpu_usage = [m.get('gpu_utilization', 0) for m in metrics if m.get('gpu_utilization') is not None]
            
            color = colors[i % len(colors)]
            
            # CPU график
            fig.add_trace(
                go.Scatter(
                    x=list(range(len(cpu_usage))),
                    y=cpu_usage,
                    mode='lines',
                    name=f'{instance} CPU',
                    line=dict(color=color, width=2)
                ),
                row=1, col=1
            )
            
            # Memory график
            fig.add_trace(
                go.Scatter(
                    x=list(range(len(memory_usage))),
                    y=memory_usage,
                    mode='lines',
                    name=f'{instance} Memory',
                    line=dict(color=color, width=2, dash='dash')
                ),
                row=1, col=2
            )
            
            # GPU график (если есть данные)
            if gpu_usage:
                fig.add_trace(
                    go.Scatter(
                        x=list(range(len(gpu_usage))),
                        y=gpu_usage,
                        mode='lines',
                        name=f'{instance} GPU',
                        line=dict(color=color, width=2, dash='dot')
                    ),
                    row=2, col=1
                )
        
        # Сводный график средних значений
        avg_data = []
        for resource_set in self.resource_data:
            instance = resource_set['instance']
            metrics = resource_set['metrics']
            
            if metrics:
                avg_cpu = np.mean([m.get('cpu_percent', 0) for m in metrics])
                avg_memory = np.mean([m.get('memory_percent', 0) for m in metrics])
                gpu_values = [m.get('gpu_utilization', 0) for m in metrics if m.get('gpu_utilization') is not None]
                avg_gpu = np.mean(gpu_values) if gpu_values else 0
                
                avg_data.append({
                    'instance': instance,
                    'cpu': avg_cpu,
                    'memory': avg_memory,
                    'gpu': avg_gpu
                })
        
        if avg_data:
            avg_df = pd.DataFrame(avg_data)
            
            fig.add_trace(
                go.Bar(
                    x=avg_df['instance'],
                    y=avg_df['cpu'],
                    name='Avg CPU %',
                    marker_color='lightblue'
                ),
                row=2, col=2
            )
            
            fig.add_trace(
                go.Bar(
                    x=avg_df['instance'],
                    y=avg_df['memory'],
                    name='Avg Memory %',
                    marker_color='lightcoral'
                ),
                row=2, col=2
            )
            
            # GPU только если есть данные
            if avg_df['gpu'].sum() > 0:
                fig.add_trace(
                    go.Bar(
                        x=avg_df['instance'],
                        y=avg_df['gpu'],
                        name='Avg GPU %',
                        marker_color='lightgreen'
                    ),
                    row=2, col=2
                )
        
        fig.update_layout(
            height=800,
            title_text="Утилизация ресурсов во время бенчмарка",
            showlegend=True
        )
        
        return fig.to_html(include_plotlyjs='cdn')
    
    def generate_summary_statistics(self) -> Dict[str, Any]:
        """Генерация сводной статистики"""
        stats = {
            'total_benchmarks': len(self.benchmark_data),
            'total_instances_tested': len(set(b['instance_type'] for b in self.benchmark_data)),
            'best_performance': {},
            'cost_efficiency': {},
            'resource_usage': {}
        }
        
        if self.benchmark_data:
            # Лучшая производительность
            best_rps = max(self.benchmark_data, key=lambda x: x['requests_per_second'])
            best_latency = min(self.benchmark_data, key=lambda x: x['avg_latency'])
            
            stats['best_performance'] = {
                'highest_rps': {
                    'instance': best_rps['instance_type'],
                    'value': best_rps['requests_per_second']
                },
                'lowest_latency': {
                    'instance': best_latency['instance_type'],
                    'value': best_latency['avg_latency']
                }
            }
        
        if self.cost_data:
            # Стоимостная эффективность
            best_cost = min(self.cost_data, key=lambda x: x['cost_per_1000_predictions'])
            best_efficiency = max(self.cost_data, key=lambda x: x['total_efficiency_score'])
            
            stats['cost_efficiency'] = {
                'most_cost_effective': {
                    'instance': best_cost['instance_name'],
                    'cost_per_1000': best_cost['cost_per_1000_predictions']
                },
                'best_overall_efficiency': {
                    'instance': best_efficiency['instance_name'],
                    'score': best_efficiency['total_efficiency_score']
                }
            }
        
        return stats
    
    def generate_html_report(self, output_path: str):
        """Генерация HTML отчета"""
        logger.info("Генерация HTML отчета...")
        
        # Создаем графики
        performance_chart = self.create_performance_comparison_chart()
        cost_chart = self.create_cost_analysis_chart()
        resource_chart = self.create_resource_utilization_chart()
        
        # Генерируем статистику
        stats = self.generate_summary_statistics()
        
        # HTML шаблон
        html_template = """
<!DOCTYPE html>
<html lang="ru">
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
                <div>Всего бенчмарков</div>
                <div class="stat-value">{{ stats.total_benchmarks }}</div>
            </div>
            <div class="stat-card">
                <div>Протестировано инстансов</div>
                <div class="stat-value">{{ stats.total_instances_tested }}</div>
            </div>
            {% if stats.best_performance.highest_rps %}
            <div class="stat-card">
                <div>Лучший RPS</div>
                <div class="stat-value">{{ "%.1f"|format(stats.best_performance.highest_rps.value) }}</div>
                <div>{{ stats.best_performance.highest_rps.instance }}</div>
            </div>
            {% endif %}
            {% if stats.cost_efficiency.most_cost_effective %}
            <div class="stat-card">
                <div>Самый экономичный</div>
                <div class="stat-value">${{ "%.4f"|format(stats.cost_efficiency.most_cost_effective.cost_per_1000) }}</div>
                <div>{{ stats.cost_efficiency.most_cost_effective.instance }}</div>
            </div>
            {% endif %}
        </div>
        
        <h2>📊 Сравнение производительности</h2>
        <div class="chart-container">
            {{ performance_chart|safe }}
        </div>
        
        {% if cost_chart %}
        <h2>💰 Анализ стоимости</h2>
        <div class="chart-container">
            {{ cost_chart|safe }}
        </div>
        {% endif %}
        
        {% if resource_chart %}
        <h2>🖥️ Утилизация ресурсов</h2>
        <div class="chart-container">
            {{ resource_chart|safe }}
        </div>
        {% endif %}
        
        <h2>📋 Детальные результаты</h2>
        <table>
            <thead>
                <tr>
                    <th>Инстанс</th>
                    <th>Пользователи</th>
                    <th>RPS</th>
                    <th>Средняя латентность (ms)</th>
                    <th>P95 латентность (ms)</th>
                    <th>Успешных запросов</th>
                    <th>Ошибок (%)</th>
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
        <h2>💵 Анализ стоимости</h2>
        <table>
            <thead>
                <tr>
                    <th>Инстанс</th>
                    <th>Стоимость/час ($)</th>
                    <th>Стоимость 1000 пред. ($)</th>
                    <th>RPS</th>
                    <th>Эффективность</th>
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
            <h3>🎯 Рекомендации</h3>
            <ul>
                {% if stats.best_performance.highest_rps %}
                <li><strong>Для высокой нагрузки:</strong> Используйте {{ stats.best_performance.highest_rps.instance }} ({{ "%.1f"|format(stats.best_performance.highest_rps.value) }} RPS)</li>
                {% endif %}
                {% if stats.best_performance.lowest_latency %}
                <li><strong>Для низкой латентности:</strong> Используйте {{ stats.best_performance.lowest_latency.instance }} ({{ "%.1f"|format(stats.best_performance.lowest_latency.value) }}ms)</li>
                {% endif %}
                {% if stats.cost_efficiency.most_cost_effective %}
                <li><strong>Для экономии:</strong> Используйте {{ stats.cost_efficiency.most_cost_effective.instance }} (${{ "%.4f"|format(stats.cost_efficiency.most_cost_effective.cost_per_1000) }} за 1000 предсказаний)</li>
                {% endif %}
                <li><strong>Мониторинг:</strong> Настройте алерты на латентность >500ms и error rate >5%</li>
                <li><strong>Автомасштабирование:</strong> Используйте HPA с метриками CPU и custom metrics</li>
            </ul>
        </div>
        
        <div class="footer">
            <p>Отчет сгенерирован: {{ generation_time }}</p>
            <p>MLOps Sentiment Analysis Benchmarking Framework</p>
        </div>
    </div>
</body>
</html>
        """
        
        # Рендерим шаблон
        template = Template(html_template)
        html_content = template.render(
            stats=stats,
            benchmark_data=self.benchmark_data,
            cost_data=self.cost_data,
            performance_chart=performance_chart,
            cost_chart=cost_chart,
            resource_chart=resource_chart,
            generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # Сохраняем файл
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML отчет сохранен: {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Comprehensive Benchmark Report Generator')
    parser.add_argument('--results-dir', default='results',
                       help='Directory containing benchmark results')
    parser.add_argument('--output', default='benchmark_comprehensive_report.html',
                       help='Output HTML file path')
    
    args = parser.parse_args()
    
    # Создаем генератор отчетов
    generator = BenchmarkReportGenerator(args.results_dir)
    
    try:
        # Загружаем данные
        generator.load_data()
        
        # Генерируем HTML отчет
        generator.generate_html_report(args.output)
        
        logger.info(f"✅ Комплексный отчет создан: {args.output}")
        
    except Exception as e:
        logger.error(f"Ошибка при генерации отчета: {e}")
        raise

if __name__ == "__main__":
    main()
