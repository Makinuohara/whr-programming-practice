"""Run reproducible end-to-end WHR/Python benchmark comparisons.

The benchmark deliberately launches both implementations as separate Python
processes.  A timed sample therefore includes process startup, source loading,
WHR lexing/parsing and interpretation, as well as the actual workload.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Iterable, Optional


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "benchmarks" / "results" / "benchmarks.json"
DEFAULT_REPORT = ROOT / "benchmarks" / "results" / "benchmarks.md"
DEFAULT_TIMEOUT = 5.0


@dataclass(frozen=True)
class Workload:
    """A pair of semantically equivalent source programs."""

    name: str
    whr_path: Path
    python_path: Path
    input_description: str
    algorithm: str
    parameters: dict[str, int]

    def descriptor(self, expected_stdout: Optional[str] = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "whr": self.whr_path.relative_to(ROOT).as_posix(),
            "python": self.python_path.relative_to(ROOT).as_posix(),
            "input": self.input_description,
            "parameters": self.parameters,
            "algorithm": self.algorithm,
        }
        if expected_stdout is not None:
            result["expected_stdout"] = expected_stdout
        return result


@dataclass
class Execution:
    workload: str
    implementation: str
    phase: str
    round: int
    command: list[str]
    elapsed_ns: int
    stdout: str
    stderr: str
    returncode: Optional[int]
    timed_out: bool
    output_match: Optional[bool] = None

    def record(self) -> dict[str, Any]:
        return {
            "workload": self.workload,
            "implementation": self.implementation,
            "phase": self.phase,
            "round": self.round,
            "command": self.command,
            "elapsed_ns": self.elapsed_ns,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returncode": self.returncode,
            "timed_out": self.timed_out,
            "output_match": self.output_match,
        }


WORKLOADS: tuple[Workload, ...] = (
    Workload(
        name="prime_count",
        whr_path=ROOT / "benchmarks" / "prime_count.whr",
        python_path=ROOT / "benchmarks" / "prime_count.py",
        input_description="试除法统计 2..3000 中的素数个数。",
        algorithm="逐候选数试除到 divisor*divisor<=candidate；找到因子立即返回。",
        parameters={"limit": 3000},
    ),
    Workload(
        name="container_update",
        whr_path=ROOT / "benchmarks" / "container_update.whr",
        python_path=ROOT / "benchmarks" / "container_update.py",
        input_description="创建 4000 元素数组，执行 6 轮索引更新，最后线性求和。",
        algorithm="循环 push 构造数组；双层循环按索引更新；循环读取并计算 checksum。",
        parameters={"size": 4000, "rounds": 6},
    ),
)


def discover_workloads() -> tuple[Workload, ...]:
    """Return the declared workload pairs after checking their source files."""

    missing: list[str] = []
    for workload in WORKLOADS:
        for path in (workload.whr_path, workload.python_path):
            if not path.is_file():
                missing.append(path.relative_to(ROOT).as_posix())
    if missing:
        raise FileNotFoundError("missing benchmark source(s): " + ", ".join(missing))
    return WORKLOADS


def _command(workload: Workload, implementation: str) -> list[str]:
    if implementation == "whr":
        return [
            sys.executable,
            "-m",
            "whr",
            workload.whr_path.relative_to(ROOT).as_posix(),
        ]
    if implementation == "python":
        return [sys.executable, workload.python_path.relative_to(ROOT).as_posix()]
    raise ValueError(f"unknown implementation: {implementation}")


def _text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def execute(
    workload: Workload,
    implementation: str,
    *,
    phase: str,
    round_number: int,
    timeout: float,
) -> Execution:
    """Run one external command and retain all observable results."""

    command = _command(workload, implementation)
    started = perf_counter_ns()
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        elapsed_ns = perf_counter_ns() - started
        return Execution(
            workload=workload.name,
            implementation=implementation,
            phase=phase,
            round=round_number,
            command=command,
            elapsed_ns=elapsed_ns,
            stdout=_text(error.stdout),
            stderr=_text(error.stderr),
            returncode=None,
            timed_out=True,
        )
    return Execution(
        workload=workload.name,
        implementation=implementation,
        phase=phase,
        round=round_number,
        command=command,
        elapsed_ns=perf_counter_ns() - started,
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
        timed_out=False,
    )


def compare_pair(
    whr: Execution, python: Execution, *, timeout: float
) -> tuple[Optional[str], list[str]]:
    """Compare two validation executions without hiding any failure."""

    executions = [whr, python]
    failures: list[str] = []
    for execution in executions:
        label = f"{execution.implementation} validation"
        if execution.timed_out:
            failures.append(f"{label} timed out after {timeout:g}s")
        elif execution.returncode != 0:
            failures.append(f"{label} returned {execution.returncode}")
        if execution.stderr:
            failures.append(f"{label} wrote stderr: {execution.stderr!r}")
    expected_stdout: Optional[str] = None
    if not failures:
        if whr.stdout != python.stdout:
            failures.append(
                "validation stdout differs: "
                f"whr={whr.stdout!r}, python={python.stdout!r}"
            )
            whr.output_match = False
            python.output_match = False
        else:
            expected_stdout = whr.stdout
            whr.output_match = True
            python.output_match = True
    return expected_stdout, failures


def validate_pair(
    workload: Workload, *, timeout: float
) -> tuple[list[Execution], Optional[str], list[str]]:
    """Independently run both programs and compare their observable output."""

    whr = execute(workload, "whr", phase="validation", round_number=0, timeout=timeout)
    python = execute(workload, "python", phase="validation", round_number=0, timeout=timeout)
    expected_stdout, failures = compare_pair(whr, python, timeout=timeout)
    return [whr, python], expected_stdout, failures


def _execution_successful(record: dict[str, Any]) -> bool:
    return (
        record.get("timed_out") is False
        and record.get("returncode") == 0
        and record.get("stderr") == ""
        and record.get("output_match") is True
    )


def _successful(record: dict[str, Any]) -> bool:
    return record.get("phase") == "formal" and _execution_successful(record)


def summarize_records(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Calculate robust summary statistics without counting failed samples."""

    grouped: dict[str, list[int]] = {"whr": [], "python": []}
    for record in records:
        implementation = record.get("implementation")
        if implementation in grouped and _successful(record):
            grouped[implementation].append(int(record["elapsed_ns"]))

    summary: dict[str, Any] = {}
    for implementation, values in grouped.items():
        if not values:
            summary[implementation] = {
                "samples": 0,
                "status": "failed",
            }
            continue
        summary[implementation] = {
            "samples": len(values),
            "status": "ok",
            "median_ns": int(statistics.median(values)),
            "min_ns": min(values),
            "max_ns": max(values),
        }
    whr_median = summary["whr"].get("median_ns")
    python_median = summary["python"].get("median_ns")
    if whr_median is not None and python_median:
        summary["whr_over_python"] = whr_median / python_median
    else:
        summary["whr_over_python"] = None
    return summary


