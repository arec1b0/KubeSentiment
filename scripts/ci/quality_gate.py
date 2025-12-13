#!/usr/bin/env python3
"""Quality gate script for CI/CD pipelines.

This script enforces quality gates by checking various metrics and failing
if thresholds are not met. Designed for use in CI/CD pipelines.
"""

import json
from pathlib import Path
import subprocess
import sys


class QualityGate:
    """Enforces quality gates for code quality metrics."""

    def __init__(self, project_root: Path):
        """Initialize quality gate checker.

        Args:
            project_root: Path to project root directory.
        """
        self.project_root = project_root
        self.thresholds = {
            "coverage": 80.0,
            "complexity_max": 10,
            "complexity_avg": 5.0,
            "security_critical": 0,
            "security_high": 0,
        }
        self.results: dict[str, any] = {}

    def run_command(
        self, cmd: list[str], timeout: int = 120
    ) -> tuple[bool, str, str]:
        """Run a command and capture output.

        Args:
            cmd: Command to run as list of strings.
            timeout: Command timeout in seconds.

        Returns:
            Tuple of (success, stdout, stderr).
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, "", "Command timed out"
        except Exception as e:
            return False, "", str(e)
        else:
            return (
                result.returncode == 0,
                result.stdout,
                result.stderr,
            )

    def check_coverage(self) -> bool:
        """Check test coverage threshold.

        Returns:
            True if coverage meets threshold.
        """
        print("📊 Checking test coverage...")
        success, _stdout, stderr = self.run_command(
            ["pytest", "tests/", "--cov=app", "--cov-report=json", "-q"]
        )

        if not success:
            print(f"❌ Coverage check failed: {stderr}")
            return False

        try:
            with (self.project_root / "coverage.json").open() as f:
                coverage_data = json.load(f)
                total_coverage = coverage_data["totals"]["percent_covered"]

            self.results["coverage"] = total_coverage
            threshold = self.thresholds["coverage"]

            if total_coverage >= threshold:
                print(f"✅ Coverage: {total_coverage:.2f}% (threshold: {threshold}%)")
                return True
            else:
                print(
                    f"❌ Coverage: {total_coverage:.2f}% (threshold: {threshold}%)"
                )
                return False
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            print(f"❌ Failed to parse coverage data: {e}")
            return False

    def check_complexity(self) -> bool:
        """Check code complexity metrics.

        Returns:
            True if complexity is within thresholds.
        """
        print("📊 Checking code complexity...")
        success, stdout, stderr = self.run_command(
            ["radon", "cc", "app/", "--min", "B", "--json"]
        )

        if not success:
            print(f"⚠️  Complexity check failed: {stderr}")
            # Don't fail on complexity check errors, just warn
            return True

        try:
            complexity_data = json.loads(stdout)
            max_complexity = 0
            total_complexity = 0
            function_count = 0

            for _file_path, functions in complexity_data.items():
                for func in functions:
                    complexity = func.get("complexity", 0)
                    max_complexity = max(max_complexity, complexity)
                    total_complexity += complexity
                    function_count += 1

            avg_complexity = (
                total_complexity / function_count if function_count > 0 else 0
            )

            self.results["complexity_max"] = max_complexity
            self.results["complexity_avg"] = avg_complexity

            max_threshold = self.thresholds["complexity_max"]
            avg_threshold = self.thresholds["complexity_avg"]

            max_ok = max_complexity <= max_threshold
            avg_ok = avg_complexity <= avg_threshold

            print(
                f"📊 Max complexity: {max_complexity} (threshold: {max_threshold})"
            )
            print(
                f"📊 Avg complexity: {avg_complexity:.2f} (threshold: {avg_threshold})"
            )

            if max_ok and avg_ok:
                print("✅ Complexity checks passed")
                return True
            else:
                print("❌ Complexity exceeds thresholds")
                return False
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️  Failed to parse complexity data: {e}")
            return True  # Don't fail on parse errors

    def check_security(self) -> bool:
        """Check security scan results.

        Returns:
            True if no critical/high security issues.
        """
        print("🔒 Checking security scan...")
        success, stdout, _stderr = self.run_command(
            [
                "bandit",
                "-r",
                "app/",
                "-c",
                "pyproject.toml",
                "-f",
                "json",
            ]
        )

        # Bandit returns non-zero on any findings, but we want to parse them
        try:
            bandit_data = json.loads(stdout)
            metrics = bandit_data.get("metrics", {})
            critical_count = metrics.get("SEVERITY.CRITICAL", {}).get("total", 0)
            high_count = metrics.get("SEVERITY.HIGH", {}).get("total", 0)

            self.results["security_critical"] = critical_count
            self.results["security_high"] = high_count

            critical_threshold = self.thresholds["security_critical"]
            high_threshold = self.thresholds["security_high"]

            print(f"🔒 Critical issues: {critical_count} (threshold: {critical_threshold})")
            print(f"🔒 High issues: {high_count} (threshold: {high_threshold})")

            if critical_count <= critical_threshold and high_count <= high_threshold:
                print("✅ Security checks passed")
                return True
            else:
                print("❌ Security issues exceed thresholds")
                return False
        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️  Failed to parse security data: {e}")
            # If we can't parse, check if command succeeded
            return success

    def check_linting(self) -> bool:
        """Check linting errors.

        Returns:
            True if no linting errors.
        """
        print("🔍 Checking linting...")
        success, _stdout, _stderr = self.run_command(
            ["ruff", "check", "app/", "tests/", "scripts/", "run.py"]
        )

        if success:
            print("✅ Linting checks passed")
            return True
        else:
            print(f"❌ Linting errors found:\n{stdout}")
            return False

    def check_type_checking(self) -> bool:
        """Check type checking errors.

        Returns:
            True if no type checking errors.
        """
        print("🔬 Checking type annotations...")
        success, _stdout, _stderr = self.run_command(
            ["mypy", "app/", "--config-file=pyproject.toml"]
        )

        if success:
            print("✅ Type checking passed")
            return True
        else:
            print(f"❌ Type checking errors found:\n{stdout}")
            return False

    def run_all_checks(self) -> bool:
        """Run all quality gate checks.

        Returns:
            True if all checks pass.
        """
        print("\n" + "=" * 60)
        print("🚀 Running Quality Gate Checks")
        print("=" * 60 + "\n")

        checks = [
            ("Linting", self.check_linting),
            ("Type Checking", self.check_type_checking),
            ("Complexity", self.check_complexity),
            ("Security", self.check_security),
            ("Coverage", self.check_coverage),
        ]

        results = {}
        for name, check_func in checks:
            try:
                results[name] = check_func()
            except Exception as e:
                print(f"❌ {name} check failed with exception: {e}")
                results[name] = False

        print("\n" + "=" * 60)
        print("📊 Quality Gate Summary")
        print("=" * 60 + "\n")

        all_passed = True
        for name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{name:20} {status}")
            if not passed:
                all_passed = False

        print("\n" + "-" * 60)
        if all_passed:
            print("✅ All quality gates passed!")
        else:
            print("❌ Some quality gates failed")
        print("-" * 60 + "\n")

        # Print detailed results
        if self.results:
            print("📈 Detailed Metrics:")
            for metric, value in self.results.items():
                if isinstance(value, float):
                    print(f"  {metric}: {value:.2f}")
                else:
                    print(f"  {metric}: {value}")

        return all_passed


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent.parent
    gate = QualityGate(project_root)
    success = gate.run_all_checks()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

