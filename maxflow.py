"""Edmonds–Karp max flow implementation."""
from collections import deque
from typing import Hashable

Node = Hashable


def max_flow(capacities: dict[tuple[Node, Node], float], source: Node, sink: Node) -> tuple[float, dict[tuple[Node, Node], float]]:
    """Return max flow and directed edge flows. Time O(V E^2), space O(V+E)."""
    residual: dict[Node, list[list]] = {}
    original: dict[tuple[Node, Node], tuple[float, list]] = {}
    for (u, v), cap in capacities.items():
        if cap < 0:
            raise ValueError("capacities must be nonnegative")
        residual.setdefault(u, [])
        residual.setdefault(v, [])
        forward = [v, len(residual[v]) + (1 if u == v else 0), float(cap)]
        reverse = [u, len(residual[u]), 0.0]
        residual[u].append(forward)
        residual[v].append(reverse)
        original[(u, v)] = (float(cap), forward)
    value = 0.0
    if source == sink:
        return value, {edge: 0.0 for edge in original}
    while True:
        parent: dict[Node, tuple[Node, int] | None] = {source: None}
        q = deque([source])
        while q and sink not in parent:
            u = q.popleft()
            for i, edge in enumerate(residual.get(u, [])):
                v, _, cap = edge
                if cap > 1e-10 and v not in parent:
                    parent[v] = (u, i)
                    q.append(v)
        if sink not in parent:
            break
        delta = float("inf")
        v = sink
        while parent[v] is not None:
            u, i = parent[v]
            delta = min(delta, residual[u][i][2])
            v = u
        v = sink
        while parent[v] is not None:
            u, i = parent[v]
            edge = residual[u][i]
            edge[2] -= delta
            residual[v][edge[1]][2] += delta
            v = u
        value += delta
    flows = {}
    for edge, (cap, forward) in original.items():
        flows[edge] = max(0.0, cap - forward[2])
    return value, flows
