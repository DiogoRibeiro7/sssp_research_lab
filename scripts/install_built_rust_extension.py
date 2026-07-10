#!/usr/bin/env python
"""Install a built Rust extension wheel into the source checkout for tests."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

EXTENSION_SUFFIXES = (".so", ".pyd", ".dylib")


def find_extension_member(wheel: zipfile.ZipFile) -> str:
    """Return the compiled extension member from a maturin wheel."""

    candidates = [
        name
        for name in wheel.namelist()
        if Path(name).name.startswith("_sssp_accel")
        and Path(name).suffix in EXTENSION_SUFFIXES
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"expected one compiled extension in wheel, found {candidates}")
    return candidates[0]


def install_extension_from_wheel(wheel_path: Path, package_dir: Path) -> Path:
    """Copy the compiled extension from a wheel into a package directory."""

    package_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel_path) as wheel:
        member = find_extension_member(wheel)
        target = package_dir / Path(member).name
        target.write_bytes(wheel.read(member))
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy built Rust extension into src package.")
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--package-dir", type=Path, default=Path("src/sssp_lab"))
    args = parser.parse_args()

    target = install_extension_from_wheel(args.wheel, args.package_dir)
    print(f"Installed {target}")


if __name__ == "__main__":
    main()
