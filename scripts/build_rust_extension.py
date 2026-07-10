#!/usr/bin/env python
"""Build the optional Rust extension wheel."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from install_built_rust_extension import install_extension_from_wheel

ROOT = Path(__file__).resolve().parents[1]
EXTENSION_DIR = ROOT / "rust" / "sssp_accel"
WHEEL_DIR = EXTENSION_DIR / "target" / "wheels"
SOURCE_PACKAGE_DIR = ROOT / "src" / "sssp_lab"


def newest_wheel(wheel_dir: Path) -> Path:
    """Return the newest built wheel in a maturin target directory."""

    wheels = sorted(
        wheel_dir.glob("*.whl"),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )
    if not wheels:
        raise RuntimeError(f"no wheels found in {wheel_dir}")
    return wheels[0]


def maturin_args(raw_args: list[str]) -> list[str]:
    """Normalize pass-through arguments after argparse's REMAINDER handling."""

    if raw_args and raw_args[0] == "--":
        return raw_args[1:]
    return raw_args


def build_wheel(*, release: bool, extra_args: list[str]) -> Path:
    """Run maturin and return the newest generated wheel path."""

    command = [sys.executable, "-m", "maturin", "build"]
    if release:
        command.append("--release")
    command.extend(extra_args)
    subprocess.run(command, cwd=EXTENSION_DIR, check=True)
    return newest_wheel(WHEEL_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the optional Rust acceleration wheel.")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Build a debug wheel instead of the default release wheel.",
    )
    parser.add_argument(
        "--install-source",
        action="store_true",
        help="Copy the compiled extension into src/sssp_lab after building.",
    )
    parser.add_argument(
        "--package-dir",
        type=Path,
        default=SOURCE_PACKAGE_DIR,
        help="Package directory used with --install-source.",
    )
    parser.add_argument(
        "extra_args",
        nargs=argparse.REMAINDER,
        help="Additional arguments passed to maturin after --.",
    )
    args = parser.parse_args()

    wheel = build_wheel(release=not args.debug, extra_args=maturin_args(args.extra_args))
    print(f"Built {wheel}")
    if args.install_source:
        target = install_extension_from_wheel(wheel, args.package_dir)
        print(f"Installed {target}")


if __name__ == "__main__":
    main()
