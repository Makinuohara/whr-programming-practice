"""Black-box test runner for WHR programs.

The runner deliberately treats the interpreter as an external command.  A
case is a source file plus optional same-stem expectation files:

* ``case.stdout`` — exact standard output, defaulting to empty;
* ``case.stderr`` — exact standard error, defaulting to empty;
* ``case.json`` — optional ``stdin``, ``exit_code``, ``tags`` and ``timeout``.
"""

from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional


ROOT = Path(__file__).resolve().parents[1]
CASES_ROOT = ROOT / "tests" / "cases"
DEFAULT_TIMEOUT = 5.0
CLI_MISSING_FILE = "tests/cli_checks/__absent_for_black_box__.whr"


@dataclass(frozen=True)
class Case:
    source: Path
    relative: str
    expected_stdout: str
    expected_stderr: str
    stdin: str
    expected_exit_code: int
    tags: tuple[str, ...]
    timeout: float

    @property
    def category(self) -> str:
        return self.source.parent.name


@dataclass
class Result:
    case: Case
    passed: bool
    actual_stdout: str = ""
    actual_stderr: str = ""
    actual_exit_code: Optional[int] = None
    timed_out: bool = False
    setup_error: Optional[str] = None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("metadata must be a JSON object")
    return value


def _load_case(source: Path) -> Case:
    metadata = _read_json(source.with_suffix(".json"))
    stdin = metadata.get("stdin", "")
    if not isinstance(stdin, str):
        raise ValueError("stdin must be a string")
    exit_code = metadata.get("exit_code", 0)
    if not isinstance(exit_code, int):
        raise ValueError("exit_code must be an integer")
    tags = metadata.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise ValueError("tags must be a string or a list of strings")
    timeout = metadata.get("timeout", DEFAULT_TIMEOUT)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("timeout must be a positive number")
    relative = source.relative_to(ROOT).as_posix()
    return Case(
        source=source,
        relative=relative,
        expected_stdout=source.with_suffix(".stdout").read_text(encoding="utf-8")
        if source.with_suffix(".stdout").exists()
        else "",
        expected_stderr=source.with_suffix(".stderr").read_text(encoding="utf-8")
        if source.with_suffix(".stderr").exists()
        else "",
        stdin=stdin,
        expected_exit_code=exit_code,
        tags=tuple(tags),
        timeout=float(timeout),
    )


def discover_cases(root: Path = CASES_ROOT) -> list[Case]:
    """Recursively load all ``.whr`` files below the cases directory."""

    if not root.exists():
        return []
    cases: list[Case] = []
    for source in sorted(root.rglob("*.whr")):
        cases.append(_load_case(source))
    return cases


def extra_cli_cases() -> list[Case]:
    """Return CLI-only checks that cannot themselves be ``.whr`` sources."""

    return [
        Case(
            source=ROOT / "cli_checks" / "__absent_for_black_box__.whr",
            relative=CLI_MISSING_FILE,
            expected_stdout="",
            expected_stderr=(
                f"{CLI_MISSING_FILE}: IOError: [Errno 2] No such file or directory: "
                f"'{CLI_MISSING_FILE}'\n"
            ),
            stdin="",
            expected_exit_code=74,
            tags=("cli", "io"),
            timeout=DEFAULT_TIMEOUT,
        )
    ]


def _matches(case: Case, text: str) -> bool:
    if not text:
        return True
    haystack = " ".join((case.relative, case.category, *case.tags))
    return text.lower() in haystack.lower()


def _run_case(case: Case) -> Result:
    command = [sys.executable, "-m", "whr", case.relative]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            input=case.stdin,
            text=True,
            capture_output=True,
            timeout=case.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return Result(
            case=case,
            passed=False,
            actual_stdout=stdout,
            actual_stderr=stderr,
            timed_out=True,
        )
    passed = (
        completed.returncode == case.expected_exit_code
        and completed.stdout == case.expected_stdout
        and completed.stderr == case.expected_stderr
    )
    return Result(
        case=case,
        passed=passed,
        actual_stdout=completed.stdout,
        actual_stderr=completed.stderr,
        actual_exit_code=completed.returncode,
    )


def _diff(label: str, expected: str, actual: str) -> str:
    if expected == actual:
        return ""
    lines = difflib.unified_diff(
        expected.splitlines(keepends=True),
        actual.splitlines(keepends=True),
        fromfile=f"{label} expected",
        tofile=f"{label} actual",
    )
    return "".join(lines)


def _print_failure(result: Result) -> None:
    case = result.case
    print(f"\nFAIL {case.relative}", file=sys.stdout)
    if result.setup_error:
        print(f"  setup error: {result.setup_error}", file=sys.stdout)
        return
    if result.timed_out:
        print(f"  timed out after {case.timeout:g}s", file=sys.stdout)
    if result.actual_exit_code != case.expected_exit_code:
        print(
            f"  exit code: expected {case.expected_exit_code}, "
            f"got {result.actual_exit_code}",
            file=sys.stdout,
        )
    stdout_diff = _diff(case.relative + ".stdout", case.expected_stdout, result.actual_stdout)
    stderr_diff = _diff(case.relative + ".stderr", case.expected_stderr, result.actual_stderr)
    if stdout_diff:
        print(stdout_diff, end="", file=sys.stdout)
    if stderr_diff:
        print(stderr_diff, end="", file=sys.stdout)


def _parse_args(argv: Optional[Iterable[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run WHR black-box cases")
    parser.add_argument(
        "--list", action="store_true", help="list selected cases without executing them"
    )
    parser.add_argument(
        "--filter", default="", help="only run cases whose path, category or tag matches"
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _parse_args(argv)
    try:
        cases = [case for case in discover_cases() if _matches(case, args.filter)]
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"runner setup failure: {error}", file=sys.stderr)
        return 1

    if args.list:
        for case in cases:
            print(case.relative)
        return 0 if cases else 1
    cli_cases = [case for case in extra_cli_cases() if _matches(case, args.filter)]
    cases.extend(cli_cases)
    if not cases:
        print("Discovered 0 cases; refusing to report success.")
        return 1

    results = [_run_case(case) for case in cases]
    passed = sum(result.passed for result in results)
    failed = len(results) - passed
    print(f"Discovered {len(results)} cases: {passed} passed, {failed} failed.")

    category_totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for result in results:
        category_totals[result.case.category][0] += 1
        category_totals[result.case.category][1] += int(result.passed)
    print("By category:")
    for category in sorted(category_totals):
        total, category_passed = category_totals[category]
        print(f"  {category}: {category_passed}/{total} passed")

    for result in results:
        if not result.passed:
            _print_failure(result)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
