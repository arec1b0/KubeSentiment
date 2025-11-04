#!/usr/bin/env python3
"""
Comprehensive Chaos Engineering Test Suite

Runs a series of chaos experiments and generates a detailed report.
"""

import argparse
import asyncio
import json
import logging
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ExperimentStatus(str, Enum):
    """Status of a chaos experiment"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Severity(str, Enum):
    """Severity level of chaos experiment"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ExperimentResult:
    """Result of a chaos experiment"""

    name: str
    status: ExperimentStatus
    severity: Severity
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    pods_before: int = 0
    pods_after: int = 0
    recovery_time_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    observations: List[str] = field(default_factory=list)
    # HPA-specific fields
    hpa_min_replicas: Optional[int] = None
    hpa_max_replicas: Optional[int] = None
    hpa_replicas_before: Optional[int] = None
    hpa_replicas_during: Optional[int] = None
    hpa_replicas_after: Optional[int] = None
    hpa_scale_up_time: Optional[float] = None
    hpa_scale_down_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        d = asdict(self)
        if self.start_time:
            d["start_time"] = self.start_time.isoformat()
        if self.end_time:
            d["end_time"] = self.end_time.isoformat()
        return d


@dataclass
class ChaosExperiment:
    """Definition of a chaos experiment"""

    name: str
    description: str
    manifest_path: str
    duration_seconds: int
    severity: Severity
    expected_behavior: List[str]
    resource_type: str = "podchaos"


