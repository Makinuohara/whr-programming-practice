from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "campus_survival" / "main.whr"
APP_DIR = APP.parent
DEMO_INPUT = APP_DIR / "demo_input.txt"
DEMO_OUTPUT = APP_DIR / "demo_output.txt"


class CampusSurvivalApplicationTests(unittest.TestCase):
    def run_app(self, input_text: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "whr", str(APP.relative_to(ROOT))],
            cwd=ROOT,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_demo_is_an_exact_successful_external_run(self) -> None:
        result = self.run_app(DEMO_INPUT.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, DEMO_OUTPUT.read_text(encoding="utf-8"))
        self.assertIn("Ending: Campus leader ending\n", result.stdout)

    def test_loc_checker_accepts_the_application(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/count_whr_loc.py",
                str(APP.relative_to(ROOT)),
                "--minimum",
                "200",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r": \d+ effective WHR lines \(minimum 200: PASS\)")
        self.assertEqual(result.stderr, "")

    def test_source_contains_the_required_language_design(self) -> None:
        source = APP.read_text(encoding="utf-8")
        for fragment in (
            "shape Player",
            "shape ActionResult",
            "form Player",
            "craft clamp",
            "craft apply_event",
            "craft perform_action",
            "repeat while player.week <= 6",
            'choice == "1"',
            'choice == "5"',
            "history: []",
            "achievements: []",
        ):
            self.assertIn(fragment, source)
        for action in ("study", "rest", "club", "part-time", "exercise"):
            self.assertIn(action, source)

    def test_eof_ends_without_an_interpreter_error(self) -> None:
        result = self.run_app("Taylor\n1\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("Input ended: simulation stopped.\n", result.stdout)
        self.assertNotIn("=== Final report ===", result.stdout)

    def test_invalid_menu_choice_does_not_advance_the_week(self) -> None:
        result = self.run_app("Jordan\nx\n1\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("Invalid action. Choose 1, 2, 3, 4, or 5.\n", result.stdout)
        self.assertEqual(result.stdout.count("Week 1 status:"), 2)
        self.assertIn("Week 1 complete.\n", result.stdout)
        self.assertNotIn("Week 2 complete.\n", result.stdout)

    def test_alternative_endings_are_reachable_by_real_action_sequences(self) -> None:
        scenarios = (
            ("Burnout", "4\n4\n4\n4\n4\n4\n", "Burnout ending"),
            ("Academic", "1\n1\n1\n1\n1\n1\n", "Academic survivor ending"),
            ("Steady", "2\n2\n2\n2\n2\n2\n", "Steady graduate ending"),
        )
        for name, choices, expected_ending in scenarios:
            with self.subTest(name=name):
                result = self.run_app(name + "\n" + choices)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertIn(f"Ending: {expected_ending}\n", result.stdout)


if __name__ == "__main__":
    unittest.main()