def _milliseconds(nanoseconds: Optional[int]) -> str:
    if nanoseconds is None:
        return "—"
    return f"{nanoseconds / 1_000_000:.3f}"


def _json_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def render_report(data: dict[str, Any]) -> str:
    """Render the saved result object as an explanatory Markdown report."""

    environment = data.get("environment", {})
    parameters = data.get("parameters", {})
    workloads = data.get("workloads", {})
    records = data.get("runs", [])
    failures = data.get("failures", [])
    lines = [
        "# WHR 与 Python 性能对比报告",
        "",
        "> 本报告由 `benchmarks/run_benchmarks.py` 根据同一份 JSON 原始结果自动生成。",
        "",
        "## 1. 实验方法",
        "",
        "- 两个实现使用语义等价、逐句对应的脚本和固定输入规模。",
        f"- 每个工作负载先执行 {parameters.get('warmups', '未知')} 次预热，再执行 {parameters.get('repetitions', '未知')} 轮正式计时。",
        "- 正式轮次交替执行顺序：奇数轮 WHR→Python，偶数轮 Python→WHR。",
        "- 计时使用 `perf_counter_ns`，统计的是独立子进程的端到端墙钟时间：包含进程启动、源码读取，以及 WHR 的词法分析、解析和解释执行。",
        "- 运行失败、超时或校验输出不一致的样本保留在 JSON 中，不进入成功样本统计，并使命令返回非零退出码。",
        "",
        "## 2. 环境与参数",
        "",
        "| 项目 | 值 |",
        "|---|---|",
        f"| 生成时间（UTC） | {data.get('generated_at_utc', '—')} |",
        f"| Python | {environment.get('python_version', '—')} |",
        f"| 平台 | {environment.get('platform', '—')} |",
        f"| 系统架构 | {environment.get('machine', '—')} |",
        f"| 处理器 | {environment.get('processor', '—') or '—'} |",
        f"| Git commit | `{environment.get('git_commit', 'unknown')}` |",
        f"| repetitions | {parameters.get('repetitions', '—')} |",
        f"| warmups | {parameters.get('warmups', '—')} |",
        f"| 单次超时 | {parameters.get('timeout_seconds', '—')} 秒 |",
        "",
    ]

    for name, workload in workloads.items():
        summary = workload.get("summary", {})
        lines.extend(
            [
                f"## 3.{len([line for line in lines if line.startswith('## 3.')]) + 1} 工作负载：`{name}`",
                "",
                f"- 输入与规模：{workload.get('input', '—')}",
                f"- 参数：`{_json_cell(workload.get('parameters', {}))}`",
                f"- 算法：{workload.get('algorithm', '—')}",
                f"- 校验输出：`{workload.get('expected_stdout', '不可用').rstrip()}`",
                "",
                "### 统计摘要",
                "",
                "| 实现 | 成功样本 | median (ms) | min (ms) | max (ms) | 状态 |",
                "|---|---:|---:|---:|---:|---|",
            ]
        )
        for implementation in ("whr", "python"):
            stats = summary.get(implementation, {})
            lines.append(
                "| "
                + " | ".join(
                    [
                        implementation,
                        str(stats.get("samples", 0)),
                        _milliseconds(stats.get("median_ns")),
                        _milliseconds(stats.get("min_ns")),
                        _milliseconds(stats.get("max_ns")),
                        str(stats.get("status", "failed")),
                    ]
                )
                + " |"
            )
        ratio = summary.get("whr_over_python")
        if ratio is None:
            lines.append("\nWHR/Python 中位数倍率：不可用（存在失败样本或 Python 中位数为零）。")
        else:
            lines.append(f"\nWHR/Python 中位数倍率：**{ratio:.2f}×**。")
        lines.extend(
            [
                "",
                "### 全部计时记录",
                "",
                "| 阶段 | 轮次 | 实现 | elapsed (ms) | returncode | timeout | output_match |",
                "|---|---:|---|---:|---:|---|---|",
            ]
        )
        for record in records:
            if record.get("workload") != name:
                continue
            lines.append(
                "| "
                + " | ".join(
                    [
                        str(record.get("phase", "—")),
                        str(record.get("round", "—")),
                        str(record.get("implementation", "—")),
                        _milliseconds(record.get("elapsed_ns")),
                        str(record.get("returncode", "—")),
                        str(record.get("timed_out", "—")),
                        str(record.get("output_match", "—")),
                    ]
                )
                + " |"
            )
        lines.append("")

    lines.extend(
        [
            "## 4. 结论与局限",
            "",
        ]
    )
    if failures:
        lines.append(f"本次实验存在 {len(failures)} 个失败项，不能把结果解释为完整性能比较。失败详情已保存在 JSON。")
    else:
        lines.append("所有工作负载的两种实现均通过返回码、stderr 和 stdout 校验，正式轮次没有失败样本。")
    lines.extend(
        [
            "",
            "WHR 的倍率反映本次实现的解释器和启动开销，不是语言本身的普遍速度定理；它也不意味着 WHR 应当快于 Python。",
            "由于实验测量端到端墙钟时间，进程启动和解析成本会在小规模输入中占比较大；机器负载、Python 版本和系统调度也会影响结果。若要研究纯解释执行吞吐量，应另行设计同进程、同启动条件的实验。",
            "",
        ]
    )
    return "\n".join(lines)


