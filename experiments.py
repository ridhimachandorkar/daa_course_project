"""Reproducible experiments and CSV/PNG output."""
import csv, math, statistics, time
import random
from pathlib import Path
from graph import synthetic_network, load_nwic_geojson
from allocators import maxflow_only,fixed_rotation,max_min_fair
from metrics import evaluate

METHODS={"maxflow":maxflow_only,"rotation":fixed_rotation,"fair":max_min_fair}


def scenario(net, fraction):
    """Return a network with a specified source supply. O(E) time/space."""
    out={**net,"capacities":net["capacities"].copy()}; demand=sum(net["demands"].values()); supply=demand*fraction
    source_edges=[e for e in out["capacities"] if e[0]==net["source"]]; old=sum(out["capacities"][e] for e in source_edges)
    if old:
        for e in source_edges: out["capacities"][e]=out["capacities"][e]/old*supply
    return out,supply


def run_experiments(outdir=None, repetitions=30, dataset=None):
    """Run requested comparisons and write raw summary CSVs/plots. Complexity depends on runs and method."""
    project_dir=Path(__file__).resolve().parent
    dest=Path(outdir) if outdir else project_dir/"results"; dest.mkdir(parents=True,exist_ok=True); rows=[]
    official=Path(dataset) if dataset else project_dir/"data"/"canal_network.geojson"
    if not official.exists(): raise FileNotFoundError(f"Government dataset required: {official}; download the NWIC/CWC Canal Network GeoJSON (see README).")
    base=load_nwic_geojson(official,farms=50,max_nodes=100)
    for seed in range(repetitions):
        # Government canal geometry is fixed. Seeds only affect any algorithm tie ordering, never the observations.
        total=sum(base["demands"].values())
        for season,fraction in (("dry",.5),("normal",.9),("monsoon",1.3)):
            net,supply=scenario(base,fraction)
            net["farms"]=net["farms"].copy(); random.Random(seed).shuffle(net["farms"])
            for name,fn in METHODS.items():
                start=time.perf_counter(); allocation=fn(net); elapsed=(time.perf_counter()-start)*1000
                m=evaluate(net,allocation,supply,elapsed)
                rows.append({"seed":seed,"season":season,"method":name,**{k:v for k,v in m.items() if not isinstance(v,dict)}})
    with (dest/"seasonal_metrics.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    aggregate=[]
    for season in ("dry","normal","monsoon"):
        for name in METHODS:
            subset=[r for r in rows if r["season"]==season and r["method"]==name]
            for metric in ("delivered","throughput_efficiency","wastage_pct","jain","min_satisfaction","head_tail_gap","runtime_ms"):
                values=[r[metric] for r in subset]
                aggregate.append({"season":season,"method":name,"metric":metric,"mean":statistics.mean(values),"stddev":statistics.stdev(values) if len(values)>1 else 0.0,"n":len(values)})
    with (dest/"seasonal_summary.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=aggregate[0].keys());w.writeheader();w.writerows(aggregate)
    growth=[]
    for farms in (10,25,50,100,200):
        # Controlled generated graphs isolate algorithm scaling; these are not observations from the government dataset.
        net=synthetic_network(farms,0); net,supply=scenario(net,.6)
        for name,fn in METHODS.items():
            start=time.perf_counter(); fn(net); growth.append({"farms":farms,"method":name,"runtime_ms":(time.perf_counter()-start)*1000})
    with (dest/"scalability.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=growth[0].keys());w.writeheader();w.writerows(growth)
    sensitivity=[]
    for fraction in (i/100 for i in range(30,121,10)):
        net0=synthetic_network(50,0); net,supply=scenario(net0,fraction)
        for name,fn in METHODS.items():
            m=evaluate(net,fn(net),supply); sensitivity.append({"supply_fraction":fraction,"method":name,"jain":m["jain"],"min_satisfaction":m["min_satisfaction"]})
    with (dest/"sensitivity.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=sensitivity[0].keys());w.writeheader();w.writerows(sensitivity)
    try:
        import matplotlib.pyplot as plt
        methods=list(METHODS)
        fig,ax=plt.subplots();
        for name in methods:
            vals=[statistics.mean(r["jain"] for r in rows if r["method"]==name and r["season"]==s) for s in ("dry","normal","monsoon")]
            ax.plot(("dry","normal","monsoon"),vals,marker="o",label=name)
        ax.set_ylabel("Jain fairness");ax.legend();fig.savefig(dest/"fairness.png",dpi=150);plt.close(fig)
        dry=[r for r in rows if r["season"]=="dry"]
        fig,ax=plt.subplots()
        labels=[]
        for name in methods:
            sub=[r for r in dry if r["method"]==name]; labels.append(name)
        xs=range(len(methods)); width=.35
        ax.bar([x-width/2 for x in xs],[statistics.mean(r["head_tail_gap"] for r in dry if r["method"]==name) for name in methods],width,label="Head minus tail")
        ax.set_xticks(list(xs),methods);ax.set_ylabel("Mean satisfaction gap");ax.legend();fig.savefig(dest/"head_tail.png",dpi=150);plt.close(fig)
        fig,ax=plt.subplots()
        for name in methods:
            items=[r for r in growth if r["method"]==name];ax.plot([r["farms"] for r in items],[max(r["runtime_ms"],.001) for r in items],marker="o",label=name)
        ax.set_xscale("log");ax.set_yscale("log");ax.set_xlabel("Farms");ax.set_ylabel("Runtime (ms)");ax.legend();fig.savefig(dest/"scalability.png",dpi=150);plt.close(fig)
        # Empirical curve compared with a V*E^2 reference normalized at the smallest size.
        fig,ax=plt.subplots()
        ref_sizes=[10,25,50,100,200]; ref=[s**3 for s in ref_sizes]
        scale=max(r["runtime_ms"] for r in growth if r["method"]=="maxflow")/ref[-1]
        ax.plot(ref_sizes,[x*scale for x in ref],"k--",label="V E² reference (normalized)")
        for name in methods:
            items=[r for r in growth if r["method"]==name];ax.plot([r["farms"] for r in items],[max(r["runtime_ms"],.001) for r in items],marker="o",label=name)
        ax.set_xscale("log");ax.set_yscale("log");ax.set_xlabel("Farms");ax.set_ylabel("Runtime (ms)");ax.legend();fig.savefig(dest/"growth_bound.png",dpi=150);plt.close(fig)
        fig,ax=plt.subplots()
        for name in methods:
            items=[r for r in sensitivity if r["method"]==name];ax.plot([r["supply_fraction"] for r in items],[r["jain"] for r in items],label=name)
        ax.set_xlabel("Supply / demand");ax.set_ylabel("Jain fairness");ax.legend();fig.savefig(dest/"sensitivity.png",dpi=150);plt.close(fig)
        fig,ax=plt.subplots()
        for name in methods:
            items=[r for r in sensitivity if r["method"]==name];ax.plot([r["supply_fraction"] for r in items],[r["min_satisfaction"] for r in items],label=name)
        ax.set_xlabel("Supply / demand");ax.set_ylabel("Minimum satisfaction");ax.legend();fig.savefig(dest/"sensitivity_min.png",dpi=150);plt.close(fig)
    except ImportError: pass
    return rows,growth,sensitivity
