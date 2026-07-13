# BMSSP Implementation Notes

These notes map the current Python scaffold to Duan, Mao, Mao, Shu, and
Yin's 2025 directed SSSP algorithm, "Breaking the Sorting Barrier for Directed
Single-Source Shortest Paths" (arXiv:2504.17033). They are an implementation
plan, not a claim that the current code implements the paper's asymptotic data
structures.

## Paper Scope

The paper gives a deterministic directed SSSP algorithm for non-negative real
edge weights in the comparison-addition model. Its headline bound is
`O(m log^(2/3) n)` on sparse directed graphs after reducing to constant-degree
graphs.

The BMSSP subproblem is the central recursive primitive. Given a level `l`, a
bound `B`, and a frontier/source set `S`, BMSSP returns a smaller or equal
boundary `B'` and a complete set `U` of vertices whose shortest paths pass
through `S` and whose distances are below `B'`. A successful execution returns
`B' = B`; a partial execution returns early after enough work has accumulated.

The current repository implements:

- bounded multi-source exploration below an absolute bound;
- frontier labels carried as absolute source offsets;
- a recursive finite-bound scaffold;
- debug invariant checks and Dijkstra comparison tests.

The current repository does not implement:

- the paper's `FindPivots` frontier-reduction routine;
- the `BaseCase` routine as a distinct level-zero BMSSP block;
- the block/list data structure with `Insert`, `BatchPrepend`, and `Pull`;
- the constant-degree graph transformation;
- the proof-level partial-execution stopping rule;
- the comparison-addition tie-ordering machinery for equal path lengths;
- the claimed `O(m log^(2/3) n)` running time.

## Parameters

The paper chooses two global parameters:

```python
k = floor(log(n) ** (1 / 3))
t = floor(log(n) ** (2 / 3))
max_level = ceil(log(n) / t)
```

The level invariant is that a BMSSP call at level `l` receives a source set
whose size is bounded by about `2 ** (l * t)`. Recursive calls use level
`l - 1` and pull only about `2 ** ((l - 1) * t)` frontier vertices at a time.

In Python, these values should be derived by a small configuration helper and
kept visible in diagnostics. For small graphs the helper must clamp `k`, `t`,
and level sizes to at least one; otherwise the theoretical formulas degenerate.

## Core State

The paper maintains global tentative labels and predecessors:

```python
labels: dict[Node, float]          # always >= true distance
predecessors: dict[Node, Node | None]
complete: set[Node]                # vertices whose labels are certified exact
relaxed: set[Node]                 # complete vertices whose outgoing edges were relaxed
```

The current code's per-call `distances` maps are correct for the scaffold, but
a faithful driver should share one label map across recursive calls. This is
necessary because lower recursive levels can improve labels that upper levels
later re-use.

The paper assumes unique path ordering for presentation. Python should not rely
on float equality or insertion order to emulate this. A practical deterministic
tie key can be:

```python
LabelKey = tuple[float, int, Node, tuple[Node, ...]]
```

For the research implementation, storing full paths in the key is acceptable
for clarity but not for asymptotic claims. A later optimized version would need
the paper's predecessor-depth tie handling.

## FindPivots

Purpose: shrink the frontier `S` before recursion so that lower levels do not
effectively sort all frontier vertices.

Paper idea:

1. Run `k` Bellman-Ford-like bounded relaxation rounds from `S`.
2. Track reached vertices `W` with labels below `B`.
3. If the reached set grows too large, return early with no pivot shrink.
4. Otherwise, build the predecessor forest induced by the relaxed labels.
5. Select pivots: roots in `S` whose induced subtree has size at least `k`.
6. Return `(pivots, W)`.

Typed Python pseudocode:

