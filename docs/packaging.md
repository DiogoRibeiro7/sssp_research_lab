# Packaging

The Python package and the optional Rust extension are packaged separately. The
Python package remains usable without Rust; the extension only adds accelerated
CSR kernels when it is installed or copied into the source checkout.

## Python-only runtime install

Use this when running examples, the installed CLI, or benchmark scripts without
the optional Rust extension:

```bash
python -m pip install -e .
sssp-benchmark --nodes 1000 --edges 5000
```

## Python-only development install

Use this when working on correctness reference implementations or docs:

```bash
python -m pip install -e . pytest ruff mypy
python -m pytest
```

The Rust-backed tests skip automatically when `sssp_lab._sssp_accel` is absent.

## Local Rust extension for benchmarks

Use this when benchmarking from the repository checkout:

```bash
python -m pip install -e . maturin pytest
python scripts/build_rust_extension.py --install-source
python -m pytest tests/test_rust_accel.py
python scripts/benchmark_rust_accel.py --require-rust
```

`--install-source` copies the compiled extension from the generated wheel into
`src/sssp_lab`, which lets editable installs and direct source-tree commands
import `sssp_lab._sssp_accel`.

## Build an extension wheel

Use this when producing a wheel artifact for the current platform and Python ABI:

```bash
python -m pip install maturin
python scripts/build_rust_extension.py
```

The generated wheel is written under `rust/sssp_accel/target/wheels`. Install it
into an environment that already has the Python package available:

```bash
python -m pip install -e .
python -m pip install rust/sssp_accel/target/wheels/*.whl
```

The wheel is platform-specific because it contains a compiled extension. Build
one wheel per target platform, Python ABI, and architecture.
