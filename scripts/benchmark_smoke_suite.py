#!/usr/bin/env python
"""Run a quick deterministic smoke suite across benchmark entry points."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def smoke_commands(output_dir: Path) -> list[list[str]]:
    """Return benchmark smoke commands using the current Python interpreter."""

    return [
        [
            sys.executable,
            "-m",
            "sssp_lab.cli",
            "--nodes",
            "30",
            "--edges",
            "90",
            "--output",
            str(output_dir / "cli_sssp.json"),
        ],
        [
            sys.executable,
            "scripts/benchmark_sssp.py",
            "--nodes",
            "30",
            "--edges",
            "90",
            "--output",
            str(output_dir / "sssp.json"),
        ],
        [
            sys.executable,
            "scripts/benchmark_delta_sweep.py",
            "--nodes",
            "20",
            "--edges",
            "60",
            "--deltas",
            "1,2",
            "--output",
            str(output_dir / "delta_sweep.json"),
        ],
        [
            sys.executable,
            "scripts/benchmark_stepping_policies.py",
            "--nodes",
            "20",
            "--edges",
            "60",
            "--output",
            str(output_dir / "stepping_policies.json"),
        ],
        [
            sys.executable,
            "scripts/benchmark_parallel_delta.py",
            "--nodes",
            "20",
            "--edges",
            "60",
            "--sources",
            "3",
            "--modes",
            "sequential,thread",
            "--output",
            str(output_dir / "parallel_delta.json"),
        ],
        [
            sys.executable,
            "scripts/benchmark_alt.py",
            "--nodes",
            "20",
            "--edges",
            "60",
            "--pairs",
            "3",
            "--landmarks",
            "3",
            "--strategy",
            "avoid",
            "--output",
            str(output_dir / "alt.json"),
        ],
        [
            sys.executable,
            "scripts/benchmark_ch.py",
            "--nodes",
            "8",
            "--edges",
            "14",
            "--pairs",
            "2",
            "--heuristic",
            "degree",
            "--output",
            str(output_dir / "ch.json"),
        ],
        [
            sys.executable,
            "scripts/benchmark_frontier.py",
            "--nodes",
            "20",
            "--edges",
            "60",
            "--initial-bound",
            "2",
            "--output",
            str(output_dir / "frontier.json"),
        ],
        [
            sys.executable,
            "scripts/benchmark_negative.py",
            "--nodes",
            "12",
            "--edges",
            "30",
            "--output",
            str(output_dir / "negative.json"),
        ],
        [
            sys.executable,
            "scripts/benchmark_thorup.py",
            "--nodes",
            "12",
            "--edges",
            "24",
            "--output",
            str(output_dir / "thorup.json"),
        ],
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run benchmark smoke commands.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".benchmarks/smoke_suite"),
        help="Directory for smoke benchmark JSON/CSV/markdown artifacts.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for command in smoke_commands(args.output_dir):
        print("Running " + " ".join(command), flush=True)
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
