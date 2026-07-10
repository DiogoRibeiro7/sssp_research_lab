from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_profile_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "profile_rust_accel",
        ROOT / "scripts" / "profile_rust_accel.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load profile script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_write_markdown_summary_includes_top_profile_entries(tmp_path: Path) -> None:
    profile = load_profile_module()
    output = tmp_path / "profile.md"
    rows: list[dict[str, object]] = [
        {
            "phase": "workspace_prepare",
            "seconds": 0.25,
            "source_count": "",
            "reachable": 4,
            "top_cumulative": [
                {
                    "function": "rust_accel.py:50:graph_to_csr",
                    "cumulative_time": 0.20,
                }
            ],
        }
    ]

    profile.write_markdown_summary(rows, output)

    assert output.read_text(encoding="utf-8").splitlines() == [
        "| phase | seconds | sources | reachable | top cumulative functions |",
        "|---|---:|---:|---:|---|",
        "| workspace_prepare | 0.250000 |  | 4 | rust_accel.py:50:graph_to_csr (0.200000s) |",
    ]


def test_profile_script_writes_source_only_outputs(tmp_path: Path) -> None:
    output = tmp_path / "profile.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/profile_rust_accel.py",
            "--nodes",
            "8",
            "--edges",
            "16",
            "--sources",
            "2",
            "--top",
            "3",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert output.exists()
    assert output.with_suffix(".md").exists()
    assert "Wrote" in result.stdout
