from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_delta_sweep_markdown_summary(tmp_path: Path) -> None:
    benchmark = load_script("benchmark_delta_sweep")
    output = tmp_path / "delta.md"
    rows: list[dict[str, object]] = [
        {
            "delta": 2.0,
            "seconds": 0.25,
            "reachable": 4,
            "relaxations": 12,
            "bucket_phases": 3,
            "max_bucket_size": 5,
        }
    ]

    benchmark.write_markdown_summary(rows, output)

    assert output.read_text(encoding="utf-8").splitlines() == [
        "| delta | seconds | reachable | relaxations | bucket phases | max bucket size |",
        "|---:|---:|---:|---:|---:|---:|",
        "| 2 | 0.250000 | 4 | 12 | 3 | 5 |",
    ]


def test_stepping_policy_markdown_summary(tmp_path: Path) -> None:
    benchmark = load_script("benchmark_stepping_policies")
    output = tmp_path / "policies.md"
    rows: list[dict[str, object]] = [
        {
            "graph_family": "wide_integer_weights",
            "policy": "median",
            "delta": 7.5,
            "seconds": 0.125,
            "relaxations": 9,
            "bucket_phases": 2,
            "max_bucket_size": 3,
        }
    ]

    benchmark.write_markdown_summary(rows, output)

    assert output.read_text(encoding="utf-8").splitlines() == [
        "| graph family | policy | delta | seconds | relaxations | bucket phases | max bucket size |",
        "|---|---|---:|---:|---:|---:|---:|",
        "| wide_integer_weights | median | 7.500000 | 0.125000 | 9 | 2 | 3 |",
    ]


def test_benchmark_scripts_write_markdown_outputs(tmp_path: Path) -> None:
    delta_output = tmp_path / "delta.json"
    policies_output = tmp_path / "policies.json"

    subprocess.run(
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
            str(delta_output),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_stepping_policies.py",
            "--nodes",
            "20",
            "--edges",
            "60",
            "--output",
            str(policies_output),
        ],
        cwd=ROOT,
        check=True,
    )

    assert delta_output.with_suffix(".csv").exists()
    assert delta_output.with_suffix(".md").exists()
    assert policies_output.with_suffix(".csv").exists()
    assert policies_output.with_suffix(".md").exists()