```python
@dataclass(frozen=True, slots=True)
class PivotResult:
    pivots: frozenset[Node]
    reached: frozenset[Node]
    partial: bool


def find_pivots(
    graph: Graph,
    sources: frozenset[Node],
    *,
    bound: float,
    k: int,
    labels: dict[Node, float],
    predecessors: dict[Node, Node | None],
    stats: OperationStats,
) -> PivotResult:
    reached = set(sources)
    frontier = set(sources)
    for _ in range(k):
        next_frontier: set[Node] = set()
        for node in frontier:
            for edge in graph.neighbors(node):
                candidate = labels[node] + edge.weight
                if candidate <= labels[edge.target] and candidate < bound:
                    labels[edge.target] = candidate
                    predecessors[edge.target] = node
                    next_frontier.add(edge.target)
                    reached.add(edge.target)
        if len(reached) > k * len(sources):
            return PivotResult(
                pivots=frozenset(sources),
                reached=frozenset(reached),
                partial=True,
            )
        frontier = next_frontier

    subtree_sizes = predecessor_forest_subtree_sizes(
        roots=sources,
        reached=reached,
        predecessors=predecessors,
    )
    pivots = frozenset(root for root, size in subtree_sizes.items() if size >= k)
    return PivotResult(pivots=pivots, reached=frozenset(reached), partial=False)
```

Deviation to document when implemented: this sketch mutates labels during pivot
search and uses ordinary Python sets. That is fine for correctness experiments,
but it does not establish the paper's time bound.

## Base Case

Purpose: solve level-zero calls with one source.

Paper idea: when `l == 0`, `S` is a singleton complete vertex. Run a bounded
mini-Dijkstra from that vertex until either about `k` vertices have been found
or the queue crosses `B`.

Typed Python pseudocode:

```python
def bmssp_base_case(
    graph: Graph,
    source: Node,
    *,
    bound: float,
    k: int,
    labels: dict[Node, float],
    predecessors: dict[Node, Node | None],
    complete: set[Node],
    stats: OperationStats,
) -> tuple[float, frozenset[Node]]:
    queue = [(labels[source], source)]
    settled: set[Node] = set()
    next_boundary = bound

    while queue and len(settled) < k + 1:
        distance, node = heappop(queue)
        if distance != labels[node]:
            continue
        if distance >= bound:
            next_boundary = min(next_boundary, distance)
            break
        complete.add(node)
        settled.add(node)
        for edge in graph.neighbors(node):
            candidate = distance + edge.weight
            if candidate <= labels[edge.target] and candidate < bound:
                labels[edge.target] = candidate
                predecessors[edge.target] = node
                heappush(queue, (candidate, edge.target))

    if len(settled) <= k:
        return bound, frozenset(settled)
    return max(labels[node] for node in settled), frozenset(settled)
```

The current `bounded_multi_source_sssp` can emulate this behavior, but a
faithful implementation should expose a separate base-case function so tests
can target the level-zero invariants directly.

## Data Structure

The paper's recursive driver depends on a data structure with:

- `Insert(key, value)`;
- `BatchPrepend(pairs)` where all new values are smaller than existing values;
- `Pull(limit)` returning the keys with the smallest values plus a separating
  upper bound.

Typed Python interface:

```python
class BMSSPQueue:
    def insert(self, node: Node, label: float) -> None: ...
    def batch_prepend(self, labels: dict[Node, float]) -> None: ...
    def pull(self, limit: int) -> tuple[frozenset[Node], float]: ...
    def __bool__(self) -> bool: ...
```

Implementation plan:

1. Start with a correctness-first heap/dictionary implementation.
2. Preserve the same interface in tests.
3. Later replace the internals with a block-list implementation matching the
   paper's `Insert`, `BatchPrepend`, and `Pull` complexity.

The heap/dictionary implementation is allowed to be slower, but it must keep
the same semantic guarantees:

- duplicate keys keep the smallest label;
- `Pull(limit)` removes the returned keys;
- returned `next_bound` separates returned labels from remaining labels;
- empty queue returns `next_bound = inf`.

## Recursive BMSSP Driver

Typed Python pseudocode:

