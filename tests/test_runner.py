from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path

from tests.run_all import discover_cases


ROOT = Path(__file__).resolve().parents[1]


class RunnerTests(unittest.TestCase):
    def test_discovery_is_nonempty_and_covers_required_categories(self) -> None:
        cases = discover_cases()
        self.assertGreaterEqual(len(cases), 35)
        self.assertEqual(
            {case.category for case in cases},
            {
                "arrays",
                "control_flow",
                "errors",
                "functions",
                "io",
                "regression",
                "structs",
                "types",
            },
        )

    def test_full_runner_is_a_successful_external_command(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tests.run_all"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"Discovered [4-9][0-9] cases: [4-9][0-9] passed, 0 failed\.")

    def test_list_filter_does_not_execute_cases(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "tests.run_all", "--list", "--filter", "errors"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        listed = [line for line in result.stdout.splitlines() if line]
        self.assertEqual(len(listed), 22)
        self.assertTrue(all("tests/cases/errors/" in line for line in listed))


if __name__ == "__main__":
    unittest.main()
