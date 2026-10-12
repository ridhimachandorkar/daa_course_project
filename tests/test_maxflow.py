import random, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from maxflow import max_flow

def test_known_flow():
    value,_=max_flow({("s","a"):3,("s","b"):2,("a","b"):1,("a","t"):2,("b","t"):3},"s","t")
    assert value==5

def test_random_graphs_networkx_crosscheck():
    nx=__import__("pytest").importorskip("networkx")
    for seed in range(100):
        rng=random.Random(seed); n=8; caps={}
        for u in range(n):
            for v in range(n):
                if u!=v and rng.random()<.2: caps[(u,v)]=rng.randint(1,10)
        ours,_=max_flow(caps,0,n-1); g=nx.DiGraph(); g.add_nodes_from(range(n))
        for (u,v),c in caps.items(): g.add_edge(u,v,capacity=c)
        assert ours==nx.maximum_flow_value(g,0,n-1)

def test_zero_supply():
    assert max_flow({("s","t"):0},"s","t")[0]==0

def test_antiparallel_edges_return_conserving_flow():
    caps={("s","a"):3,("a","s"):2,("a","t"):2,("s","t"):1}
    value,flows=max_flow(caps,"s","t")
    assert value==3
    for edge,flow in flows.items(): assert -1e-9<=flow<=caps[edge]+1e-9
    for node in ("a",):
        assert abs(sum(v for (u,w),v in flows.items() if w==node)-sum(v for (u,w),v in flows.items() if u==node))<1e-9
