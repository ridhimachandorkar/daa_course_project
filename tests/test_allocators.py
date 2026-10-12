import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from graph import synthetic_network
from allocators import maxflow_only,max_min_fair,fixed_rotation
from maxflow import max_flow

def test_satisfaction_and_capacities():
    net=synthetic_network(8,4)
    for method in (maxflow_only,max_min_fair,fixed_rotation):
        result=method(net)
        assert all(-1e-8<=result[f]<=net["demands"][f]+1e-7 for f in net["farms"])

def test_fair_equal_under_shared_bottleneck():
    net={"source":"s","sink":"t","farms":["a","b"],"demands":{"a":5.,"b":5.},"capacities":{("s","x"):4.,("x","a"):5.,("x","b"):5.,("a","t"):5.,("b","t"):5.}}
    a=max_min_fair(net)
    assert abs(a["a"]-2)<1e-5 and abs(a["b"]-2)<1e-5
    for farm in net["farms"]:
        trial=net["capacities"].copy()
        for other in net["farms"]: trial[(other,net["sink"])]=a[other]+(1e-4 if other==farm else 0.0)
        value,_=max_flow(trial,net["source"],net["sink"])
        assert value+1e-8 < sum(trial[(f,net["sink"])] for f in net["farms"])

def test_one_farm_and_excess_supply():
    net=synthetic_network(1,1)
    assert abs(max_min_fair(net)["F0"]-net["demands"]["F0"])<1e-5
    for method in (maxflow_only,max_min_fair,fixed_rotation):
        allocation=method(net)
        assert abs(allocation["F0"]-net["demands"]["F0"])<1e-5

def test_allocations_are_flow_feasible():
    net=synthetic_network(12,2)
    for method in (maxflow_only,max_min_fair,fixed_rotation):
        allocation=method(net); trial=net["capacities"].copy()
        for f in net["farms"]: trial[(f,net["sink"])]=allocation[f]
        value,_=max_flow(trial,net["source"],net["sink"])
        assert value+1e-7 >= sum(allocation.values())

def test_disconnected_farm_and_zero_supply():
    net={"source":"s","sink":"t","farms":["a","b"],"demands":{"a":2.,"b":2.},"capacities":{("s","a"):2.,("a","t"):2.,("b","t"):2.}}
    assert max_min_fair(net)["b"]==0
    net["capacities"][("s","a")]=0
    assert maxflow_only(net)=={"a":0.0,"b":0.0}
