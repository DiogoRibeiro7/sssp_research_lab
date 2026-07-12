from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def test_cli_writes_optional_benchmark_exports(tmp_path: Path) -> None:
    output = tmp_path / "cli_benchmark.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "sssp_lab.cli",
            "--nodes",
            "20",
            "--edges",
            "60",
            "--seed",
            "7",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stderr == ""
    assert "binary_heap_dijkstra:" in completed.stdout
    assert "dial_circular:" in completed.stdout
    assert f"Wrote {output}" in completed.stdout

    rows = json.loads(output.read_text(encoding="utf-8"))
    assert {row["algorithm"] for row in rows} == {
        "binary_heap_dijkstra",
        "dial",
        "dial_circular",
        "radix_heap",
        "delta_stepping_delta_5",
    }
    assert all(row["reachable"] > 0 for row in rows)

    with output.with_suffix(".csv").open(newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(csv_rows) == len(rows)
    assert output.with_suffix(".md").exists()
