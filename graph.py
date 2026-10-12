"""Canal graph construction and NWIC Government of India GeoJSON loading."""
from __future__ import annotations
import json, math, random
from pathlib import Path
from typing import Any

SOURCE, SINK = "SOURCE", "SINK"


def synthetic_network(farms: int, seed: int = 0, branching: int = 3) -> dict[str, Any]:
    """Build a reproducible test network. Time/space O(farms). Values are synthetic."""
    if farms < 1: raise ValueError("farms must be positive")
    rng = random.Random(seed)
    capacities: dict[tuple[str, str], float] = {}
    demands = {f"F{i}": max(1.0, rng.lognormvariate(1.0, .35)) for i in range(farms)}
    total_demand=sum(demands.values())
    nodes = [SOURCE]
    # A shallow tree with deterministic branch assignment.
    for i, farm in enumerate(demands):
        branch = f"B{i // max(1, branching)}"
        if branch not in nodes:
            nodes.append(branch); capacities[(SOURCE, branch)] = total_demand * 2
        capacities[(branch, farm)] = demands[farm] * 1.2
        capacities[(farm, SINK)] = demands[farm]
        nodes.append(farm)
    return {"capacities": capacities, "demands": demands, "farms": list(demands), "distance": {f: 2 for f in demands}, "source": SOURCE, "sink": SINK, "nodes": nodes, "synthetic": True}


def load_nwic_geojson(path: str | Path, snap_m: float = 50.0, farms: int = 50, max_nodes: int = 100) -> dict[str, Any]:
    """Load a bounded NWIC/CWC topology; geometry observed, model values synthetic. O(E log V) time, O(V+E) space."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    features = raw.get("features", [])
    if not features: raise ValueError("GeoJSON has no features")
    # GeoJSON coordinates are longitude/latitude. Equirectangular snapping is adequate only for local sub-networks.
    coords: dict[tuple[int, int], str] = {}
    edges: list[tuple[str, str, float]] = []
    def first_point(geom):
        pts=geom.get("coordinates",[])
        while pts and isinstance(pts[0],list): pts=pts[0]
        return pts if len(pts)>=2 and isinstance(pts[0],(int,float)) else None
    latitudes=[pt[1] for f in features if f.get("geometry") and (pt:=first_point(f["geometry"]))]
    if not latitudes: raise ValueError("GeoJSON has no valid coordinate lines")
    mean_lat = sum(latitudes) / len(latitudes)
    sx = 111320 * math.cos(math.radians(mean_lat)); sy = 110540
    def node(pt: list[float]) -> str:
        key = (round(pt[0] * sx / snap_m), round(pt[1] * sy / snap_m))
        if key not in coords: coords[key] = f"N{len(coords)}"
        return coords[key]
    for f in features:
        geom = f.get("geometry") or {}
        lines = [geom.get("coordinates", [])] if geom.get("type") == "LineString" else geom.get("coordinates", []) if geom.get("type") == "MultiLineString" else []
        for line in lines:
            for a, b in zip(line, line[1:]):
                u, v = node(a), node(b)
                if u != v: edges.append((u, v, math.hypot((b[0]-a[0])*sx, (b[1]-a[1])*sy)))
    if not edges: raise ValueError("No line segments found in GeoJSON")
    # Use a bounded BFS section of the largest component so the student algorithms remain tractable.
    adj: dict[str, set[str]] = {}
    for u,v,_ in edges: adj.setdefault(u,set()).add(v); adj.setdefault(v,set()).add(u)
    comps=[]; seen=set()
    for n in adj:
        if n not in seen:
            stack=[n]; seen.add(n); comp=[]
            while stack:
                x=stack.pop(); comp.append(x)
                for y in adj[x]-seen: seen.add(y); stack.append(y)
            comps.append(comp)
    largest=set(max(comps,key=len)); root=min(largest); comp={root}; queue=[root]
    while queue and len(comp)<max_nodes:
        u=queue.pop(0)
        for v in sorted(adj[u]):
            if v in largest and v not in comp and len(comp)<max_nodes: comp.add(v); queue.append(v)
    selected=[e for e in edges if e[0] in comp and e[1] in comp]
    undirected=[]; reached={root}; queue=[root]; depth={root:0}
    while queue:
        u=queue.pop(0)
        for v in sorted(adj[u]):
            if v in comp and v not in reached: reached.add(v); queue.append(v); depth[v]=depth[u]+1; undirected.append((u,v))
    # Orient a spanning tree away from an arbitrary root; real canal flow direction is not inferred.
    capacities={}
    for u,v in undirected: capacities[(u,v)]=100.0
    # Taps are model inputs attached to selected real canal nodes; the source contains no farm outlet inventory.
    taps=sorted(comp-{root})[:min(farms,len(comp)-1)]
    farms={f"F{i}": 10.0 for i,_ in enumerate(taps)}
    distances={}
    for i,tap in enumerate(taps): capacities[(tap,f"F{i}")]=10.0; distances[f"F{i}"]=depth[tap]
    for farm in farms: capacities[(farm,SINK)]=10.0
    capacities[(SOURCE,root)]=100.0
    return {"capacities":capacities,"demands":farms,"farms":list(farms),"distance":distances,"source":SOURCE,"sink":SINK,"nodes":[SOURCE,*sorted(comp),*farms,SINK],"synthetic":False,"topology_source":"NWIC/CWC Canal Network GeoJSON","topology_edges":len(selected),"topology_nodes":len(comp),"snap_m":snap_m,"capacity_assignment":"synthetic uniform 100 ML/day per modeled canal segment","demand_assignment":"synthetic uniform 10 ML/day per modeled tap"}
