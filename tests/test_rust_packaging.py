from __future__ import annotations

import importlib.util
import os
import sys
import zipfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def load_script(name: str) -> ModuleType:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_install_extension_from_wheel_copies_compiled_member(tmp_path: Path) -> None:
    installer = load_script("install_built_rust_extension")
    wheel = tmp_path / "accel.whl"
    package_dir = tmp_path / "package"
    extension_bytes = b"compiled-extension"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("sssp_lab/_sssp_accel.cp312-win_amd64.pyd", extension_bytes)
        archive.writestr("metadata.txt", "ignored")

    target = installer.install_extension_from_wheel(wheel, package_dir)

    assert target == package_dir / "_sssp_accel.cp312-win_amd64.pyd"
    assert target.read_bytes() == extension_bytes


def test_build_helper_normalizes_maturin_args() -> None:
    builder = load_script("build_rust_extension")

    assert builder.maturin_args(["--", "--compatibility", "linux"]) == [
        "--compatibility",
        "linux",
    ]
    assert builder.maturin_args(["--compatibility", "linux"]) == ["--compatibility", "linux"]


def test_build_helper_selects_newest_wheel(tmp_path: Path) -> None:
    builder = load_script("build_rust_extension")
    older = tmp_path / "older.whl"
    newer = tmp_path / "newer.whl"
    older.write_text("older", encoding="utf-8")
    newer.write_text("newer", encoding="utf-8")
    os.utime(older, (1_700_000_000, 1_700_000_000))
    os.utime(newer, (1_800_000_000, 1_800_000_000))

    assert builder.newest_wheel(tmp_path) == newer
