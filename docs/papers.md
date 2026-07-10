# Paper Map

This repository is organized around shortest-path algorithms where the central question is ordering: which labels must be ordered, which can be bucketed, which can be delayed, and which can be moved to preprocessing?

## 1. Breaking the Sorting Barrier for Directed SSSP

**Paper:** Ran Duan, Jiayi Mao, Xiao Mao, Xinkai Shu, Longhui Yin. *Breaking the Sorting Barrier for Directed Single-Source Shortest Paths*. arXiv:2504.17033, 2025.

**Repo mapping:**

- `algorithms/bmssp.py`
- `algorithms/frontier_sssp.py`
- `prompts/05_research_frontier_bmssp_prompt.md`

**Implementation note:** The repo includes a bounded multi-source primitive and a frontier experiment. It does not claim to be a proof-level implementation of the complete recursive BMSSP algorithm.

## 2. A Faster Directed Single-Source Shortest Path Algorithm

**Paper:** Ran Duan, Xiao Mao, Xinkai Shu, Longhui Yin. *A Faster Directed Single-Source Shortest Path Algorithm*. arXiv:2602.07868, 2026.

**Repo mapping:**

- `algorithms/frontier_sssp.py`
- `prompts/06_faster_directed_sssp_prompt.md`

**Implementation note:** The repository treats this as a research extension. The current code is an experimental frontier-partition baseline.

## 3. Δ-stepping

**Paper:** Ulrich Meyer, Peter Sanders. *Δ-stepping: a parallelizable shortest path algorithm*. Journal of Algorithms, 2003.

**Repo mapping:**

- `algorithms/delta_stepping.py`
- `algorithms/stepping_variants.py`
- `prompts/02_delta_stepping_prompt.md`

## 4. Efficient stepping algorithms

**Paper:** Xiaojin Dong et al. *Efficient Stepping Algorithms and Implementations for Parallel Shortest Paths*. SPAA 2021.

**Repo mapping:**

- `algorithms/stepping_variants.py`
- `prompts/03_stepping_variants_prompt.md`

## 5. Radix heaps and integer queues

**Paper family:** Ahuja, Mehlhorn, Orlin, Tarjan and related integer-priority shortest-path algorithms.

**Repo mapping:**

- `algorithms/radix_heap.py`
- `algorithms/dijkstra_radix.py`
- `algorithms/dial.py`
- `prompts/04_radix_buckets_prompt.md`

## 6. Thorup integer undirected SSSP

**Paper:** Mikkel Thorup. *Undirected Single-Source Shortest Paths with Positive Integer Weights in Linear Time*. JACM, 1999.

**Repo mapping:**

- `algorithms/thorup_like.py`
- `prompts/07_thorup_integer_sssp_prompt.md`

**Implementation note:** The current module is a lab scaffold and integer baseline. The full component hierarchy is not yet implemented.

## 7. ALT

**Paper:** Andrew V. Goldberg, Chris Harrelson. *Computing the Shortest Path: A* Search Meets Graph Theory*. SODA 2005.

**Repo mapping:**

- `algorithms/alt.py`
- `prompts/08_alt_prompt.md`

## 8. Contraction Hierarchies

**Paper:** Robert Geisberger, Peter Sanders, Dominik Schultes, Daniel Delling. *Contraction Hierarchies: Faster and Simpler Hierarchical Routing in Road Networks*. WEA 2008.

**Repo mapping:**

- `algorithms/contraction_hierarchies.py`
- `prompts/09_contraction_hierarchies_prompt.md`

## 9. Negative-weight near-linear SSSP

**Paper:** Aaron Bernstein, Danupon Nanongkai, Christian Wulff-Nilsen. *Negative-Weight Single-Source Shortest Paths in Near-linear Time*. FOCS 2022 / arXiv:2203.03456.

**Repo mapping:**

- `algorithms/negative_weight.py`
- `prompts/10_negative_weight_near_linear_prompt.md`

**Implementation note:** Current code provides Bellman-Ford and Johnson reweighting baselines. The near-linear randomized algorithm is a research task.
