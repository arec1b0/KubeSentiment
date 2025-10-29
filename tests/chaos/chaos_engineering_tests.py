#!/usr/bin/env python3
"""
Chaos Engineering Test Suite for KubeSentiment
Tests system resilience under various failure conditions
"""

import asyncio
import time
import subprocess
import json
import random
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ChaosExperiment:
    """Configuration for a chaos experiment"""
    name: str
    description: str
    namespace: str
    app_label: str
    duration_seconds: int


class KubernetesClient:
    """Simple Kubernetes client for chaos operations"""

    @staticmethod
    def run_kubectl(args: List[str]) -> tuple[int, str, str]:
        """Execute kubectl command"""
        cmd = ['kubectl'] + args
        logger.debug(f"Executing: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    @classmethod
    def get_pods(cls, namespace: str, label_selector: str) -> List[str]:
        """Get list of pod names matching label selector"""
        code, stdout, stderr = cls.run_kubectl([
            'get', 'pods',
            '-n', namespace,
            '-l', label_selector,
            '-o', 'jsonpath={.items[*].metadata.name}'
        ])

        if code == 0:
            return stdout.split()
        else:
            logger.error(f"Failed to get pods: {stderr}")
            return []

    @classmethod
    def delete_pod(cls, namespace: str, pod_name: str) -> bool:
        """Delete a specific pod"""
        logger.info(f"Deleting pod: {pod_name}")
        code, stdout, stderr = cls.run_kubectl([
            'delete', 'pod', pod_name,
            '-n', namespace,
            '--grace-period=0',
            '--force'
        ])

        if code == 0:
            logger.info(f"Successfully deleted pod: {pod_name}")
            return True
        else:
            logger.error(f"Failed to delete pod: {stderr}")
            return False

    @classmethod
    def get_pod_status(cls, namespace: str, pod_name: str) -> Optional[Dict]:
        """Get pod status"""
        code, stdout, stderr = cls.run_kubectl([
            'get', 'pod', pod_name,
            '-n', namespace,
            '-o', 'json'
        ])

        if code == 0:
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                logger.error("Failed to parse pod JSON")
                return None
        return None

    @classmethod
    def wait_for_pod_ready(cls, namespace: str, label_selector: str, timeout: int = 120) -> bool:
        """Wait for pods to be ready"""
        logger.info(f"Waiting for pods with label {label_selector} to be ready...")

        code, stdout, stderr = cls.run_kubectl([
            'wait', '--for=condition=ready',
            'pod',
            '-l', label_selector,
            '-n', namespace,
            f'--timeout={timeout}s'
        ])

        if code == 0:
            logger.info("Pods are ready")
            return True
        else:
            logger.warning(f"Pods not ready within timeout: {stderr}")
            return False

    @classmethod
    def get_deployment_replicas(cls, namespace: str, deployment_name: str) -> Optional[int]:
        """Get number of replicas for a deployment"""
        code, stdout, stderr = cls.run_kubectl([
            'get', 'deployment', deployment_name,
            '-n', namespace,
            '-o', 'jsonpath={.spec.replicas}'
        ])

        if code == 0:
            try:
                return int(stdout)
            except ValueError:
                return None
        return None

    @classmethod
    def scale_deployment(cls, namespace: str, deployment_name: str, replicas: int) -> bool:
        """Scale deployment to specified replicas"""
        logger.info(f"Scaling deployment {deployment_name} to {replicas} replicas")

        code, stdout, stderr = cls.run_kubectl([
            'scale', 'deployment', deployment_name,
            '-n', namespace,
            f'--replicas={replicas}'
        ])

        if code == 0:
            logger.info(f"Successfully scaled deployment")
            return True
        else:
            logger.error(f"Failed to scale deployment: {stderr}")
            return False

    @classmethod
    def apply_network_partition(cls, namespace: str, pod_name: str, target_cidr: str) -> bool:
        """Simulate network partition by blocking traffic to target CIDR"""
        logger.info(f"Applying network partition to pod {pod_name}, blocking {target_cidr}")

        # Use iptables to block traffic (requires NET_ADMIN capability)
        command = f"iptables -A OUTPUT -d {target_cidr} -j DROP"

        code, stdout, stderr = cls.run_kubectl([
            'exec', pod_name,
            '-n', namespace,
            '--',
            'sh', '-c', command
        ])

        if code == 0:
            logger.info("Network partition applied")
            return True
        else:
            logger.warning(f"Failed to apply network partition (may need NET_ADMIN): {stderr}")
            return False

    @classmethod
    def remove_network_partition(cls, namespace: str, pod_name: str, target_cidr: str) -> bool:
        """Remove network partition"""
        logger.info(f"Removing network partition from pod {pod_name}")

        command = f"iptables -D OUTPUT -d {target_cidr} -j DROP"

        code, stdout, stderr = cls.run_kubectl([
            'exec', pod_name,
            '-n', namespace,
            '--',
            'sh', '-c', command
        ])

        return code == 0


class ServiceHealthChecker:
    """Check service health during chaos experiments"""

    def __init__(self, service_url: str, namespace: str, service_name: str):
        self.service_url = service_url
        self.namespace = namespace
        self.service_name = service_name

    async def check_health(self) -> bool:
        """Check if service is healthy"""
        try:
            # Use kubectl to port-forward and check health
            code, stdout, stderr = KubernetesClient.run_kubectl([
                'run', 'health-check-temp',
                '--rm', '-i',
                '--restart=Never',
                '--image=curlimages/curl:latest',
                '-n', self.namespace,
                '--',
                'curl', '-f', '-s',
                f'http://{self.service_name}:80/health',
                '--connect-timeout', '5'
            ])

            return code == 0

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def check_predict_endpoint(self) -> bool:
        """Check if prediction endpoint is working"""
        try:
            test_payload = '{"text":"test message for chaos engineering"}'

            code, stdout, stderr = KubernetesClient.run_kubectl([
                'run', 'predict-check-temp',
                '--rm', '-i',
                '--restart=Never',
                '--image=curlimages/curl:latest',
                '-n', self.namespace,
                '--',
                'curl', '-f', '-s',
                '-X', 'POST',
                f'http://{self.service_name}:80/api/v1/predict',
                '-H', 'Content-Type: application/json',
                '-d', test_payload,
                '--connect-timeout', '10'
            ])

            return code == 0

        except Exception as e:
            logger.error(f"Predict endpoint check failed: {e}")
            return False


class ChaosEngineeringTests:
    """Chaos engineering test suite"""

    def __init__(self, namespace: str, app_label: str, service_name: str):
        self.namespace = namespace
        self.app_label = app_label
        self.service_name = service_name
        self.health_checker = ServiceHealthChecker("", namespace, service_name)

        self.results = []

    async def run_all_tests(self) -> Dict:
        """Run all chaos engineering tests"""
        logger.info("Starting Chaos Engineering Test Suite")
        logger.info(f"Namespace: {self.namespace}, App Label: {self.app_label}")

        tests = [
            ("Pod Termination Test", self.test_pod_termination),
            ("Random Pod Killer Test", self.test_random_pod_killer),
            ("Multiple Pod Termination Test", self.test_multiple_pod_termination),
            ("Service Degradation Test", self.test_service_degradation),
            ("Rapid Scaling Test", self.test_rapid_scaling),
        ]

        for test_name, test_func in tests:
            logger.info(f"\n{'='*60}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'='*60}")

            try:
                result = await test_func()
                self.results.append({
                    "test": test_name,
                    "status": "passed" if result else "failed",
                    "details": result if isinstance(result, dict) else {}
                })
            except Exception as e:
                logger.error(f"Test {test_name} failed with exception: {e}")
                self.results.append({
                    "test": test_name,
                    "status": "error",
                    "error": str(e)
                })

            # Wait between tests
            await asyncio.sleep(10)

        return self._generate_report()

    async def test_pod_termination(self) -> bool:
        """
        Chaos Test: Single Pod Termination
        Validates that the system can recover from a single pod failure
        """
        logger.info("Test: Single Pod Termination")

        # Get current pods
        pods = KubernetesClient.get_pods(self.namespace, self.app_label)
        if not pods:
            logger.error("No pods found")
            return False

        logger.info(f"Found {len(pods)} pods")

        # Check initial health
        initial_health = await self.health_checker.check_health()
        logger.info(f"Initial health check: {'PASS' if initial_health else 'FAIL'}")

        # Kill one pod
        target_pod = pods[0]
        logger.info(f"Terminating pod: {target_pod}")

        if not KubernetesClient.delete_pod(self.namespace, target_pod):
            logger.error("Failed to delete pod")
            return False

        # Wait a moment for pod to terminate
        await asyncio.sleep(5)

        # Check that service is still available (other replicas should handle traffic)
        during_health = await self.health_checker.check_health()
        logger.info(f"Health during pod termination: {'PASS' if during_health else 'FAIL'}")

        # Wait for replacement pod to be ready
        recovery_success = KubernetesClient.wait_for_pod_ready(
            self.namespace,
            self.app_label,
            timeout=120
        )

        # Final health check
        final_health = await self.health_checker.check_health()
        logger.info(f"Final health check: {'PASS' if final_health else 'FAIL'}")

        # Test passes if:
        # 1. Service remained available during termination (due to other replicas)
        # 2. New pod successfully started
        # 3. Final health check passed

        passed = during_health and recovery_success and final_health

        logger.info(f"Pod Termination Test: {'PASSED' if passed else 'FAILED'}")
        return passed

    async def test_random_pod_killer(self) -> bool:
        """
        Chaos Test: Random Pod Killer
        Randomly terminates pods over a period of time
        """
        logger.info("Test: Random Pod Killer (30 seconds)")

        duration = 30
        kill_interval = 10  # Kill a pod every 10 seconds

        start_time = time.time()
        health_checks = []

        while time.time() - start_time < duration:
            # Get current pods
            pods = KubernetesClient.get_pods(self.namespace, self.app_label)

            if pods:
                # Kill random pod
                target_pod = random.choice(pods)
                logger.info(f"Randomly terminating pod: {target_pod}")
                KubernetesClient.delete_pod(self.namespace, target_pod)

            # Check health
            health = await self.health_checker.check_health()
            health_checks.append(health)
            logger.info(f"Health check during chaos: {'PASS' if health else 'FAIL'}")

            # Wait before next kill
            await asyncio.sleep(kill_interval)

        # Wait for recovery
        await asyncio.sleep(15)
        KubernetesClient.wait_for_pod_ready(self.namespace, self.app_label)

        # Final health check
        final_health = await self.health_checker.check_health()

        # Test passes if majority of health checks passed and final state is healthy
        success_rate = sum(health_checks) / len(health_checks) if health_checks else 0
        passed = success_rate >= 0.7 and final_health

        logger.info(f"Random Pod Killer Test: Health success rate: {success_rate*100:.1f}%")
        logger.info(f"Random Pod Killer Test: {'PASSED' if passed else 'FAILED'}")

        return passed

    async def test_multiple_pod_termination(self) -> bool:
        """
        Chaos Test: Multiple Pod Termination
        Terminates multiple pods simultaneously
        """
        logger.info("Test: Multiple Pod Termination")

        # Get current pods
        pods = KubernetesClient.get_pods(self.namespace, self.app_label)

        if len(pods) < 2:
            logger.error("Not enough pods for multiple termination test")
            return False

        # Kill half of the pods (but leave at least 1)
        num_to_kill = max(1, len(pods) // 2)
        pods_to_kill = random.sample(pods, num_to_kill)

        logger.info(f"Terminating {num_to_kill} pods simultaneously")

        # Kill pods in parallel
        for pod in pods_to_kill:
            KubernetesClient.delete_pod(self.namespace, pod)

        await asyncio.sleep(2)

        # Check health during termination
        during_health = await self.health_checker.check_health()
        logger.info(f"Health during multiple pod termination: {'PASS' if during_health else 'FAIL'}")

        # Wait for recovery
        recovery_success = KubernetesClient.wait_for_pod_ready(
            self.namespace,
            self.app_label,
            timeout=180
        )

        # Final health check
        final_health = await self.health_checker.check_health()
        logger.info(f"Final health check: {'PASS' if final_health else 'FAIL'}")

        # Verify correct number of pods restored
        final_pods = KubernetesClient.get_pods(self.namespace, self.app_label)
        pods_restored = len(final_pods) >= len(pods)

        passed = recovery_success and final_health and pods_restored

        logger.info(f"Multiple Pod Termination Test: {'PASSED' if passed else 'FAILED'}")
        return passed

    async def test_service_degradation(self) -> bool:
        """
        Chaos Test: Service Degradation
        Reduces the number of replicas and tests behavior under load
        """
        logger.info("Test: Service Degradation")

        # Find deployment name
        deployment_name = f"mlops-sentiment"  # Adjust if different

        # Get current replica count
        original_replicas = KubernetesClient.get_deployment_replicas(
            self.namespace,
            deployment_name
        )

        if not original_replicas or original_replicas < 2:
            logger.error("Need at least 2 replicas for degradation test")
            return False

        logger.info(f"Original replicas: {original_replicas}")

        # Scale down to 1 replica
        logger.info("Scaling down to 1 replica")
        if not KubernetesClient.scale_deployment(self.namespace, deployment_name, 1):
            return False

        # Wait for scaling
        await asyncio.sleep(10)
        KubernetesClient.wait_for_pod_ready(self.namespace, self.app_label)

        # Test health with degraded service
        degraded_health = await self.health_checker.check_health()
        logger.info(f"Health with degraded service: {'PASS' if degraded_health else 'FAIL'}")

        # Test prediction endpoint
        prediction_works = await self.health_checker.check_predict_endpoint()
        logger.info(f"Prediction endpoint: {'PASS' if prediction_works else 'FAIL'}")

        # Restore original replica count
        logger.info(f"Restoring to {original_replicas} replicas")
        if not KubernetesClient.scale_deployment(self.namespace, deployment_name, original_replicas):
            return False

        # Wait for full recovery
        await asyncio.sleep(15)
        KubernetesClient.wait_for_pod_ready(self.namespace, self.app_label)

        # Final health check
        final_health = await self.health_checker.check_health()
        logger.info(f"Final health check: {'PASS' if final_health else 'FAIL'}")

        passed = degraded_health and prediction_works and final_health

        logger.info(f"Service Degradation Test: {'PASSED' if passed else 'FAILED'}")
        return passed

    async def test_rapid_scaling(self) -> bool:
        """
        Chaos Test: Rapid Scaling
        Rapidly scales deployment up and down
        """
        logger.info("Test: Rapid Scaling")

        deployment_name = f"mlops-sentiment"

        # Get current replica count
        original_replicas = KubernetesClient.get_deployment_replicas(
            self.namespace,
            deployment_name
        )

        if not original_replicas:
            logger.error("Could not get current replica count")
            return False

        logger.info(f"Original replicas: {original_replicas}")

        health_checks = []

        # Rapid scaling sequence
        scaling_sequence = [
            (original_replicas * 2, "Scale up 2x"),
            (1, "Scale down to 1"),
            (original_replicas * 3, "Scale up 3x"),
            (original_replicas, "Restore original"),
        ]

        for target_replicas, description in scaling_sequence:
            logger.info(f"Step: {description} (target: {target_replicas})")

            # Scale
            if not KubernetesClient.scale_deployment(self.namespace, deployment_name, target_replicas):
                logger.error(f"Failed to scale: {description}")
                continue

            # Brief wait
            await asyncio.sleep(5)

            # Health check
            health = await self.health_checker.check_health()
            health_checks.append(health)
            logger.info(f"Health during {description}: {'PASS' if health else 'FAIL'}")

        # Wait for final stabilization
        await asyncio.sleep(20)
        KubernetesClient.wait_for_pod_ready(self.namespace, self.app_label, timeout=180)

        # Final health check
        final_health = await self.health_checker.check_health()
        logger.info(f"Final health check: {'PASS' if final_health else 'FAIL'}")

        # Verify final replica count
        final_replicas = KubernetesClient.get_deployment_replicas(self.namespace, deployment_name)
        replicas_correct = final_replicas == original_replicas

        # Test passes if majority of health checks passed and final state is correct
        success_rate = sum(health_checks) / len(health_checks) if health_checks else 0
        passed = success_rate >= 0.75 and final_health and replicas_correct

        logger.info(f"Rapid Scaling Test: Health success rate: {success_rate*100:.1f}%")
        logger.info(f"Rapid Scaling Test: {'PASSED' if passed else 'FAILED'}")

        return passed

    def _generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['status'] == 'passed')
        failed_tests = sum(1 for r in self.results if r['status'] == 'failed')
        error_tests = sum(1 for r in self.results if r['status'] == 'error')

        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "errors": error_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0
            },
            "results": self.results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        return report


async def main():
    parser = argparse.ArgumentParser(description='Chaos Engineering Tests for KubeSentiment')
    parser.add_argument('--namespace', default='default',
                       help='Kubernetes namespace')
    parser.add_argument('--app-label', default='app.kubernetes.io/name=mlops-sentiment',
                       help='App label selector')
    parser.add_argument('--service-name', default='mlops-sentiment',
                       help='Service name')
    parser.add_argument('--output', help='Output file for results (JSON)')

    args = parser.parse_args()

    # Run chaos tests
    chaos = ChaosEngineeringTests(
        namespace=args.namespace,
        app_label=args.app_label,
        service_name=args.service_name
    )

    results = await chaos.run_all_tests()

    # Print results
    print("\n" + "="*80)
    print("CHAOS ENGINEERING TEST RESULTS")
    print("="*80)
    print(json.dumps(results, indent=2))

    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")

    # Exit code based on results
    if results['summary']['success_rate'] >= 80:
        logger.info("Chaos tests PASSED (≥80% success rate)")
        return 0
    else:
        logger.warning(f"Chaos tests FAILED ({results['summary']['success_rate']:.1f}% success rate)")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
