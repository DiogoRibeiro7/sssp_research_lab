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
For repeated queries, prefer `RustSsspWorkspace.from_graph(graph)`: it validates
non-negative weights, builds CSR once, caches integer weights when possible, and
then exposes single-source and batched Dijkstra/circular-Dial methods.

## Local Build

From the repository root:

```bash
python -m pip install maturin
python scripts/build_rust_extension.py --install-source
```

Then run:

```bash
python -m pytest tests/test_rust_accel.py
python scripts/benchmark_rust_accel.py --require-rust
```

Without the extension installed, the wrapper raises `RustBackendUnavailable` and
the optional kernel tests are skipped.

The benchmark script writes JSON, CSV, and markdown rows comparing Python and Rust
implementations. Without `--require-rust`, it still writes Python-only baseline
rows so benchmark automation can run before the optional wheel is installed.
When the Rust backend is installed, the output includes both end-to-end wrapper
rows and `*_csr_reused` rows that reuse one prebuilt CSR graph. This separates
conversion overhead from kernel runtime for repeated-query experiments.
Use `--sources N` to run several deterministic source nodes and report both
total runtime and `seconds_per_source`. The `*_csr_batch` rows call Rust once
with every source to measure Python call overhead separately from kernel work.
Rows with matching Python baselines include `speedup_vs_python`.

CI builds the maturin wheel in a dedicated job and copies the compiled extension
into `src/sssp_lab` with `scripts/install_built_rust_extension.py` before running
the integration tests.

See `docs/packaging.md` for Python-only installs, local extension builds, and
wheel installation commands. For source-checkout benchmarking, use:

```bash
python scripts/build_rust_extension.py --install-source
```

## Design Boundary

The Rust backend is deliberately optional. It should not replace Python tests or
the clear reference implementations. Any new Rust kernel must be validated
against the Python algorithm on the same graph inputs.

The API boundary is:

- Python owns `Graph` validation, CSR construction, arbitrary node-id mapping,
  and `PathResult` materialization.
- Rust owns kernels over already-prepared CSR arrays, including loops over
  batched source nodes when call overhead matters.
- End-to-end convenience wrappers such as `dijkstra_rust(graph, source)` remain
  available, but benchmark and production-style repeated-query code should use
  `RustSsspWorkspace` to avoid rebuilding graph data for every source.

This keeps the correctness surface inspectable in Python while moving the
highest-payoff inner loops and repeated-source execution into Rust.
