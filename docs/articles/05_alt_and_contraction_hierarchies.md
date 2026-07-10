# ALT and Contraction Hierarchies

ALT and Contraction Hierarchies both move work from query time to preprocessing.

ALT precomputes distances from selected landmarks. During a query, triangle
inequality gives lower bounds that guide A* search toward the target. Directed
graphs need both distances from landmarks and distances to landmarks, computed
on the reversed graph.

Contraction Hierarchies preprocess shortcuts. Contracting a vertex can add a
shortcut between its neighbors when no equally short witness path avoids that
vertex. Query time then searches upward in the hierarchy from both ends.

Road networks are special because they are sparse, nearly planar, and have
strong hierarchy. Good landmarks and contraction orders can reduce query work
substantially. Random dense graphs usually show less structure.

The repository keeps both modules educational: ALT has reusable landmark
indexes, query stats, and several landmark strategies including avoid-style and
coordinate-corner selection, while CH supports small-graph shortcut unpacking,
static ordering heuristics, and witness-aware dynamic ordering variants.