class ChaosTestSuite:
    """Orchestrates chaos engineering tests"""

    def __init__(self, namespace: str = "default", dry_run: bool = False):
        self.namespace = namespace
        self.dry_run = dry_run
        self.results: List[ExperimentResult] = []

    def check_prerequisites(self) -> tuple[bool, List[str]]:
        """Check prerequisites for running chaos experiments"""
        errors = []

        # Check kubectl
        returncode, _, stderr = self.run_kubectl_command(["kubectl", "version", "--client"])
        if returncode != 0:
            errors.append(f"kubectl not available: {stderr}")

        # Check cluster connectivity
        returncode, _, stderr = self.run_kubectl_command(["kubectl", "cluster-info"])
        if returncode != 0:
            errors.append(f"Cannot connect to Kubernetes cluster: {stderr}")

        # Check if service deployment exists
        cmd = [
            "kubectl",
            "get",
            "deployment",
            "-n",
            self.namespace,
            "-l",
            "app.kubernetes.io/name=mlops-sentiment",
            "--no-headers",
        ]
        returncode, stdout, stderr = self.run_kubectl_command(cmd)
        if returncode != 0 or not stdout.strip():
            errors.append(f"mlops-sentiment deployment not found in namespace {self.namespace}")

        # Check Chaos Mesh installation
        cmd = ["kubectl", "get", "crd", "podchaos.chaos-mesh.org"]
        returncode, _, _ = self.run_kubectl_command(cmd)
        if returncode != 0:
            errors.append("Chaos Mesh not installed (podchaos CRD not found)")

        # Check if at least one pod is healthy
        if not self.check_pod_health():
            errors.append(
                f"No healthy pods found for mlops-sentiment in namespace {self.namespace}"
            )

        return len(errors) == 0, errors

    def check_hpa_prerequisites(self) -> tuple[bool, List[str]]:
        """Check prerequisites specifically for HPA experiments"""
        errors = []

        # Check if HPA exists
        hpa_name = self.find_hpa_name()
        if not hpa_name:
            errors.append(
                f"HPA not found for mlops-sentiment deployment in namespace {self.namespace}"
            )
        else:
            # Check HPA status
            hpa_status = self.get_hpa_status()
            if not hpa_status:
                errors.append(f"Could not retrieve HPA status for {hpa_name}")
            else:
                min_replicas = hpa_status.get("min_replicas")
                max_replicas = hpa_status.get("max_replicas")
                if min_replicas is None or max_replicas is None:
                    errors.append(
                        f"HPA {hpa_name} has invalid configuration (min: {min_replicas}, max: {max_replicas})"
                    )

        # Check metrics-server (required for HPA)
        cmd = [
            "kubectl",
            "get",
            "deployment",
            "metrics-server",
            "-n",
            "kube-system",
            "--no-headers",
        ]
        returncode, _, _ = self.run_kubectl_command(cmd)
        if returncode != 0:
            errors.append("Metrics-server not found (required for HPA)")

        return len(errors) == 0, errors

    def run_kubectl_command(self, command: List[str]) -> tuple[int, str, str]:
        """Run a kubectl command"""
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except Exception as e:
            return 1, "", str(e)

    def get_pod_count(self) -> int:
        """Get current number of sentiment pods"""
        cmd = [
            "kubectl",
            "get",
            "pods",
            "-n",
            self.namespace,
            "-l",
            "app.kubernetes.io/name=mlops-sentiment",
            "--no-headers",
        ]
        returncode, stdout, stderr = self.run_kubectl_command(cmd)
        if returncode == 0:
            return len(stdout.strip().split("\n")) if stdout.strip() else 0
        return 0

    def check_pod_health(self) -> bool:
        """Check if at least one pod is healthy"""
        cmd = [
            "kubectl",
            "get",
            "pods",
            "-n",
            self.namespace,
            "-l",
            "app.kubernetes.io/name=mlops-sentiment",
            "-o",
            "jsonpath={.items[?(@.status.phase=='Running')].metadata.name}",
        ]
        returncode, stdout, stderr = self.run_kubectl_command(cmd)
        return returncode == 0 and bool(stdout.strip())

    def apply_chaos(self, manifest_path: str) -> bool:
        """Apply a chaos experiment"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would apply: {manifest_path}")
            return True

        cmd = ["kubectl", "apply", "-f", manifest_path, "-n", self.namespace]
        returncode, stdout, stderr = self.run_kubectl_command(cmd)

        if returncode == 0:
            logger.info(f"Applied chaos: {manifest_path}")
            return True
        else:
            logger.error(f"Failed to apply chaos: {stderr}")
            return False

    def cleanup_chaos(self, resource_type: str) -> bool:
        """Clean up chaos experiments"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would cleanup: {resource_type}")
            return True

        cmd = ["kubectl", "delete", resource_type, "--all", "-n", self.namespace]
        returncode, stdout, stderr = self.run_kubectl_command(cmd)
        return returncode == 0

    def wait_for_recovery(self, timeout: int = 300) -> float:
        """Wait for system to recover and return recovery time"""
        start = time.time()
        check_interval = 5

        while time.time() - start < timeout:
            if self.check_pod_health():
                recovery_time = time.time() - start
                logger.info(f"System recovered in {recovery_time:.2f}s")
                return recovery_time

            time.sleep(check_interval)

        logger.warning(f"Recovery timeout after {timeout}s")
        return timeout

    def find_hpa_name(self) -> Optional[str]:
        """Find HPA name for mlops-sentiment deployment"""
        # Try to find HPA by label selector matching the deployment
        cmd = [
            "kubectl",
            "get",
            "hpa",
            "-n",
            self.namespace,
            "-l",
            "app.kubernetes.io/name=mlops-sentiment",
            "-o",
            "jsonpath={.items[0].metadata.name}",
        ]
        returncode, stdout, _ = self.run_kubectl_command(cmd)
        if returncode == 0 and stdout.strip():
            return stdout.strip()

        # Fallback: try to find HPA that targets deployment with mlops-sentiment label
        cmd = [
            "kubectl",
            "get",
            "hpa",
            "-n",
            self.namespace,
            "-o",
            "jsonpath={.items[?(@.spec.scaleTargetRef.name=~'.*mlops-sentiment.*')].metadata.name}",
        ]
        returncode, stdout, _ = self.run_kubectl_command(cmd)
        if returncode == 0 and stdout.strip():
            return stdout.strip().split()[0] if stdout.strip() else None

        return None

    def get_hpa_status(self) -> Optional[Dict[str, Any]]:
        """Get HPA status including current and desired replicas"""
        hpa_name = self.find_hpa_name()
        if not hpa_name:
            return None

        cmd = ["kubectl", "get", "hpa", hpa_name, "-n", self.namespace, "-o", "json"]
        returncode, stdout, stderr = self.run_kubectl_command(cmd)
        if returncode != 0:
            logger.warning(f"Failed to get HPA status: {stderr}")
            return None

        try:
            hpa_data = json.loads(stdout)
            return {
                "name": hpa_name,
                "current_replicas": hpa_data.get("status", {}).get("currentReplicas", 0),
                "desired_replicas": hpa_data.get("status", {}).get("desiredReplicas", 0),
                "min_replicas": hpa_data.get("spec", {}).get("minReplicas", 0),
                "max_replicas": hpa_data.get("spec", {}).get("maxReplicas", 0),
                "current_cpu_utilization": (
                    hpa_data.get("status", {})
                    .get("currentMetrics", [{}])[0]
                    .get("resource", {})
                    .get("current", {})
                    .get("averageUtilization", 0)
                    if hpa_data.get("status", {}).get("currentMetrics")
                    else None
                ),
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse HPA status: {e}")
            return None

    def get_hpa_replicas(self) -> Optional[int]:
        """Get current HPA replica count"""
        hpa_status = self.get_hpa_status()
        return hpa_status.get("current_replicas") if hpa_status else None

    async def run_hpa_experiment(self, experiment: ChaosExperiment) -> ExperimentResult:
        """Run HPA-specific chaos experiment with detailed HPA monitoring"""
        result = ExperimentResult(
            name=experiment.name, status=ExperimentStatus.PENDING, severity=experiment.severity
        )

        logger.info(f"\n{'='*60}")
        logger.info(f"Starting HPA experiment: {experiment.name}")
        logger.info(f"Description: {experiment.description}")
        logger.info(f"Severity: {experiment.severity.value}")
        logger.info(f"Duration: {experiment.duration_seconds}s")
        logger.info(f"{'='*60}\n")

        try:
            # Get HPA status before experiment
            hpa_status_before = self.get_hpa_status()
            if not hpa_status_before:
                result.status = ExperimentStatus.FAILED
                result.errors.append("HPA not found for mlops-sentiment deployment")
                return result

            result.hpa_min_replicas = hpa_status_before.get("min_replicas")
            result.hpa_max_replicas = hpa_status_before.get("max_replicas")
            result.hpa_replicas_before = hpa_status_before.get("current_replicas")
            result.pods_before = self.get_pod_count()

            logger.info(f"HPA Status Before:")
            logger.info(f"  Min Replicas: {result.hpa_min_replicas}")
            logger.info(f"  Max Replicas: {result.hpa_max_replicas}")
            logger.info(f"  Current Replicas: {result.hpa_replicas_before}")
            logger.info(f"  Pods: {result.pods_before}")

            # Check if manifest exists
            if not Path(experiment.manifest_path).exists():
                result.status = ExperimentStatus.FAILED
                result.errors.append(f"Manifest not found: {experiment.manifest_path}")
                return result

            # Apply chaos
            result.start_time = datetime.now()
            result.status = ExperimentStatus.RUNNING

            if not self.apply_chaos(experiment.manifest_path):
                result.status = ExperimentStatus.FAILED
                result.errors.append("Failed to apply chaos manifest")
                return result

            # Monitor HPA during experiment (poll every 15 seconds)
            logger.info(f"Monitoring HPA scaling behavior for {experiment.duration_seconds}s...")
            poll_interval = 15
            poll_count = experiment.duration_seconds // poll_interval
            peak_replicas = result.hpa_replicas_before
            scale_up_start = None
            scale_up_complete = None

            for i in range(poll_count):
                await asyncio.sleep(poll_interval)

                hpa_status = self.get_hpa_status()
                if hpa_status:
                    current_replicas = hpa_status.get("current_replicas", 0)
                    cpu_util = hpa_status.get("current_cpu_utilization")

                    logger.info(
                        f"  [{i+1}/{poll_count}] HPA: {current_replicas} replicas"
                        + (f", CPU: {cpu_util}%" if cpu_util else "")
                    )

                    # Track peak replicas
                    if current_replicas > peak_replicas:
                        peak_replicas = current_replicas
                        if scale_up_start is None:
                            scale_up_start = time.time()

                    # Check if we've reached max replicas
                    if current_replicas >= result.hpa_max_replicas and scale_up_complete is None:
                        scale_up_complete = time.time()
                        logger.info(f"  HPA reached max replicas ({result.hpa_max_replicas})")

            result.hpa_replicas_during = peak_replicas

            if scale_up_start and scale_up_complete:
                result.hpa_scale_up_time = scale_up_complete - scale_up_start
                result.observations.append(
                    f"HPA scaled up to {peak_replicas} replicas in {result.hpa_scale_up_time:.1f}s"
                )

            # Cleanup chaos
            logger.info("Cleaning up chaos experiment...")
            self.cleanup_chaos("stresschaos")

            # Monitor scale-down after chaos ends
            logger.info("Monitoring HPA scale-down behavior...")
            scale_down_start = time.time()
            scale_down_complete = None
            scale_down_timeout = 600  # 10 minutes max for scale-down

            while time.time() - scale_down_start < scale_down_timeout:
                await asyncio.sleep(15)

                hpa_status = self.get_hpa_status()
                if hpa_status:
                    current_replicas = hpa_status.get("current_replicas", 0)
                    logger.info(f"  HPA scale-down: {current_replicas} replicas")

                    # Check if we've reached min replicas
                    if current_replicas <= result.hpa_min_replicas:
                        scale_down_complete = time.time()
                        result.hpa_scale_down_time = scale_down_complete - scale_down_start
                        logger.info(
                            f"  HPA scaled down to min replicas ({result.hpa_min_replicas}) in {result.hpa_scale_down_time:.1f}s"
                        )
                        break

            # Get final metrics
            hpa_status_after = self.get_hpa_status()
            if hpa_status_after:
                result.hpa_replicas_after = hpa_status_after.get("current_replicas")

            result.pods_after = self.get_pod_count()
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()

            # Validate HPA behavior
            validation_errors = []

            if result.hpa_replicas_during and result.hpa_replicas_during < result.hpa_min_replicas:
                validation_errors.append(
                    f"HPA did not scale up (stayed at {result.hpa_replicas_during} replicas)"
                )

            if result.hpa_replicas_after and result.hpa_replicas_after > result.hpa_min_replicas:
                result.observations.append(
                    f"HPA has not fully scaled down (currently {result.hpa_replicas_after} replicas, min: {result.hpa_min_replicas})"
                )

            if result.hpa_replicas_during and result.hpa_replicas_during >= result.hpa_max_replicas:
                result.observations.append(
                    f"HPA successfully scaled to max replicas ({result.hpa_max_replicas})"
                )

            if result.hpa_scale_up_time and result.hpa_scale_up_time > 120:
                result.observations.append(f"Slow scale-up time: {result.hpa_scale_up_time:.1f}s")

            if result.hpa_scale_down_time and result.hpa_scale_down_time > 600:
                result.observations.append(
                    f"Slow scale-down time: {result.hpa_scale_down_time:.1f}s"
                )

            # Validate recovery
            if result.pods_after >= result.hpa_min_replicas and self.check_pod_health():
                if validation_errors:
                    result.status = ExperimentStatus.COMPLETED
                    result.errors.extend(validation_errors)
                else:
                    result.status = ExperimentStatus.COMPLETED
                    result.observations.append("HPA behavior validated successfully")
            else:
                result.status = ExperimentStatus.FAILED
                result.errors.append("System did not recover properly")
                result.errors.extend(validation_errors)

        except Exception as e:
            logger.error(f"Experiment failed with exception: {e}", exc_info=True)
            result.status = ExperimentStatus.FAILED
            result.errors.append(str(e))
            result.end_time = datetime.now()

        logger.info(f"\nExperiment {experiment.name} status: {result.status.value}\n")
        self.results.append(result)
        return result

    async def run_experiment(self, experiment: ChaosExperiment) -> ExperimentResult:
        """Run a single chaos experiment"""
        result = ExperimentResult(
            name=experiment.name, status=ExperimentStatus.PENDING, severity=experiment.severity
        )

        logger.info(f"\n{'='*60}")
        logger.info(f"Starting experiment: {experiment.name}")
        logger.info(f"Description: {experiment.description}")
        logger.info(f"Severity: {experiment.severity.value}")
        logger.info(f"Duration: {experiment.duration_seconds}s")
        logger.info(f"{'='*60}\n")

        try:
            # Get baseline metrics
            result.pods_before = self.get_pod_count()
            logger.info(f"Pods before experiment: {result.pods_before}")

            # Check if manifest exists
            if not Path(experiment.manifest_path).exists():
                result.status = ExperimentStatus.FAILED
                result.errors.append(f"Manifest not found: {experiment.manifest_path}")
                return result

            # Apply chaos
            result.start_time = datetime.now()
            result.status = ExperimentStatus.RUNNING

            if not self.apply_chaos(experiment.manifest_path):
                result.status = ExperimentStatus.FAILED
                result.errors.append("Failed to apply chaos manifest")
                return result

            # Monitor experiment
            logger.info(f"Monitoring for {experiment.duration_seconds}s...")

            if not self.dry_run:
                await asyncio.sleep(experiment.duration_seconds)

            # Cleanup chaos
            logger.info("Cleaning up chaos experiment...")
            # Cleanup multiple resource types for network chaos
            if experiment.resource_type == "networkchaos":
                self.cleanup_chaos("networkchaos")
            elif experiment.resource_type == "stresschaos":
                self.cleanup_chaos("stresschaos")
            else:
                self.cleanup_chaos(experiment.resource_type)

            # Wait for recovery
            logger.info("Waiting for system recovery...")
            result.recovery_time_seconds = self.wait_for_recovery()

            # Get post-experiment metrics
            result.pods_after = self.get_pod_count()
            result.end_time = datetime.now()
            result.duration_seconds = (result.end_time - result.start_time).total_seconds()

            # Validate recovery
            if result.pods_after >= 1 and self.check_pod_health():
                result.status = ExperimentStatus.COMPLETED
                result.observations.append("System recovered successfully")
            else:
                result.status = ExperimentStatus.FAILED
                result.errors.append("System did not recover properly")

            # Add observations
            if result.pods_before != result.pods_after:
                result.observations.append(
                    f"Pod count changed: {result.pods_before} → {result.pods_after}"
                )

            if result.recovery_time_seconds < 30:
                result.observations.append("Fast recovery (<30s)")
            elif result.recovery_time_seconds < 120:
                result.observations.append("Normal recovery (<2m)")
            else:
                result.observations.append("Slow recovery (>2m)")

        except Exception as e:
            logger.error(f"Experiment failed with exception: {e}", exc_info=True)
            result.status = ExperimentStatus.FAILED
            result.errors.append(str(e))
            result.end_time = datetime.now()

        logger.info(f"\nExperiment {experiment.name} status: {result.status.value}\n")
        self.results.append(result)
        return result

    def generate_report(self, output_path: str = "chaos_report.json"):
        """Generate comprehensive test report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "namespace": self.namespace,
            "summary": {
                "total_experiments": len(self.results),
                "completed": sum(1 for r in self.results if r.status == ExperimentStatus.COMPLETED),
                "failed": sum(1 for r in self.results if r.status == ExperimentStatus.FAILED),
                "skipped": sum(1 for r in self.results if r.status == ExperimentStatus.SKIPPED),
            },
            "experiments": [r.to_dict() for r in self.results],
        }

        # Write JSON report
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        # Write text report
        text_report = output_path.replace(".json", ".txt")
        with open(text_report, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("CHAOS ENGINEERING TEST REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Generated: {report['generated_at']}\n")
            f.write(f"Namespace: {report['namespace']}\n\n")

            f.write("SUMMARY\n")
            f.write("-" * 80 + "\n")
            for key, value in report["summary"].items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            f.write("\n")

            f.write("EXPERIMENT RESULTS\n")
            f.write("-" * 80 + "\n\n")

            for result in self.results:
                f.write(f"Experiment: {result.name}\n")
                f.write(f"Status: {result.status.value}\n")
                f.write(f"Severity: {result.severity.value}\n")
                f.write(f"Duration: {result.duration_seconds:.2f}s\n")
                f.write(f"Recovery Time: {result.recovery_time_seconds:.2f}s\n")
                f.write(f"Pods: {result.pods_before} → {result.pods_after}\n")

                # Add HPA-specific metrics if available
                if result.hpa_replicas_before is not None:
                    f.write(
                        f"HPA Replicas: {result.hpa_replicas_before} → {result.hpa_replicas_during or 'N/A'} → {result.hpa_replicas_after or 'N/A'}\n"
                    )
                    if result.hpa_min_replicas:
                        f.write(
                            f"HPA Range: {result.hpa_min_replicas} - {result.hpa_max_replicas}\n"
                        )
                    if result.hpa_scale_up_time:
                        f.write(f"HPA Scale-Up Time: {result.hpa_scale_up_time:.2f}s\n")
                    if result.hpa_scale_down_time:
                        f.write(f"HPA Scale-Down Time: {result.hpa_scale_down_time:.2f}s\n")

                if result.observations:
                    f.write("Observations:\n")
                    for obs in result.observations:
                        f.write(f"  - {obs}\n")

                if result.errors:
                    f.write("Errors:\n")
                    for err in result.errors:
                        f.write(f"  - {err}\n")

                f.write("\n" + "-" * 80 + "\n\n")

        logger.info(f"Report generated: {output_path}")
        logger.info(f"Text report: {text_report}")

        return report


async def main():
    parser = argparse.ArgumentParser(description="Run chaos engineering test suite")
    parser.add_argument("--namespace", default="default", help="Kubernetes namespace")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--output", default="chaos_report.json", help="Output report file")
    parser.add_argument("--experiments", nargs="+", help="Specific experiments to run")
    parser.add_argument("--skip-prereq-check", action="store_true", help="Skip prerequisite checks")
    args = parser.parse_args()

    # Define experiments
    all_experiments = [
        ChaosExperiment(
            name="pod-kill-basic",
            description="Kill a single pod to test recovery",
            manifest_path="chaos/chaos-mesh/01-pod-kill.yaml",
            duration_seconds=60,
            severity=Severity.LOW,
            expected_behavior=[
                "Pod is recreated automatically",
                "Service remains available",
                "No data loss",
            ],
        ),
        ChaosExperiment(
            name="pod-kill-multiple",
            description="Kill multiple pods simultaneously to test resilience",
            manifest_path="chaos/chaos-mesh/01-pod-kill.yaml",
            duration_seconds=90,
            severity=Severity.MEDIUM,
            expected_behavior=[
                "All pods are recreated automatically",
                "Service remains available throughout",
                "HPA maintains desired replica count",
                "Recovery time < 2 minutes",
            ],
        ),
        ChaosExperiment(
            name="network-partition-redis",
            description="Partition network connection to Redis to test graceful degradation",
            manifest_path="chaos/chaos-mesh/02-network-chaos.yaml",
            duration_seconds=120,
            severity=Severity.MEDIUM,
            resource_type="networkchaos",
            expected_behavior=[
                "Service continues to operate without cache",
                "Fallback to non-cached operation",
                "No complete service outage",
                "Graceful degradation observed",
            ],
        ),
        ChaosExperiment(
            name="network-partition-pods",
            description="Partition network between pods to test inter-pod communication resilience",
            manifest_path="chaos/chaos-mesh/02-network-chaos.yaml",
            duration_seconds=90,
            severity=Severity.HIGH,
            resource_type="networkchaos",
            expected_behavior=[
                "Individual pods remain functional",
                "Service remains available via remaining pods",
                "No request failures",
                "Load balancing adapts",
            ],
        ),
        ChaosExperiment(
            name="network-delay",
            description="Add network latency to test performance degradation",
            manifest_path="chaos/chaos-mesh/02-network-chaos.yaml",
            duration_seconds=120,
            severity=Severity.MEDIUM,
            resource_type="networkchaos",
            expected_behavior=[
                "Increased response times",
                "No request failures",
                "Graceful degradation",
            ],
        ),
        ChaosExperiment(
            name="cpu-stress",
            description="Stress CPU to test HPA and performance",
            manifest_path="chaos/chaos-mesh/03-stress-chaos.yaml",
            duration_seconds=180,
            severity=Severity.MEDIUM,
            resource_type="stresschaos",
            expected_behavior=[
                "HPA triggers scale-up",
                "Service remains responsive",
                "No pod evictions",
            ],
        ),
        ChaosExperiment(
            name="hpa-stress-test",
            description="Test HPA scaling behavior under CPU stress - validates scale-up to maxReplicas and scale-down to minReplicas",
            manifest_path="chaos/chaos-mesh/04-hpa-stress-chaos.yaml",
            duration_seconds=300,  # 5 minutes active stress
            severity=Severity.HIGH,
            resource_type="stresschaos",
            expected_behavior=[
                "HPA scales up to maxReplicas when CPU > 70%",
                "Service remains available during scaling",
                "HPA scales down to minReplicas after stress ends",
                "Scaling completes within HPA behavior windows",
                "Scale-up completes within 60-90 seconds",
                "Scale-down completes within 5 minutes",
            ],
        ),
    ]

    # Filter experiments if specified
    if args.experiments:
        experiments = [e for e in all_experiments if e.name in args.experiments]
    else:
        experiments = all_experiments

    # Run test suite
    suite = ChaosTestSuite(namespace=args.namespace, dry_run=args.dry_run)

    logger.info(f"\n{'='*80}")
    logger.info("CHAOS ENGINEERING TEST SUITE")
    logger.info(f"{'='*80}\n")
    logger.info(f"Namespace: {args.namespace}")
    logger.info(f"Experiments: {len(experiments)}")
    logger.info(f"Dry Run: {args.dry_run}\n")

    # Check prerequisites
    if not args.skip_prereq_check:
        logger.info("Checking prerequisites...")
        prereq_ok, errors = suite.check_prerequisites()
        if not prereq_ok:
            logger.error("Prerequisites check failed:")
            for error in errors:
                logger.error(f"  - {error}")
            logger.error("\nPlease fix the issues above before running chaos experiments.")
            logger.error("You can skip this check with --skip-prereq-check (not recommended)")
            return 1

        # Check HPA prerequisites if running HPA test
        if any(e.name == "hpa-stress-test" for e in experiments):
            logger.info("Checking HPA prerequisites...")
            hpa_prereq_ok, hpa_errors = suite.check_hpa_prerequisites()
            if not hpa_prereq_ok:
                logger.error("HPA prerequisites check failed:")
                for error in hpa_errors:
                    logger.error(f"  - {error}")
                logger.error("\nPlease fix the issues above before running HPA chaos experiments.")
                return 1

        logger.info("Prerequisites check passed\n")

    for experiment in experiments:
        # Use specialized HPA experiment runner for HPA tests
        if experiment.name == "hpa-stress-test":
            await suite.run_hpa_experiment(experiment)
        else:
            await suite.run_experiment(experiment)
        # Wait between experiments
        if not args.dry_run:
            logger.info("Waiting 30s before next experiment...\n")
            await asyncio.sleep(30)

    # Generate report
    suite.generate_report(args.output)

    # Print summary
    logger.info(f"\n{'='*80}")
    logger.info("TEST SUITE COMPLETED")
    logger.info(f"{'='*80}\n")

    summary = {
        "Total": len(suite.results),
        "Completed": sum(1 for r in suite.results if r.status == ExperimentStatus.COMPLETED),
        "Failed": sum(1 for r in suite.results if r.status == ExperimentStatus.FAILED),
    }

    for key, value in summary.items():
        logger.info(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
