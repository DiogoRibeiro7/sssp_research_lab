# BMSSP and the Sorting Barrier

The sorting barrier asks whether shortest-path algorithms must pay for a global
ordering structure in the style of Dijkstra's priority queue.

Bounded multi-source shortest paths are one way to study that question. Instead
of globally settling every tentative label, a bounded subproblem starts from
several sources and explores only labels below a bound. Labels at or beyond the
bound become the frontier for later work.

The repository currently implements that bounded subproblem, including source
offsets, frontier exposure, counters, debug invariant checks, and a finite-bound
recursive scaffold that composes bounded subproblems through frontier labels. It
does not implement the proof-level BMSSP data structures from the paper.

That distinction matters. The Python code is useful for testing invariants and
for comparing frontier behavior against Dijkstra, but it still uses heap-based
bounded exploration internally. It therefore makes no asymptotic claim about
breaking the sorting barrier.
