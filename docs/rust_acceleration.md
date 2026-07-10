# Rust Acceleration

The Python implementations remain the correctness reference. Rust is introduced
as an optional acceleration layer for hot kernels that operate on compressed
sparse row arrays.

## Current Kernels

The optional PyO3 extension exposes:

- `dijkstra_csr`: non-negative real-weight Dijkstra over CSR arrays.
- `dial_circular_csr`: non-negative integer circular-Dial over CSR arrays.

Python wrappers in `sssp_lab.algorithms.rust_accel` convert the repository's
`Graph` object into CSR arrays and map distances/predecessors back to node ids.

## Local Build

From the extension directory:

```bash
cd rust/sssp_accel
maturin develop
```

Then run:

```bash
python -m pytest tests/test_rust_accel.py
```

Without the extension installed, the wrapper raises `RustBackendUnavailable` and
the optional kernel tests are skipped.

## Design Boundary

The Rust backend is deliberately optional. It should not replace Python tests or
the clear reference implementations. Any new Rust kernel must be validated
against the Python algorithm on the same graph inputs.
