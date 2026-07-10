use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use std::cmp::Ordering;
use std::collections::{BinaryHeap, VecDeque};

#[derive(Clone, Copy, Debug, PartialEq)]
struct State {
    cost: f64,
    node: usize,
}

impl Eq for State {}

impl Ord for State {
    fn cmp(&self, other: &Self) -> Ordering {
        other
            .cost
            .total_cmp(&self.cost)
            .then_with(|| other.node.cmp(&self.node))
    }
}

impl PartialOrd for State {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

fn validate_offsets(node_count: usize, offsets: &[usize]) -> PyResult<()> {
    if offsets.len() != node_count + 1 {
        return Err(PyValueError::new_err("offsets length must be node_count + 1"));
    }
    if offsets.windows(2).any(|pair| pair[0] > pair[1]) {
        return Err(PyValueError::new_err("offsets must be monotone"));
    }
    Ok(())
}

fn validate_targets(node_count: usize, edge_count: usize, targets: &[usize]) -> PyResult<()> {
    if targets.len() != edge_count {
        return Err(PyValueError::new_err("targets length must match weights length"));
    }
    if targets.iter().any(|&target| target >= node_count) {
        return Err(PyValueError::new_err("target index out of range"));
    }
    Ok(())
}

#[pyfunction]
fn dijkstra_csr(
    node_count: usize,
    offsets: Vec<usize>,
    targets: Vec<usize>,
    weights: Vec<f64>,
    source: usize,
) -> PyResult<(Vec<f64>, Vec<Option<usize>>)> {
    validate_offsets(node_count, &offsets)?;
    validate_targets(node_count, weights.len(), &targets)?;
    if source >= node_count {
        return Err(PyValueError::new_err("source index out of range"));
    }
    if weights
        .iter()
        .any(|weight| !weight.is_finite() || *weight < 0.0)
    {
        return Err(PyValueError::new_err("weights must be finite and non-negative"));
    }
    if offsets[node_count] != targets.len() {
        return Err(PyValueError::new_err("final offset must equal edge count"));
    }

    let mut distances = vec![f64::INFINITY; node_count];
    let mut predecessors = vec![None; node_count];
    let mut heap = BinaryHeap::new();
    distances[source] = 0.0;
    heap.push(State {
        cost: 0.0,
        node: source,
    });

    while let Some(State { cost, node }) = heap.pop() {
        if cost != distances[node] {
            continue;
        }
        for edge_index in offsets[node]..offsets[node + 1] {
            let target = targets[edge_index];
            let candidate = cost + weights[edge_index];
            if candidate < distances[target] {
                distances[target] = candidate;
                predecessors[target] = Some(node);
                heap.push(State {
                    cost: candidate,
                    node: target,
                });
            }
        }
    }

    Ok((distances, predecessors))
}

#[pyfunction]
fn dial_circular_csr(
    node_count: usize,
    offsets: Vec<usize>,
    targets: Vec<usize>,
    weights: Vec<u64>,
    source: usize,
) -> PyResult<(Vec<f64>, Vec<Option<usize>>)> {
    validate_offsets(node_count, &offsets)?;
    validate_targets(node_count, weights.len(), &targets)?;
    if source >= node_count {
        return Err(PyValueError::new_err("source index out of range"));
    }
    if offsets[node_count] != targets.len() {
        return Err(PyValueError::new_err("final offset must equal edge count"));
    }

    let max_weight = weights.iter().copied().max().unwrap_or(0);
    let width_u64 = max_weight
        .checked_add(1)
        .ok_or_else(|| PyValueError::new_err("maximum weight is too large"))?;
    let width: usize = width_u64
        .try_into()
        .map_err(|_| PyValueError::new_err("bucket width does not fit usize"))?;
    if width > 10_000_000 {
        return Err(PyValueError::new_err("bucket width is too large for circular Dial"));
    }

    let mut distances = vec![u64::MAX; node_count];
    let mut predecessors = vec![None; node_count];
    let mut buckets: Vec<VecDeque<usize>> = (0..width).map(|_| VecDeque::new()).collect();
    distances[source] = 0;
    buckets[0].push_back(source);

    let mut active_entries = 1usize;
    let mut current_distance = 0u64;
    while active_entries > 0 {
        let bucket_index = (current_distance % width_u64) as usize;
        if buckets[bucket_index].is_empty() {
            current_distance = current_distance
                .checked_add(1)
                .ok_or_else(|| PyValueError::new_err("distance overflow"))?;
            continue;
        }

        let node = buckets[bucket_index]
            .pop_front()
            .expect("bucket was checked as non-empty");
        active_entries -= 1;
        if distances[node] != current_distance {
            continue;
        }

        for edge_index in offsets[node]..offsets[node + 1] {
            let target = targets[edge_index];
            let candidate = current_distance
                .checked_add(weights[edge_index])
                .ok_or_else(|| PyValueError::new_err("distance overflow"))?;
            if candidate < distances[target] {
                distances[target] = candidate;
                predecessors[target] = Some(node);
                let target_bucket = (candidate % width_u64) as usize;
                buckets[target_bucket].push_back(target);
                active_entries += 1;
            }
        }
    }

    let float_distances = distances
        .into_iter()
        .map(|distance| {
            if distance == u64::MAX {
                f64::INFINITY
            } else {
                distance as f64
            }
        })
        .collect();
    Ok((float_distances, predecessors))
}

#[pymodule]
fn _sssp_accel(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(dijkstra_csr, module)?)?;
    module.add_function(wrap_pyfunction!(dial_circular_csr, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{dial_circular_csr, dijkstra_csr};

    #[test]
    fn dijkstra_handles_shortest_path() {
        let offsets = vec![0, 2, 3, 4, 4];
        let targets = vec![1, 2, 2, 3];
        let weights = vec![2.0, 5.0, 1.0, 3.0];

        let (distances, predecessors) = dijkstra_csr(4, offsets, targets, weights, 0).unwrap();

        assert_eq!(distances, vec![0.0, 2.0, 3.0, 6.0]);
        assert_eq!(predecessors[3], Some(2));
    }

    #[test]
    fn circular_dial_handles_integer_weights() {
        let offsets = vec![0, 2, 3, 4, 4];
        let targets = vec![1, 2, 2, 3];
        let weights = vec![2, 5, 1, 3];

        let (distances, predecessors) = dial_circular_csr(4, offsets, targets, weights, 0).unwrap();

        assert_eq!(distances, vec![0.0, 2.0, 3.0, 6.0]);
        assert_eq!(predecessors[3], Some(2));
    }

    #[test]
    fn rejects_negative_dijkstra_weight() {
        let result = dijkstra_csr(2, vec![0, 1, 1], vec![1], vec![-1.0], 0);

        assert!(result.is_err());
    }
}
