"""Evaluation metrics for farm allocations."""
import math, time


def evaluate(net, allocation, supply, elapsed_ms=0.0):
    """Compute throughput, satisfaction, Jain index, and edge gap. O(F) time/space."""
    farms=net["farms"]; demands=net["demands"]
    ratios=[min(1.0, allocation.get(f,0.0)/demands[f]) if demands[f] else 1.0 for f in farms]
    useful=min(supply,sum(min(demands[f],allocation.get(f,0.0)) for f in farms)) if supply else 0.0
    denom=sum(x*x for x in ratios)
    ordered=sorted(farms,key=lambda f: net.get("distance",{}).get(f, float(f[1:]) if f.startswith("F") and f[1:].isdigit() else 0))
    k=max(1,math.ceil(len(farms)*.2)); head=[allocation.get(f,0)/demands[f] for f in ordered[:k]]; tail=[allocation.get(f,0)/demands[f] for f in ordered[-k:]]
    return {"delivered":useful,"throughput_efficiency":useful/supply if supply else 0.0,"wastage_pct":100*(supply-useful)/supply if supply else 0.0,"satisfaction":{f:allocation.get(f,0)/demands[f] if demands[f] else 1.0 for f in farms},"jain":sum(ratios)**2/(len(ratios)*denom) if denom else 1.0,"min_satisfaction":min(ratios,default=1.0),"head_tail_gap":sum(head)/k-sum(tail)/k,"runtime_ms":elapsed_ms}
