"""Run the reproducible, non-destructive WHR project acceptance checks.

This checker is intentionally a coordinator rather than another test runner:
it invokes the public CLI and existing test commands in subprocesses, and it
reads the retained formal benchmark JSON without starting a benchmark run.
The presentation deliverables are checked separately so a missing deck is
reported clearly while the other acceptance results remain visible.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks" / "results" / "2026-09-26.json"


@dataclass(frozen=True)
class CheckResult:
    """One independently reported acceptance check."""

    label: str
    passed: bool
    detail: str


def _display(value: str, limit: int = 1200) -> str:
    """Render command output compactly while retaining useful diagnostics."""

    value = value.replace("\r\n", "\n")
    if len(value) > limit:
        value = value[:limit] + "..."
    return repr(value)


def _run(
    label: str,
    command: Sequence[str],
    results: list[CheckResult],
    *,
    expected_stdout: str | None = None,
    expected_stderr: str | None = None,
    timeout: float = 120.0,
) -> subprocess.CompletedProcess[str] | None:
    """Run one public command and append a pass/fail result.

    A timeout or failed process is converted into a normal failed check.  The
    checker itself therefore keeps running and reports all remaining checks.
    """

    try:
        completed = subprocess.run(
            list(command),
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        results.append(
            CheckResult(
                label,
                False,
                f"timed out after {timeout:g}s: {error.cmd!r}",
            )
        )
        return None
    except OSError as error:
        results.append(CheckResult(label, False, f"could not start command: {error}"))
        return None

    passed = completed.returncode == 0
    expectations: list[str] = [f"exit={completed.returncode}"]
    if expected_stdout is not None:
        stdout_ok = completed.stdout == expected_stdout
        passed = passed and stdout_ok
        expectations.append(
            f"stdout={'match' if stdout_ok else 'mismatch'}"
        )
    if expected_stderr is not None:
        stderr_ok = completed.stderr == expected_stderr
        passed = passed and stderr_ok
        expectations.append(
            f"stderr={'match' if stderr_ok else 'mismatch'}"
        )
    if not passed or expected_stdout is None or expected_stderr is None:
        expectations.extend(
            [
                f"stdout={_display(completed.stdout)}",
                f"stderr={_display(completed.stderr)}",
            ]
        )
    results.append(CheckResult(label, passed, "; ".join(expectations)))
    return completed


def _check_file(
    relative: str, results: list[CheckResult], *, description: str | None = None
) -> None:
    path = ROOT / relative
    label = description or f"deliverable {relative}"
    if path.is_file():
        results.append(CheckResult(label, True, str(relative)))
    else:
        results.append(CheckResult(label, False, f"missing file: {relative}"))


def _check_deliverables(results: list[CheckResult]) -> None:
    """Check the files that make the submission independently reviewable."""

    frozen_docs = (
        "docs/language/01_WHR语言规范.md",
        "docs/language/02_标准库.md",
        "docs/language/03_错误模型.md",
        "docs/language/04_规范示例与预期行为.md",
    )
    for relative in frozen_docs:
        _check_file(relative, results, description=f"language specification: {relative}")

    for relative in ("whr/__init__.py", "whr/__main__.py", "whr/cli.py"):
        _check_file(relative, results, description=f"interpreter source: {relative}")

    _check_file("tests/run_all.py", results, description="black-box test runner")
    cases = sorted((ROOT / "tests" / "cases").rglob("*.whr"))
    results.append(
        CheckResult(
            "black-box test cases",
            bool(cases),
            f"{len(cases)} .whr cases under tests/cases",
        )
    )
    test_modules = sorted((ROOT / "tests").glob("test_*.py"))
    results.append(
        CheckResult(
            "unit test modules",
            bool(test_modules),
            f"{len(test_modules)} test_*.py modules",
        )
    )

    _check_file("benchmarks/results/2026-09-26.json", results, description="formal benchmark JSON")
    _check_file("docs/performance/性能测试报告.md", results, description="benchmark report")
    for relative in (
        "benchmarks/README.md",
        "benchmarks/run_benchmarks.py",
        "benchmarks/prime_count.whr",
        "benchmarks/prime_count.py",
        "benchmarks/container_update.whr",
        "benchmarks/container_update.py",
    ):
        _check_file(relative, results, description=f"benchmark source/tool: {relative}")

    for relative in (
        "docs/guides/01_快速开始.md",
        "docs/guides/02_开发指南.md",
        "docs/guides/03_调试与错误指南.md",
        "docs/guides/04_Agent任务模板.md",
    ):
        _check_file(relative, results, description=f"human/Agent guide: {relative}")
    _check_file(
        ".agents/skills/whr-language/SKILL.md",
        results,
        description="project WHR Agent skill",
    )

    for relative in (
        "apps/campus_survival/main.whr",
        "apps/campus_survival/README.md",
        "apps/campus_survival/demo_input.txt",
        "apps/campus_survival/demo_output.txt",
    ):
        _check_file(relative, results, description=f"application deliverable: {relative}")
    for relative in (
        "docs/agent_logs/06_skill_forward_test.md",
        "docs/agent_logs/07_app_task.md",
        "docs/agent_logs/07_app_implementation.md",
    ):
        _check_file(relative, results, description=f"Agent development log: {relative}")

    _check_file("examples/hello.whr", results, description="hello example")
    _check_file("examples/language_tour.whr", results, description="language tour example")

    _check_presentation_deliverables(results)


def _presentation_files() -> list[Path]:
    root = ROOT / "presentation"
    if not root.is_dir():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def _has_named_text_file(files: Iterable[Path], keywords: tuple[str, ...]) -> Path | None:
    for path in files:
        if path.suffix.lower() not in {".md", ".txt", ".docx", ".pdf"}:
            continue
        name = path.name.lower()
        if any(keyword.lower() in name for keyword in keywords):
            return path
    return None


def _check_presentation_deliverables(results: list[CheckResult]) -> None:
    """Report the five presentation artifacts without assuming one filename."""

    files = _presentation_files()
    root_note = "presentation/ exists" if files else "presentation/ is missing or empty"
    results.append(CheckResult("presentation directory", bool(files), root_note))

    for suffix, label in ((".pptx", "presentation PPTX"), (".pdf", "presentation PDF")):
        matches = [path for path in files if path.suffix.lower() == suffix]
        detail = str(matches[0].relative_to(ROOT)) if matches else (
            f"no {suffix} found under presentation/; add the final slide deck/export"
        )
        results.append(CheckResult(label, bool(matches), detail))

    text_requirements = (
        ("defense script", ("讲稿", "验收", "defense", "speech")),
        ("demonstration script", ("演示", "demo", "script")),
        ("FAQ / common questions", ("问答", "faq", "qa")),
    )
    for label, keywords in text_requirements:
        match = _has_named_text_file(files, keywords)
        if match is None:
            detail = (
                "missing named text artifact under presentation/; "
                "accepted name keywords: " + ", ".join(keywords)
            )
        else:
            detail = str(match.relative_to(ROOT))
        results.append(CheckResult(label, match is not None, detail))


def _check_benchmark(path: Path, results: list[CheckResult]) -> None:
    """Validate retained formal samples, without invoking benchmark code."""

    label = "formal benchmark JSON integrity"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        results.append(CheckResult(label, False, f"cannot read JSON: {error}"))
        return
    if not isinstance(data, dict):
        results.append(CheckResult(label, False, "top-level JSON value is not an object"))
        return

    problems: list[str] = []
    summary = data.get("summary")
    environment = data.get("environment")
    parameters = data.get("parameters")
    runs = data.get("runs")
    workloads = data.get("workloads")
    if not isinstance(summary, dict):
        problems.append("summary is not an object")
        summary = {}
    if not isinstance(environment, dict):
        problems.append("environment is not an object")
        environment = {}
    if not isinstance(parameters, dict):
        problems.append("parameters is not an object")
        parameters = {}
    if not isinstance(runs, list):
        problems.append("runs is not an array")
        runs = []
    if not isinstance(workloads, dict):
        problems.append("workloads is not an object")
        workloads = {}

    if summary.get("status") != "ok":
        problems.append(f"summary.status={summary.get('status')!r}, expected 'ok'")
    if summary.get("workloads") != 2:
        problems.append(f"summary.workloads={summary.get('workloads')!r}, expected 2")
    if summary.get("formal_runs") != 28:
        problems.append(f"summary.formal_runs={summary.get('formal_runs')!r}, expected 28")
    if summary.get("failures") != 0:
        problems.append(f"summary.failures={summary.get('failures')!r}, expected 0")
    if environment.get("git_dirty") is not False:
        problems.append(f"environment.git_dirty={environment.get('git_dirty')!r}, expected false")
    if parameters.get("repetitions") != 7:
        problems.append(f"parameters.repetitions={parameters.get('repetitions')!r}, expected 7")

    formal = [record for record in runs if isinstance(record, dict) and record.get("phase") == "formal"]
    if len(formal) != 28:
        problems.append(f"formal run records={len(formal)}, expected 28")
    if data.get("failures") != []:
        problems.append("top-level failures is not an empty array")

    expected_workloads = {"prime_count", "container_update"}
    missing_workloads = expected_workloads - set(workloads)
    if missing_workloads:
        problems.append("missing workloads: " + ", ".join(sorted(missing_workloads)))
    extra_workloads = set(workloads) - expected_workloads
    if extra_workloads:
        problems.append("unexpected workloads: " + ", ".join(sorted(extra_workloads)))

    for workload in sorted(expected_workloads & set(workloads)):
        workload_data = workloads[workload]
        if not isinstance(workload_data, dict):
            problems.append(f"{workload} workload entry is not an object")
            continue
        records = [record for record in formal if record.get("workload") == workload]
        counts = Counter(record.get("implementation") for record in records)
        if counts != Counter({"whr": 7, "python": 7}):
            problems.append(f"{workload} formal counts={dict(counts)!r}, expected 7 per implementation")
        rounds_by_impl: dict[str, set[Any]] = {"whr": set(), "python": set()}
        expected_stdout = workload_data.get("expected_stdout")
        for record in records:
            implementation = record.get("implementation")
            if implementation in rounds_by_impl:
                rounds_by_impl[implementation].add(record.get("round"))
            if record.get("returncode") != 0:
                problems.append(f"{workload}/{implementation} round {record.get('round')}: nonzero exit")
            if record.get("timed_out") is not False:
                problems.append(f"{workload}/{implementation} round {record.get('round')}: timed out")
            if record.get("output_match") is not True:
                problems.append(f"{workload}/{implementation} round {record.get('round')}: output mismatch")
            if record.get("stderr") != "":
                problems.append(f"{workload}/{implementation} round {record.get('round')}: stderr is nonempty")
            if isinstance(expected_stdout, str) and record.get("stdout") != expected_stdout:
                problems.append(f"{workload}/{implementation} round {record.get('round')}: stdout differs from workload checksum")
        for implementation, rounds in rounds_by_impl.items():
            if rounds != set(range(1, 8)):
                problems.append(f"{workload}/{implementation} rounds={sorted(rounds)!r}, expected 1..7")

        workload_summary = workload_data.get("summary", {})
        if not isinstance(workload_summary, dict):
            problems.append(f"{workload} summary is not an object")
            workload_summary = {}
        for implementation in ("whr", "python"):
            sample_summary = workload_summary.get(implementation, {})
            if sample_summary.get("samples") != 7 or sample_summary.get("status") != "ok":
                problems.append(
                    f"{workload}/{implementation} summary is not 7 successful samples"
                )

    if problems:
        results.append(CheckResult(label, False, " | ".join(problems)))
    else:
        results.append(
            CheckResult(
                label,
                True,
                f"{path.relative_to(ROOT)}: 2 workloads, 28 formal samples, clean git state",
            )
        )


def _run_acceptance_commands(results: list[CheckResult]) -> None:
    python = sys.executable
    version = f"WHR 1.0 (interpreter 1.0.0)\n"
    _run(
        "CLI --version",
        [python, "-m", "whr", "--version"],
        results,
        expected_stdout=version,
        expected_stderr="",
    )
    _run(
        "language_tour --check",
        [python, "-m", "whr", "--check", "examples/language_tour.whr"],
        results,
        expected_stdout="",
        expected_stderr="",
    )
    expected_tour = (
        "student: WHR\n"
        "scores: [92, 88, 96, 100]\n"
        "average: 94\n"
        "level: excellent\n"
    )
    _run(
        "language_tour execution",
        [python, "-m", "whr", "examples/language_tour.whr"],
        results,
        expected_stdout=expected_tour,
        expected_stderr="",
    )
    _run("black-box suite (tests.run_all)", [python, "-m", "tests.run_all"], results)
    _run(
        "unit test suite",
        [python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        results,
    )
    _run(
        "Python compileall",
        [python, "-m", "compileall", "-q", "whr", "tests", "benchmarks", "scripts"],
        results,
        expected_stdout="",
        expected_stderr="",
    )
    _run(
        "application effective LOC >= 200",
        [
            python,
            "scripts/count_whr_loc.py",
            "apps/campus_survival/main.whr",
            "--minimum",
            "200",
        ],
        results,
    )

    input_path = ROOT / "apps" / "campus_survival" / "demo_input.txt"
    output_path = ROOT / "apps" / "campus_survival" / "demo_output.txt"
    try:
        demo_input = input_path.read_text(encoding="utf-8")
        demo_output = output_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        results.append(CheckResult("application demo", False, f"cannot read demo fixture: {error}"))
    else:
        try:
            completed = subprocess.run(
                [python, "-m", "whr", "apps/campus_survival/main.whr"],
                cwd=ROOT,
                input=demo_input,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120.0,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            results.append(CheckResult("application demo", False, f"execution failed: {error}"))
        else:
            ok = (
                completed.returncode == 0
                and completed.stdout == demo_output
                and completed.stderr == ""
            )
            results.append(
                CheckResult(
                    "application demo",
                    ok,
                    (
                        f"exit={completed.returncode}; "
                        f"stdout={'match' if completed.stdout == demo_output else 'mismatch'}; "
                        f"stderr={'match' if completed.stderr == '' else _display(completed.stderr)}"
                    ),
                )
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-json",
        type=Path,
        default=DEFAULT_BENCHMARK,
        help="retained formal benchmark JSON (never executed or regenerated)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    benchmark_path = args.benchmark_json
    if not benchmark_path.is_absolute():
        benchmark_path = ROOT / benchmark_path

    results: list[CheckResult] = []
    _check_deliverables(results)
    _run_acceptance_commands(results)
    _check_benchmark(benchmark_path, results)

    print("WHR project acceptance check")
    print("=" * 28)
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.label}: {result.detail}")
    passed = sum(result.passed for result in results)
    failed = len(results) - passed
    print("=" * 28)
    print(f"Summary: {passed} passed, {failed} failed, {len(results)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
