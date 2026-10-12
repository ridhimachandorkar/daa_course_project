"""Command line entry point."""
import argparse, json, time
from pathlib import Path
from graph import synthetic_network, load_nwic_geojson
from experiments import METHODS, run_experiments, scenario
from metrics import evaluate


def main():
    default_dataset=Path(__file__).resolve().parent/"data"/"canal_network.geojson"
    p=argparse.ArgumentParser();p.add_argument("--farms",type=int,default=50);p.add_argument("--season",choices=("dry","normal","monsoon"),default="dry");p.add_argument("--seed",type=int,default=0);p.add_argument("--method",choices=(*METHODS,"all"),default="all");p.add_argument("--run-all",action="store_true");p.add_argument("--dataset",default=str(default_dataset),help="Path to NWIC/CWC Canal Network GeoJSON");p.add_argument("--synthetic",action="store_true",help="Explicitly use generated topology instead of the government geometry")
    a=p.parse_args()
    if a.run_all: run_experiments(dataset=a.dataset); return
    if a.synthetic: net=synthetic_network(a.farms,a.seed)
    elif Path(a.dataset).exists(): net=load_nwic_geojson(a.dataset,farms=a.farms)
    else: p.error(f"Government GeoJSON not found at {a.dataset}; pass --synthetic only for generated experiments.")
    fraction={"dry":.5,"normal":.9,"monsoon":1.3}[a.season];net,supply=scenario(net,fraction)
    for name in METHODS if a.method=="all" else (a.method,):
        t=time.perf_counter();alloc=METHODS[name](net);m=evaluate(net,alloc,supply,(time.perf_counter()-t)*1000);print(json.dumps({"method":name,"season":a.season,"data_source":"NWIC/CWC observed topology + synthetic capacities/demands" if not net.get("synthetic") else "synthetic generated network","metrics":m},indent=2))
if __name__=="__main__": main()
