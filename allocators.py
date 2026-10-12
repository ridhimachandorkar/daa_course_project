"""Allocation strategies for a capacitated canal graph."""
from maxflow import max_flow


def maxflow_only(net):
    """Run Edmonds–Karp and return farm allocations. O(V E^2) time, O(V+E) space."""
    _, flow=max_flow(net["capacities"],net["source"],net["sink"])
    return {f:flow.get((f,net["sink"]),0.0) for f in net["farms"]}


def fixed_rotation(net, order=None):
    """Prioritize farms sequentially, retaining earlier service. O(F V E^2) time, O(V+E) space."""
    caps=net["capacities"].copy(); result={f:0.0 for f in net["farms"]}
    for farm in (order or net["farms"]):
        trial=caps.copy()
        for f in net["farms"]:
            if f != farm: trial[(f,net["sink"])]=0.0
        amount,flow=max_flow(trial,net["source"],net["sink"])
        result[farm]=amount
        # Consume the channels used in this rotation slot.
        for edge,used in flow.items():
            if edge in caps and edge[1] != net["sink"]: caps[edge]=max(0.0,caps[edge]-used)
        caps[(farm,net["sink"])]=0.0
    return result


def max_min_fair(net, iterations=50):
    """Progressive common-level feasibility search; O((F I+F^2) V E^2) time, O(V+E) space."""
    farms=net["farms"]; demands=net["demands"]; caps=net["capacities"]
    fixed={}; active=set(farms)
    reachable={net["source"]}; stack=[net["source"]]; adjacency={}
    for (u,v),cap in caps.items():
        if cap>1e-10 and v != net["sink"]: adjacency.setdefault(u,[]).append(v)
    while stack:
        u=stack.pop()
        for v in adjacency.get(u,[]):
            if v not in reachable: reachable.add(v); stack.append(v)
    for f in farms:
        if f not in reachable: fixed[f]=0.0; active.discard(f)
    # Allocate common rate, freezing demand-satisfied farms or bottlenecked farms.
    while active:
        lo=0.0; hi=max(demands.values())
        for _ in range(iterations):
            mid=(lo+hi)/2
            trial=caps.copy()
            for f in farms: trial[(f,net["sink"])]=fixed.get(f,min(mid,demands[f])) if f not in active else min(mid,demands[f])
            feasible,_=max_flow(trial,net["source"],net["sink"])
            target=sum(trial[(f,net["sink"])] for f in farms)
            if feasible+1e-8 >= target: lo=mid
            else: hi=mid
        level=lo
        newly=[f for f in active if demands[f] <= level+1e-7]
        # Test each active farm separately above the common level. Freezing all
        # farms when a joint increase fails can strand capacity on other branches.
        for candidate in active:
            trial=caps.copy()
            for f in farms:
                trial[(f,net["sink"])]=fixed.get(f,min(level,demands[f])) if f not in active else min(level,demands[f])
            trial[(candidate,net["sink"])]=min(level+1e-5,demands[candidate])
            feasible,_=max_flow(trial,net["source"],net["sink"])
            target=sum(trial[(f,net["sink"])] for f in farms)
            if feasible+1e-8 < target: newly.append(candidate)
        if not newly: newly=[min(active)]
        for f in newly: fixed[f]=min(level,demands[f]); active.remove(f)
    return fixed
