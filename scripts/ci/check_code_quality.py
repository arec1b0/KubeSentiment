#!/usr/bin/env python3
"""A script for running a suite of code quality checks.

This script automates the process of checking code quality by running several
linters and formatters, including Black, isort, Ruff, mypy, Radon, and Bandit.
It then generates a consolidated report of the results and suggests commands
for fixing any issues that were found.
"""

from pathlib import Path
import subprocess
import sys


class CodeQualityChecker:
    """Encapsulates the logic for running code quality checks.

    This class provides methods for running various code quality tools,
    collecting their results, and presenting them in a summary report.

    Attributes:
        project_root: The root directory of the project.
        results: A dictionary to store the results of the checks.
    """

    def __init__(self, project_root: Path):
        """Initializes the `CodeQualityChecker`.

        Args:
            project_root: The path to the project's root directory.
        """
        self.project_root = project_root
        self.results: dict[str, dict] = {}

    def run_command(self, cmd: list[str]) -> tuple[bool, str]:
        """Executes a command-line tool and captures its output.

        Args:
            cmd: A list of strings representing the command to be executed.

        Returns:
            A tuple containing a boolean indicating success and a string with
            the command's output.
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
        else:
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output

    def check_black(self) -> None:
        """Checks code formatting using the Black tool."""
        print("🎨 Checking Black formatting...", end=" ")
        success, output = self.run_command(
            ["black", "--check", "app/", "tests/", "scripts/", "run.py"]
        )
        self.results["black"] = {"success": success, "output": output}
        print("✅" if success else "❌")

    def check_isort(self) -> None:
        """Checks import sorting using the isort tool."""
        print("📦 Checking isort...", end=" ")
        success, output = self.run_command(
            ["isort", "--check-only", "app/", "tests/", "scripts/", "run.py"]
        )
        self.results["isort"] = {"success": success, "output": output}
        print("✅" if success else "❌")

    def check_ruff(self) -> None:
        """Checks for style guide enforcement using the Ruff linter."""
        print("🔎 Checking Ruff...", end=" ")
        success, output = self.run_command(
            ["ruff", "check", "app/", "tests/", "scripts/", "run.py"]
        )
        self.results["ruff"] = {"success": success, "output": output}
        print("✅" if success else "❌")

    def check_complexity(self) -> None:
        """Checks code complexity using Radon."""
        print("📊 Checking code complexity...", end=" ")
        success, output = self.run_command(
            ["radon", "cc", "app/", "--min", "B", "--show-complexity"]
        )
        self.results["complexity"] = {"success": success, "output": output}
        print("✅" if success else "❌")

    def check_mypy(self) -> None:
        """Performs static type checking using the mypy tool."""
        print("🔬 Checking mypy...", end=" ")
        success, output = self.run_command(["mypy", "app/", "--config-file=pyproject.toml"])
        self.results["mypy"] = {"success": success, "output": output}
        print("✅" if success else "❌")

    def check_bandit(self) -> None:
        """Performs security analysis using the Bandit tool."""
        print("🔒 Checking Bandit security...", end=" ")
        success, output = self.run_command(["bandit", "-r", "app/", "-c", "pyproject.toml"])
        self.results["bandit"] = {"success": success, "output": output}
        print("✅" if success else "❌")

    def run_all_checks(self) -> bool:
        """Runs all configured code quality checks.

        Returns:
            `True` if all checks pass, `False` otherwise.
        """
        print("\n" + "=" * 60)
        print("🚀 Running Code Quality Checks")
        print("=" * 60 + "\n")

        self.check_black()
        self.check_isort()
        self.check_ruff()
        self.check_mypy()
        self.check_complexity()
        self.check_bandit()

        return all(result["success"] for result in self.results.values())

    def print_summary(self) -> None:
        """Prints a summary of the results of all checks."""
        print("\n" + "=" * 60)
        print("📊 Summary")
        print("=" * 60 + "\n")

        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r["success"])

        for tool, result in self.results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{tool:15} {status}")

        print("\n" + "-" * 60)
        print(f"Total: {passed}/{total} checks passed")
        print("-" * 60 + "\n")

        if passed < total:
            print("❌ Some checks failed. Details below:\n")
            for tool, result in self.results.items():
                if not result["success"]:
                    print(f"\n{'=' * 60}")
                    print(f"❌ {tool.upper()} ERRORS:")
                    print("=" * 60)
                    print(result["output"])

    def suggest_fixes(self) -> None:
        """Provides suggestions for fixing any failed checks."""
        failed = [tool for tool, r in self.results.items() if not r["success"]]

        if not failed:
            print("🎉 All checks passed! Great job!")
            return

        print("\n" + "=" * 60)
        print("💡 Suggested Fixes")
        print("=" * 60 + "\n")

        if "black" in failed or "isort" in failed:
            print("📝 To auto-fix formatting and imports:")
            print("   make format")
            print("   # or")
            print("   make lint-fix\n")

        if "ruff" in failed:
            print("🔧 To fix Ruff linting issues:")
            print("   1. Auto-fix issues: ruff check --fix app/ tests/")
            print("   2. Or run: make lint-fix")
            print("   3. Review remaining issues manually\n")

        if "complexity" in failed:
            print("📊 To fix complexity issues:")
            print("   1. Review complexity report above")
            print("   2. Refactor functions with complexity > 10")
            print("   3. Extract complex logic into smaller functions\n")

        if "mypy" in failed:
            print("🔬 To fix mypy type errors:")
            print("   1. Add type hints to functions")
            print("   2. Fix type mismatches")
            print("   3. Use # type: ignore for unavoidable issues\n")

        if "bandit" in failed:
            print("🔒 To fix security issues:")
            print("   1. Review security warnings carefully")
            print("   2. Fix high-severity issues immediately")
            print("   3. Use # nosec only if false positive\n")


def main():
    """The main entry point for the script."""
    project_root = Path(__file__).parent.parent.parent

    checker = CodeQualityChecker(project_root)
    all_passed = checker.run_all_checks()
    checker.print_summary()
    checker.suggest_fixes()

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
