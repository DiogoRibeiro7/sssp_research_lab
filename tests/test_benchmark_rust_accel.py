from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_benchmark_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "benchmark_rust_accel",
        ROOT / "scripts" / "benchmark_rust_accel.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load benchmark script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_add_speedups_matches_python_baselines() -> None:
    benchmark = load_benchmark_module()
    rows: list[dict[str, object]] = [
        {
            "algorithm": "dijkstra",
            "backend": "python",
            "seconds": 8.0,
            "source_count": 2,
            "seconds_per_source": 4.0,
        },
        {
            "algorithm": "dial_circular",
            "backend": "python",
            "seconds": 6.0,
            "source_count": 2,
            "seconds_per_source": 3.0,
        },
        {
            "algorithm": "dijkstra_csr_batch",
            "backend": "rust",
            "seconds": 2.0,
            "source_count": 2,
            "seconds_per_source": 1.0,
        },
        {
            "algorithm": "dial_circular_csr_reused",
            "backend": "rust",
            "seconds": 1.5,
            "source_count": 2,
            "seconds_per_source": 0.75,
        },
        {
            "algorithm": "csr_conversion",
            "backend": "python",
            "seconds": 0.25,
            "source_count": 2,
            "seconds_per_source": 0.125,
        },
    ]

    benchmark.add_speedups(rows)

    assert rows[0]["speedup_vs_python"] == ""
    assert rows[1]["speedup_vs_python"] == ""
    assert rows[2]["speedup_vs_python"] == pytest.approx(4.0)
    assert rows[3]["speedup_vs_python"] == pytest.approx(4.0)
    assert rows[4]["speedup_vs_python"] == ""


def test_write_markdown_summary_formats_speedups(tmp_path: Path) -> None:
    benchmark = load_benchmark_module()
    output = tmp_path / "summary.md"
    rows: list[dict[str, object]] = [
        {
            "algorithm": "dijkstra",
            "backend": "python",
            "seconds": 8.0,
            "source_count": 2,
            "seconds_per_source": 4.0,
            "speedup_vs_python": "",
        },
        {
            "algorithm": "dijkstra_csr_batch",
            "backend": "rust",
            "seconds": 2.0,
            "source_count": 2,
            "seconds_per_source": 1.0,
            "speedup_vs_python": 4.0,
        },
    ]

    benchmark.write_markdown_summary(rows, output)

    assert output.read_text(encoding="utf-8").splitlines() == [
        "| algorithm | backend | sources | seconds | seconds/source | speedup vs python |",
        "|---|---|---:|---:|---:|---:|",
        "| dijkstra | python | 2 | 8.000000 | 4.000000 |  |",
        "| dijkstra_csr_batch | rust | 2 | 2.000000 | 1.000000 | 4.00x |",
    ]