```python
@dataclass(frozen=True, slots=True)
class PaperBMSSPResult:
    boundary: float
    complete_vertices: frozenset[Node]
    partial: bool
    levels: tuple[BMSSPLevel, ...]


def paper_bmssp(
    graph: Graph,
    *,
    level: int,
    bound: float,
    sources: frozenset[Node],
    config: BMSSPConfig,
    labels: dict[Node, float],
    predecessors: dict[Node, Node | None],
    complete: set[Node],
    debug: bool = False,
    stats: OperationStats | None = None,
) -> PaperBMSSPResult:
    if level == 0:
        boundary, settled = bmssp_base_case(...)
        return PaperBMSSPResult(boundary, settled, boundary < bound, levels=(...))

    pivot_result = find_pivots(...)
    queue = BMSSPQueue(bound=bound, block_size=config.block_size)
    for node in pivot_result.pivots:
        queue.insert(node, labels[node])

    complete_here = set(pivot_result.reached)
    current_boundary = min(labels[node] for node in queue) if queue else bound

    while queue and len(complete_here) < config.work_limit(level):
        child_sources, child_bound = queue.pull(config.child_source_limit(level))
        child = paper_bmssp(
            graph,
            level=level - 1,
            bound=child_bound,
            sources=child_sources,
            config=config,
            labels=labels,
            predecessors=predecessors,
            complete=complete,
            debug=debug,
            stats=stats,
        )
        complete_here.update(child.complete_vertices)

        prepend_labels: dict[Node, float] = {}
        for node in child.complete_vertices:
            for edge in graph.neighbors(node):
                candidate = labels[node] + edge.weight
                if candidate <= labels[edge.target]:
                    labels[edge.target] = candidate
                    predecessors[edge.target] = node
                    if candidate < child_bound:
                        queue.insert(edge.target, candidate)
                    elif candidate < bound:
                        prepend_labels[edge.target] = candidate
        queue.batch_prepend(prepend_labels)

        if not queue:
            return PaperBMSSPResult(bound, frozenset(complete_here), False, levels=(...))

    return PaperBMSSPResult(
        current_boundary,
        frozenset(complete_here),
        current_boundary < bound,
        levels=(...),
    )
```

This driver should be introduced under a new name until it is empirically and
structurally ready to replace `recursive_bmssp`.

## Invariants

Debug mode should check these after every major block:

- `labels[node] >= true_distance[node]` for test builds where Dijkstra is
  available as an oracle.
- Every node in `complete` has `labels[node] == true_distance[node]` in oracle
  tests.
- Each returned `U` is complete.
- If a call succeeds, returned boundary equals input `B`.
- If a call is partial, returned boundary is less than `B` and the amount of
  completed work meets the configured threshold.
- Every recursive child uses sources whose labels are finite and less than its
  bound.
- `Pull(limit)` returns the smallest available labels and produces a valid
  separating bound.
- Batch-prepended labels are smaller than the current queue minimum.

## Test Plan

Before replacing current scaffold behavior, add tests in this order:

1. `BMSSPQueue` duplicate-key, pull, empty, and batch-prepend behavior.
2. `find_pivots` on small graphs where pivot subtrees are known exactly.
3. `bmssp_base_case` against Dijkstra on singleton-source bounded searches.
4. `paper_bmssp` on at least 100 random directed non-negative graphs.
5. Layered DAGs with close labels and many ties.
6. Sparse directed graphs with disconnected vertices; the paper assumes
   reachability, but the Python API should preserve `inf` for unreachable
   vertices.
7. Adversarial graphs where many labels fall just below and just above a bound.

## Current Implementation Mapping

| Paper block | Current code | Status |
|---|---|---|
| Global labels and predecessors | Per-call distance/predecessor maps | Needs shared-state driver |
| `FindPivots` | Not present | Open |
| Base case | Emulated by bounded primitive | Needs explicit function |
| `Insert` / `BatchPrepend` / `Pull` | Not present | Open |
| Recursive BMSSP | `recursive_bmssp` finite-bound scaffold | Correct scaffold, not paper driver |
| Partial execution threshold | Frontier/bound exhaustion only | Open |
| Debug proof obligations | Bounded invariants | Needs oracle-assisted paper invariants |

## Next Implementation Step

Add the `BMSSPQueue` interface with a correctness-first heap/dictionary
implementation and tests. This creates the interface needed by the paper driver
without destabilizing the existing bounded primitive.
