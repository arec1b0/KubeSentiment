#!/usr/bin/env python3
"""
Скрипт для проверки качества кода и генерации отчета.
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class CodeQualityChecker:
    """Проверка качества кода с отчетом."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: Dict[str, Dict] = {}

    def run_command(self, name: str, cmd: List[str]) -> Tuple[bool, str]:
        """Запустить команду и вернуть результат."""
        try:
            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True, timeout=60
            )
            success = result.returncode == 0
            output = result.stdout + result.stderr
            return success, output
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def check_black(self) -> None:
        """Проверить форматирование с Black."""
        print("🎨 Checking Black formatting...", end=" ")
        success, output = self.run_command(
            "black", ["black", "--check", "app/", "tests/", "scripts/", "run.py"]
        )
        self.results["black"] = {"success": success, "output": output}
        print("✅" if success else "❌")

    def check_isort(self) -> None:
        """Проверить сортировку импортов."""
        print("📦 Checking isort...", end=" ")
        success, output = self.run_command(
            "isort",
            ["isort", "--check-only", "app/", "tests/", "scripts/", "run.py"],
        )
        self.results["isort"] = {"success": success, "output": output}
        print("✅" if success else "❌")

    def check_flake8(self) -> None:
        """Проверить стиль кода с Flake8."""
        print("🔍 Checking Flake8...", end=" ")
        success, output = self.run_command(
            "flake8", ["flake8", "app/", "tests/", "scripts/", "run.py"]
        )
        self.results["flake8"] = {"success": success, "output": output}
        print("✅" if success else "❌")

    def check_mypy(self) -> None:
        """Проверить типы с mypy."""
        print("🔬 Checking mypy...", end=" ")
        success, output = self.run_command(
            "mypy", ["mypy", "app/", "--ignore-missing-imports"]
        )
        self.results["mypy"] = {"success": success, "output": output}
        print("✅" if success else "❌")

    def check_bandit(self) -> None:
        """Проверить безопасность с Bandit."""
        print("🔒 Checking Bandit security...", end=" ")
        success, output = self.run_command("bandit", ["bandit", "-r", "app/"])
        self.results["bandit"] = {"success": success, "output": output}
        print("✅" if success else "❌")

    def run_all_checks(self) -> bool:
        """Запустить все проверки."""
        print("\n" + "=" * 60)
        print("🚀 Running Code Quality Checks")
        print("=" * 60 + "\n")

        self.check_black()
        self.check_isort()
        self.check_flake8()
        self.check_mypy()
        self.check_bandit()

        return all(result["success"] for result in self.results.values())

    def print_summary(self) -> None:
        """Вывести сводку результатов."""
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
        """Предложить исправления."""
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

        if "flake8" in failed:
            print("🔧 To fix flake8 issues:")
            print("   1. Review errors above")
            print("   2. Fix manually or run: make format")
            print("   3. Some issues require manual intervention\n")

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
    """Главная функция."""
    project_root = Path(__file__).parent.parent

    checker = CodeQualityChecker(project_root)
    all_passed = checker.run_all_checks()
    checker.print_summary()
    checker.suggest_fixes()

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

