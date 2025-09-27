#!/usr/bin/env python3
"""
MLOps Sentiment Analysis - Load Testing Script
Нагрузочное тестирование для измерения производительности модели
"""

import asyncio
import aiohttp
import argparse
import json
import time
import yaml
import statistics
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Результат одного запроса"""
    timestamp: float
    latency: float
    status_code: int
    success: bool
    error: Optional[str] = None
    response_size: int = 0

@dataclass
class BenchmarkMetrics:
    """Метрики бенчмарка"""
    instance_type: str
    concurrent_users: int
    duration: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    avg_latency: float
    p50_latency: float
    p90_latency: float
    p95_latency: float
    p99_latency: float
    min_latency: float
    max_latency: float
    error_rate: float
    throughput: float
    cpu_usage: float
    memory_usage: float
    gpu_usage: Optional[float] = None

class LoadTester:
    """Класс для проведения нагрузочного тестирования"""
    
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Загрузка конфигурации"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _generate_test_data(self) -> List[Dict[str, Any]]:
        """Генерация тестовых данных"""
        test_texts = [
            "Этот продукт просто великолепен! Очень доволен покупкой.",
            "Ужасное качество, деньги на ветер. Не рекомендую.",
            "Нормальный товар, ничего особенного, но свои деньги стоит.",
            "Превосходное обслуживание и быстрая доставка!",
            "Полное разочарование, ожидал большего от этого бренда.",
            "Отличное соотношение цены и качества.",
            "Товар пришел поврежденным, очень расстроен.",
            "Рекомендую всем! Лучшая покупка в этом году.",
            "Средненько, есть варианты получше за эту цену.",
            "Фантастический продукт, буду заказывать еще!"
        ]
        
        samples_count = self.config['benchmark']['test_data']['samples_count']
        test_data = []
        
        for i in range(samples_count):
            text = test_texts[i % len(test_texts)]
            test_data.append({
                "text": text,
                "id": f"test_{i}",
                "timestamp": datetime.now().isoformat()
            })
            
        return test_data
    
    async def _make_request(self, session: aiohttp.ClientSession, 
                           url: str, data: Dict[str, Any]) -> TestResult:
        """Выполнение одного HTTP запроса"""
        start_time = time.time()
        
        try:
            timeout = aiohttp.ClientTimeout(
                total=self.config['benchmark']['load_test']['request_timeout']
            )
            
            async with session.post(url, json=data, timeout=timeout) as response:
                response_text = await response.text()
                end_time = time.time()
                
                return TestResult(
                    timestamp=start_time,
                    latency=(end_time - start_time) * 1000,  # в миллисекундах
                    status_code=response.status,
                    success=response.status == 200,
                    response_size=len(response_text)
                )
                
        except Exception as e:
            end_time = time.time()
            return TestResult(
                timestamp=start_time,
                latency=(end_time - start_time) * 1000,
                status_code=0,
                success=False,
                error=str(e)
            )
    
    async def _user_simulation(self, user_id: int, url: str, 
                              test_data: List[Dict[str, Any]], 
                              duration: int) -> List[TestResult]:
        """Симуляция одного пользователя"""
        results = []
        end_time = time.time() + duration
        
        async with aiohttp.ClientSession() as session:
            request_count = 0
            
            while time.time() < end_time:
                # Выбираем случайные тестовые данные
                data = test_data[request_count % len(test_data)]
                
                result = await self._make_request(session, url, data)
                results.append(result)
                
                request_count += 1
                
                # Небольшая пауза между запросами (имитация реального пользователя)
                await asyncio.sleep(0.1)
        
        logger.info(f"User {user_id} completed {len(results)} requests")
        return results
    
    async def run_load_test(self, instance_type: str, concurrent_users: int, 
                           duration: int, endpoint_url: str) -> List[TestResult]:
        """Запуск нагрузочного теста"""
        logger.info(f"Starting load test: {concurrent_users} users, {duration}s duration")
        
        test_data = self._generate_test_data()
        self.start_time = time.time()
        
        # Создаем задачи для всех пользователей
        tasks = []
        for user_id in range(concurrent_users):
            task = self._user_simulation(user_id, endpoint_url, test_data, duration)
            tasks.append(task)
        
        # Запускаем все задачи параллельно
        user_results = await asyncio.gather(*tasks)
        
        # Объединяем результаты всех пользователей
        all_results = []
        for results in user_results:
            all_results.extend(results)
        
        self.end_time = time.time()
        self.results = all_results
        
        logger.info(f"Load test completed: {len(all_results)} total requests")
        return all_results
    
    def calculate_metrics(self, instance_type: str, concurrent_users: int) -> BenchmarkMetrics:
        """Расчет метрик производительности"""
        if not self.results:
            raise ValueError("No test results available")
        
        successful_results = [r for r in self.results if r.success]
        failed_results = [r for r in self.results if not r.success]
        
        latencies = [r.latency for r in successful_results]
        
        if not latencies:
            raise ValueError("No successful requests")
        
        duration = self.end_time - self.start_time
        
        metrics = BenchmarkMetrics(
            instance_type=instance_type,
            concurrent_users=concurrent_users,
            duration=duration,
            total_requests=len(self.results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            requests_per_second=len(self.results) / duration,
            avg_latency=statistics.mean(latencies),
            p50_latency=np.percentile(latencies, 50),
            p90_latency=np.percentile(latencies, 90),
            p95_latency=np.percentile(latencies, 95),
            p99_latency=np.percentile(latencies, 99),
            min_latency=min(latencies),
            max_latency=max(latencies),
            error_rate=(len(failed_results) / len(self.results)) * 100,
            throughput=len(successful_results) / duration,
            cpu_usage=0.0,  # Будет заполнено мониторингом
            memory_usage=0.0,  # Будет заполнено мониторингом
        )
        
        return metrics
    
    def save_results(self, metrics: BenchmarkMetrics, output_path: str):
        """Сохранение результатов"""
        # Создаем директорию если не существует
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем метрики в JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(metrics), f, indent=2, ensure_ascii=False)
        
        # Сохраняем детальные результаты
        detailed_path = output_path.replace('.json', '_detailed.json')
        detailed_results = [asdict(r) for r in self.results]
        
        with open(detailed_path, 'w', encoding='utf-8') as f:
            json.dump(detailed_results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to {output_path}")
    
    def generate_report(self, metrics: BenchmarkMetrics, output_dir: str):
        """Генерация отчета с графиками"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # График латентности
        plt.figure(figsize=(12, 8))
        
        # Гистограмма латентности
        plt.subplot(2, 2, 1)
        latencies = [r.latency for r in self.results if r.success]
        plt.hist(latencies, bins=50, alpha=0.7, edgecolor='black')
        plt.xlabel('Latency (ms)')
        plt.ylabel('Frequency')
        plt.title('Latency Distribution')
        plt.grid(True, alpha=0.3)
        
        # График RPS во времени
        plt.subplot(2, 2, 2)
        timestamps = [r.timestamp for r in self.results]
        start_time = min(timestamps)
        time_buckets = {}
        
        for result in self.results:
            bucket = int((result.timestamp - start_time) // 10) * 10  # 10-секундные интервалы
            if bucket not in time_buckets:
                time_buckets[bucket] = 0
            time_buckets[bucket] += 1
        
        times = sorted(time_buckets.keys())
        rps_values = [time_buckets[t] / 10 for t in times]  # RPS
        
        plt.plot(times, rps_values, marker='o')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Requests per Second')
        plt.title('RPS Over Time')
        plt.grid(True, alpha=0.3)
        
        # Процентили латентности
        plt.subplot(2, 2, 3)
        percentiles = [50, 90, 95, 99]
        latency_percentiles = [np.percentile(latencies, p) for p in percentiles]
        
        plt.bar([f'P{p}' for p in percentiles], latency_percentiles)
        plt.xlabel('Percentile')
        plt.ylabel('Latency (ms)')
        plt.title('Latency Percentiles')
        plt.grid(True, alpha=0.3)
        
        # Статус кодов
        plt.subplot(2, 2, 4)
        status_codes = {}
        for result in self.results:
            code = result.status_code if result.status_code != 0 else 'Error'
            status_codes[code] = status_codes.get(code, 0) + 1
        
        plt.pie(status_codes.values(), labels=status_codes.keys(), autopct='%1.1f%%')
        plt.title('Response Status Codes')
        
        plt.tight_layout()
        plt.savefig(output_dir / f'benchmark_report_{metrics.instance_type}_{metrics.concurrent_users}users.png', 
                   dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Report generated in {output_dir}")

async def main():
    parser = argparse.ArgumentParser(description='MLOps Sentiment Analysis Load Testing')
    parser.add_argument('--config', default='configs/benchmark-config.yaml',
                       help='Path to benchmark configuration file')
    parser.add_argument('--instance-type', required=True,
                       help='Instance type to test (cpu-small, gpu-t4, etc.)')
    parser.add_argument('--endpoint', required=True,
                       help='API endpoint URL')
    parser.add_argument('--users', type=int, default=10,
                       help='Number of concurrent users')
    parser.add_argument('--duration', type=int, default=60,
                       help='Test duration in seconds')
    parser.add_argument('--output', default='results/benchmark_results.json',
                       help='Output file for results')
    parser.add_argument('--report-dir', default='results/reports',
                       help='Directory for generated reports')
    
    args = parser.parse_args()
    
    # Создаем тестер
    tester = LoadTester(args.config)
    
    try:
        # Запускаем нагрузочный тест
        results = await tester.run_load_test(
            instance_type=args.instance_type,
            concurrent_users=args.users,
            duration=args.duration,
            endpoint_url=args.endpoint
        )
        
        # Рассчитываем метрики
        metrics = tester.calculate_metrics(args.instance_type, args.users)
        
        # Выводим результаты
        print(f"\n{'='*60}")
        print(f"BENCHMARK RESULTS - {args.instance_type}")
        print(f"{'='*60}")
        print(f"Concurrent Users: {metrics.concurrent_users}")
        print(f"Duration: {metrics.duration:.2f}s")
        print(f"Total Requests: {metrics.total_requests}")
        print(f"Successful Requests: {metrics.successful_requests}")
        print(f"Failed Requests: {metrics.failed_requests}")
        print(f"Requests per Second: {metrics.requests_per_second:.2f}")
        print(f"Average Latency: {metrics.avg_latency:.2f}ms")
        print(f"P50 Latency: {metrics.p50_latency:.2f}ms")
        print(f"P95 Latency: {metrics.p95_latency:.2f}ms")
        print(f"P99 Latency: {metrics.p99_latency:.2f}ms")
        print(f"Error Rate: {metrics.error_rate:.2f}%")
        print(f"Throughput: {metrics.throughput:.2f} req/s")
        
        # Сохраняем результаты
        tester.save_results(metrics, args.output)
        
        # Генерируем отчет
        tester.generate_report(metrics, args.report_dir)
        
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
