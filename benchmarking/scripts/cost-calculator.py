#!/usr/bin/env python3
"""
MLOps Sentiment Analysis - Cost Calculator
Расчет стоимости 1000 предсказаний для разных типов инстансов
"""

import json
import yaml
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class InstanceCost:
    """Стоимость инстанса"""
    name: str
    type: str
    cost_per_hour: float
    vcpu: int
    memory_gb: float
    gpu: Optional[str] = None
    gpu_memory_gb: Optional[float] = None

@dataclass
class BenchmarkCostAnalysis:
    """Анализ стоимости бенчмарка"""
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
    """Отчет сравнения стоимости"""
    timestamp: str
    total_predictions: int
    analyses: List[BenchmarkCostAnalysis]
    best_cost_efficiency: str
    best_latency_efficiency: str
    best_overall_efficiency: str
    recommendations: List[str]

class CostCalculator:
    """Калькулятор стоимости для бенчмарков"""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.instance_costs = self._parse_instance_costs()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Загрузка конфигурации"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _parse_instance_costs(self) -> Dict[str, InstanceCost]:
        """Парсинг стоимости инстансов из конфигурации"""
        instance_costs = {}
        
        # CPU инстансы
        for instance in self.config['instances']['cpu']:
            cost = InstanceCost(
                name=instance['name'],
                type=instance['type'],
                cost_per_hour=instance['cost_per_hour'],
                vcpu=instance['vcpu'],
                memory_gb=float(instance['memory'].replace('Gi', ''))
            )
            instance_costs[instance['name']] = cost
        
        # GPU инстансы
        for instance in self.config['instances']['gpu']:
            cost = InstanceCost(
                name=instance['name'],
                type=instance['type'],
                cost_per_hour=instance['cost_per_hour'],
                vcpu=instance['vcpu'],
                memory_gb=float(instance['memory'].replace('Gi', '')),
                gpu=instance['gpu'],
                gpu_memory_gb=float(instance['gpu_memory'].replace('Gi', ''))
            )
            instance_costs[instance['name']] = cost
        
        return instance_costs
    
    def calculate_cost_analysis(self, benchmark_results_path: str) -> List[BenchmarkCostAnalysis]:
        """Расчет анализа стоимости на основе результатов бенчмарка"""
        analyses = []
        
        # Загружаем результаты бенчмарка
        with open(benchmark_results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        # Если это один результат, оборачиваем в список
        if isinstance(results, dict):
            results = [results]
        
        for result in results:
            instance_type = result['instance_type']
            
            if instance_type not in self.instance_costs:
                logger.warning(f"Instance type {instance_type} not found in cost configuration")
                continue
            
            instance_cost = self.instance_costs[instance_type]
            
            # Расчет метрик
            rps = result['requests_per_second']
            avg_latency = result['avg_latency']
            predictions_per_hour = rps * 3600  # RPS * секунд в часе
            
            # Стоимость 1000 предсказаний
            if predictions_per_hour > 0:
                cost_per_1000_predictions = (instance_cost.cost_per_hour * 1000) / predictions_per_hour
            else:
                cost_per_1000_predictions = float('inf')
            
            # Эффективность
            cost_efficiency = rps / instance_cost.cost_per_hour if instance_cost.cost_per_hour > 0 else 0
            latency_efficiency = 1000 / avg_latency if avg_latency > 0 else 0
            total_efficiency = (cost_efficiency * latency_efficiency) / cost_per_1000_predictions if cost_per_1000_predictions > 0 else 0
            
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
                total_efficiency_score=total_efficiency
            )
            
            analyses.append(analysis)
        
        return analyses
    
    def generate_cost_comparison_report(self, analyses: List[BenchmarkCostAnalysis], 
                                      total_predictions: int = 1000) -> CostComparisonReport:
        """Генерация отчета сравнения стоимости"""
        
        if not analyses:
            raise ValueError("No analyses provided")
        
        # Находим лучшие варианты
        best_cost = min(analyses, key=lambda x: x.cost_per_1000_predictions)
        best_latency = min(analyses, key=lambda x: x.avg_latency_ms)
        best_overall = max(analyses, key=lambda x: x.total_efficiency_score)
        
        # Генерируем рекомендации
        recommendations = self._generate_recommendations(analyses)
        
        report = CostComparisonReport(
            timestamp=datetime.now().isoformat(),
            total_predictions=total_predictions,
            analyses=analyses,
            best_cost_efficiency=best_cost.instance_name,
            best_latency_efficiency=best_latency.instance_name,
            best_overall_efficiency=best_overall.instance_name,
            recommendations=recommendations
        )
        
        return report
    
    def _generate_recommendations(self, analyses: List[BenchmarkCostAnalysis]) -> List[str]:
        """Генерация рекомендаций на основе анализа"""
        recommendations = []
        
        # Сортируем по стоимости
        cost_sorted = sorted(analyses, key=lambda x: x.cost_per_1000_predictions)
        latency_sorted = sorted(analyses, key=lambda x: x.avg_latency_ms)
        efficiency_sorted = sorted(analyses, key=lambda x: x.total_efficiency_score, reverse=True)
        
        # Рекомендации по стоимости
        cheapest = cost_sorted[0]
        most_expensive = cost_sorted[-1]
        
        cost_diff = most_expensive.cost_per_1000_predictions / cheapest.cost_per_1000_predictions
        
        recommendations.append(
            f"💰 Самый экономичный вариант: {cheapest.instance_name} "
            f"(${cheapest.cost_per_1000_predictions:.4f} за 1000 предсказаний)"
        )
        
        if cost_diff > 2:
            recommendations.append(
                f"⚠️ Разница в стоимости между самым дешевым и дорогим инстансом составляет {cost_diff:.1f}x"
            )
        
        # Рекомендации по латентности
        fastest = latency_sorted[0]
        slowest = latency_sorted[-1]
        
        recommendations.append(
            f"⚡ Самый быстрый вариант: {fastest.instance_name} "
            f"({fastest.avg_latency_ms:.2f}ms средняя латентность)"
        )
        
        # Рекомендации по общей эффективности
        most_efficient = efficiency_sorted[0]
        recommendations.append(
            f"🎯 Лучший баланс цена/производительность: {most_efficient.instance_name}"
        )
        
        # Специфичные рекомендации
        gpu_analyses = [a for a in analyses if 'gpu' in a.instance_name.lower()]
        cpu_analyses = [a for a in analyses if 'cpu' in a.instance_name.lower()]
        
        if gpu_analyses and cpu_analyses:
            best_gpu = min(gpu_analyses, key=lambda x: x.cost_per_1000_predictions)
            best_cpu = min(cpu_analyses, key=lambda x: x.cost_per_1000_predictions)
            
            if best_cpu.cost_per_1000_predictions < best_gpu.cost_per_1000_predictions:
                savings = ((best_gpu.cost_per_1000_predictions - best_cpu.cost_per_1000_predictions) / 
                          best_gpu.cost_per_1000_predictions) * 100
                recommendations.append(
                    f"💡 CPU инстансы экономичнее GPU на {savings:.1f}% для данной нагрузки"
                )
            else:
                performance_gain = (best_gpu.requests_per_second / best_cpu.requests_per_second - 1) * 100
                recommendations.append(
                    f"🚀 GPU инстансы обеспечивают прирост производительности на {performance_gain:.1f}%"
                )
        
        # Рекомендации по масштабированию
        high_rps_instances = [a for a in analyses if a.requests_per_second > 100]
        if high_rps_instances:
            recommendations.append(
                "📈 Для высоких нагрузок (>100 RPS) рекомендуется использовать: " +
                ", ".join([a.instance_name for a in high_rps_instances[:3]])
            )
        
        return recommendations
    
    def save_cost_report(self, report: CostComparisonReport, output_path: str):
        """Сохранение отчета о стоимости"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, indent=2, ensure_ascii=False)
        
        logger.info(f"Cost report saved to {output_path}")
    
    def generate_cost_visualization(self, analyses: List[BenchmarkCostAnalysis], 
                                  output_dir: str):
        """Генерация визуализации стоимости"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Подготовка данных
        df = pd.DataFrame([asdict(a) for a in analyses])
        
        # Создаем фигуру с несколькими графиками
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # График 1: Стоимость за 1000 предсказаний
        ax1 = axes[0, 0]
        bars1 = ax1.bar(df['instance_name'], df['cost_per_1000_predictions'])
        ax1.set_title('Стоимость 1000 предсказаний по типам инстансов')
        ax1.set_xlabel('Тип инстанса')
        ax1.set_ylabel('Стоимость (USD)')
        ax1.tick_params(axis='x', rotation=45)
        
        # Добавляем значения на столбцы
        for bar, value in zip(bars1, df['cost_per_1000_predictions']):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
                    f'${value:.4f}', ha='center', va='bottom', fontsize=9)
        
        # График 2: RPS vs Стоимость в час
        ax2 = axes[0, 1]
        scatter = ax2.scatter(df['cost_per_hour'], df['requests_per_second'], 
                             s=100, alpha=0.7, c=df['avg_latency_ms'], cmap='viridis')
        ax2.set_title('Производительность vs Стоимость')
        ax2.set_xlabel('Стоимость в час (USD)')
        ax2.set_ylabel('Запросов в секунду')
        
        # Добавляем подписи точек
        for i, row in df.iterrows():
            ax2.annotate(row['instance_name'], 
                        (row['cost_per_hour'], row['requests_per_second']),
                        xytext=(5, 5), textcoords='offset points', fontsize=8)
        
        # Цветовая шкала для латентности
        cbar = plt.colorbar(scatter, ax=ax2)
        cbar.set_label('Средняя латентность (ms)')
        
        # График 3: Эффективность
        ax3 = axes[1, 0]
        efficiency_bars = ax3.bar(df['instance_name'], df['total_efficiency_score'])
        ax3.set_title('Общая эффективность (производительность/стоимость)')
        ax3.set_xlabel('Тип инстанса')
        ax3.set_ylabel('Оценка эффективности')
        ax3.tick_params(axis='x', rotation=45)
        
        # График 4: Сравнение латентности
        ax4 = axes[1, 1]
        latency_bars = ax4.bar(df['instance_name'], df['avg_latency_ms'])
        ax4.set_title('Средняя латентность по типам инстансов')
        ax4.set_xlabel('Тип инстанса')
        ax4.set_ylabel('Латентность (ms)')
        ax4.tick_params(axis='x', rotation=45)
        
        # Добавляем значения на столбцы
        for bar, value in zip(latency_bars, df['avg_latency_ms']):
            ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{value:.1f}ms', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'cost_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Дополнительный график: Стоимость vs Производительность (bubble chart)
        plt.figure(figsize=(12, 8))
        
        # Размер пузырьков пропорционален эффективности
        sizes = [max(50, a.total_efficiency_score * 100) for a in analyses]
        
        scatter = plt.scatter(df['cost_per_1000_predictions'], df['requests_per_second'],
                             s=sizes, alpha=0.6, c=df['avg_latency_ms'], cmap='RdYlBu_r')
        
        plt.xlabel('Стоимость 1000 предсказаний (USD)')
        plt.ylabel('Запросов в секунду')
        plt.title('Анализ стоимости и производительности\n(размер пузырька = общая эффективность)')
        
        # Добавляем подписи
        for i, row in df.iterrows():
            plt.annotate(row['instance_name'], 
                        (row['cost_per_1000_predictions'], row['requests_per_second']),
                        xytext=(5, 5), textcoords='offset points')
        
        # Цветовая шкала
        cbar = plt.colorbar(scatter)
        cbar.set_label('Средняя латентность (ms)')
        
        plt.grid(True, alpha=0.3)
        plt.savefig(output_dir / 'cost_performance_bubble.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Cost visualization saved to {output_dir}")
    
    def print_cost_summary(self, report: CostComparisonReport):
        """Вывод сводки по стоимости"""
        print(f"\n{'='*80}")
        print("АНАЛИЗ СТОИМОСТИ БЕНЧМАРКА")
        print(f"{'='*80}")
        print(f"Дата анализа: {report.timestamp}")
        print(f"Количество предсказаний: {report.total_predictions}")
        print(f"\n{'Инстанс':<15} {'Тип':<15} {'$/час':<10} {'RPS':<8} {'Латентность':<12} {'$/1000 пред.':<12}")
        print("-" * 80)
        
        for analysis in sorted(report.analyses, key=lambda x: x.cost_per_1000_predictions):
            print(f"{analysis.instance_name:<15} "
                  f"{analysis.instance_type:<15} "
                  f"${analysis.cost_per_hour:<9.3f} "
                  f"{analysis.requests_per_second:<7.1f} "
                  f"{analysis.avg_latency_ms:<11.1f}ms "
                  f"${analysis.cost_per_1000_predictions:<11.4f}")
        
        print(f"\n{'='*80}")
        print("РЕКОМЕНДАЦИИ:")
        print(f"{'='*80}")
        
        for i, recommendation in enumerate(report.recommendations, 1):
            print(f"{i}. {recommendation}")
        
        print(f"\n🏆 Лучший по стоимости: {report.best_cost_efficiency}")
        print(f"⚡ Лучший по скорости: {report.best_latency_efficiency}")
        print(f"🎯 Лучший общий баланс: {report.best_overall_efficiency}")

def main():
    parser = argparse.ArgumentParser(description='Cost Calculator for MLOps Benchmarking')
    parser.add_argument('--config', default='configs/benchmark-config.yaml',
                       help='Path to benchmark configuration file')
    parser.add_argument('--results', required=True,
                       help='Path to benchmark results JSON file(s)')
    parser.add_argument('--predictions', type=int, default=1000,
                       help='Number of predictions for cost calculation')
    parser.add_argument('--output', default='results/cost_analysis.json',
                       help='Output file for cost analysis')
    parser.add_argument('--report-dir', default='results/cost_reports',
                       help='Directory for generated reports')
    
    args = parser.parse_args()
    
    # Создаем калькулятор
    calculator = CostCalculator(args.config)
    
    try:
        # Рассчитываем анализ стоимости
        analyses = calculator.calculate_cost_analysis(args.results)
        
        if not analyses:
            logger.error("No valid analyses generated")
            return
        
        # Генерируем отчет
        report = calculator.generate_cost_comparison_report(analyses, args.predictions)
        
        # Сохраняем отчет
        calculator.save_cost_report(report, args.output)
        
        # Генерируем визуализацию
        calculator.generate_cost_visualization(analyses, args.report_dir)
        
        # Выводим сводку
        calculator.print_cost_summary(report)
        
    except Exception as e:
        logger.error(f"Cost calculation failed: {e}")
        raise

if __name__ == "__main__":
    main()
