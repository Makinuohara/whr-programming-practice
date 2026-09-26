from __future__ import annotations

import unittest

from benchmarks.run_benchmarks import (
    Execution,
    compare_pair,
    discover_workloads,
    _git_dirty_from_status,
    render_report,
    summarize_records,
)


def execution(
    implementation: str,
    *,
    stdout: str = "answer\n",
    returncode: int | None = 0,
    stderr: str = "",
    timed_out: bool = False,
) -> Execution:
    return Execution(
        workload="synthetic",
        implementation=implementation,
        phase="validation",
        round=0,
        command=[implementation],
        elapsed_ns=1_000_000,
        stdout=stdout,
        stderr=stderr,
        returncode=returncode,
        timed_out=timed_out,
    )


class BenchmarkTests(unittest.TestCase):
    def test_git_status_mapping_distinguishes_clean_dirty_and_unavailable(self) -> None:
        self.assertFalse(_git_dirty_from_status(""))
        self.assertFalse(_git_dirty_from_status("\n"))
        self.assertTrue(_git_dirty_from_status(" M benchmarks/run_benchmarks.py\n"))
        self.assertIsNone(_git_dirty_from_status(None))

    def test_workloads_have_paired_sources_and_fixed_parameters(self) -> None:
        workloads = discover_workloads()
        self.assertEqual({workload.name for workload in workloads}, {"prime_count", "container_update"})
        for workload in workloads:
            self.assertTrue(workload.whr_path.is_file())
            self.assertTrue(workload.python_path.is_file())
            self.assertTrue(workload.parameters)

    def test_output_comparison_accepts_match_and_reports_mismatch(self) -> None:
        expected, failures = compare_pair(execution("whr"), execution("python"), timeout=1)
        self.assertEqual(expected, "answer\n")
        self.assertEqual(failures, [])

        expected, failures = compare_pair(
            execution("whr"), execution("python", stdout="different\n"), timeout=1
        )
        self.assertIsNone(expected)
        self.assertEqual(len(failures), 1)
        self.assertIn("stdout differs", failures[0])

    def test_statistics_exclude_failed_and_warmup_samples(self) -> None:
        records = [
            {
                "implementation": "whr",
                "phase": "formal",
                "elapsed_ns": 10,
                "returncode": 0,
                "stderr": "",
                "timed_out": False,
                "output_match": True,
            },
            {
                "implementation": "whr",
                "phase": "formal",
                "elapsed_ns": 30,
                "returncode": 70,
                "stderr": "error",
                "timed_out": False,
                "output_match": False,
            },
            {
                "implementation": "whr",
                "phase": "warmup",
                "elapsed_ns": 1,
                "returncode": 0,
                "stderr": "",
                "timed_out": False,
                "output_match": True,
            },
            {
                "implementation": "python",
                "phase": "formal",
                "elapsed_ns": 5,
                "returncode": 0,
                "stderr": "",
                "timed_out": False,
                "output_match": True,
            },
        ]
        summary = summarize_records(records)
        self.assertEqual(summary["whr"]["samples"], 1)
        self.assertEqual(summary["whr"]["median_ns"], 10)
        self.assertEqual(summary["python"]["samples"], 1)
        self.assertEqual(summary["whr_over_python"], 2.0)

    def test_report_contains_method_environment_stats_and_rounds(self) -> None:
        data = {
            "generated_at_utc": "2026-01-01T00:00:00+00:00",
            "environment": {
                "python_version": "3.x",
                "platform": "test-platform",
                "machine": "test-machine",
                "processor": "test-cpu",
                "git_commit": "abc123",
            },
            "parameters": {"repetitions": 1, "warmups": 0, "timeout_seconds": 5},
            "workloads": {
                "synthetic": {
                    "input": "small",
                    "parameters": {"n": 2},
                    "algorithm": "loop",
                    "expected_stdout": "answer\n",
                    "summary": {
                        "whr": {"samples": 1, "status": "ok", "median_ns": 10, "min_ns": 10, "max_ns": 10},
                        "python": {"samples": 1, "status": "ok", "median_ns": 5, "min_ns": 5, "max_ns": 5},
                        "whr_over_python": 2.0,
                    },
                }
            },
            "runs": [
                {
                    "workload": "synthetic",
                    "phase": "formal",
                    "round": 1,
                    "implementation": "whr",
                    "elapsed_ns": 10,
                    "returncode": 0,
                    "timed_out": False,
                    "output_match": True,
                }
            ],
            "failures": [],
        }
        report = render_report(data)
        self.assertIn("端到端墙钟时间", report)
        self.assertIn("test-platform", report)
        self.assertIn("synthetic", report)
        self.assertIn("2.00×", report)
        self.assertIn("全部计时记录", report)


if __name__ == "__main__":
    unittest.main()