def _git_value(*arguments: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _git_dirty_from_status(status: Optional[str]) -> Optional[bool]:
    """Map git status output to clean/dirty without conflating unavailable Git."""

    if status is None:
        return None
    return bool(status.strip())


def environment_snapshot() -> dict[str, Any]:
    status = _git_value("status", "--porcelain")
    return {
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "git_commit": _git_value("rev-parse", "HEAD") or "unknown",
        "git_dirty": _git_dirty_from_status(status),
    }


def _resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_report(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(data), encoding="utf-8")


def _parse_args(argv: Optional[Iterable[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run WHR/Python performance benchmarks")
    parser.add_argument("--repetitions", type=int, default=7, help="formal rounds per workload")
    parser.add_argument("--warmups", type=int, default=2, help="warmup rounds per workload")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="timeout per process in seconds")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="raw JSON output path")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Markdown report path")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _parse_args(argv)
    if args.repetitions < 1:
        print("--repetitions must be at least 1", file=sys.stderr)
        return 2
    if args.warmups < 0:
        print("--warmups must not be negative", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        print("--timeout must be positive", file=sys.stderr)
        return 2

    output_path = _resolve_path(args.output)
    report_path = _resolve_path(args.report)
    generated_at = datetime.now(timezone.utc).isoformat()
    data: dict[str, Any] = {
        "schema_version": 1,
        "generated_at_utc": generated_at,
        "environment": environment_snapshot(),
        "parameters": {
            "repetitions": args.repetitions,
            "warmups": args.warmups,
            "timeout_seconds": args.timeout,
        },
        "workloads": {},
        "runs": [],
        "failures": [],
    }

    try:
        workloads = discover_workloads()
    except (OSError, ValueError) as error:
        data["failures"].append({"kind": "setup", "message": str(error)})
        _write_json(output_path, data)
        _write_report(report_path, data)
        print(f"benchmark setup failed: {error}", file=sys.stderr)
        return 1

    all_executions: list[Execution] = []
    for workload in workloads:
        validation, expected_stdout, failures = validate_pair(workload, timeout=args.timeout)
        all_executions.extend(validation)
        data["workloads"][workload.name] = workload.descriptor(expected_stdout)
        data["workloads"][workload.name]["validation"] = {
            "ok": not failures,
            "failures": failures,
        }
        for message in failures:
            data["failures"].append(
                {"workload": workload.name, "kind": "validation", "message": message}
            )

        if failures:
            continue
        assert expected_stdout is not None
        for warmup_round in range(1, args.warmups + 1):
            order = ("whr", "python") if warmup_round % 2 else ("python", "whr")
            for implementation in order:
                execution = execute(
                    workload,
                    implementation,
                    phase="warmup",
                    round_number=warmup_round,
                    timeout=args.timeout,
                )
                execution.output_match = (
                    execution.returncode == 0
                    and not execution.timed_out
                    and execution.stderr == ""
                    and execution.stdout == expected_stdout
                )
                all_executions.append(execution)
        for formal_round in range(1, args.repetitions + 1):
            order = ("whr", "python") if formal_round % 2 else ("python", "whr")
            for implementation in order:
                execution = execute(
                    workload,
                    implementation,
                    phase="formal",
                    round_number=formal_round,
                    timeout=args.timeout,
                )
                execution.output_match = (
                    execution.returncode == 0
                    and not execution.timed_out
                    and execution.stderr == ""
                    and execution.stdout == expected_stdout
                )
                all_executions.append(execution)

    data["runs"] = [execution.record() for execution in all_executions]
    for record in data["runs"]:
        if record.get("phase") in {"warmup", "formal"} and not _execution_successful(record):
            data["failures"].append(
                {
                    "workload": record["workload"],
                    "kind": f"{record['phase']}_run",
                    "implementation": record["implementation"],
                    "round": record["round"],
                    "message": "sample failed or output did not match validation",
                }
            )
    for name in data["workloads"]:
        workload_records = [record for record in data["runs"] if record["workload"] == name]
        data["workloads"][name]["summary"] = summarize_records(workload_records)
    data["summary"] = {
        "workloads": len(data["workloads"]),
        "formal_runs": sum(record.get("phase") == "formal" for record in data["runs"]),
        "failures": len(data["failures"]),
        "status": "ok" if not data["failures"] else "failed",
    }

    _write_json(output_path, data)
    _write_report(report_path, data)
    if data["failures"]:
        print(
            f"Benchmark failed with {len(data['failures'])} failure(s); "
            f"raw data: {output_path}",
            file=sys.stderr,
        )
        return 1
    print(f"Benchmark complete: {len(workloads)} workloads, {args.repetitions} formal rounds each.")
    print(f"Raw JSON: {output_path}")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
