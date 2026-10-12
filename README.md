# Max-Min Fair Canal Water Allocation using Flow Networks

This DAA project compares Edmonds–Karp max-flow, a greedy fixed-order rotation, and progressive max-min allocation on a mapped canal network.

## Government dataset and provenance

The primary topology is the **Canal Network** geospatial layer published by the Central Water Commission on the National Water Data Portal, maintained by the National Water Informatics Centre (NWIC), Ministry of Jal Shakti, Government of India. This repository includes the 233,098,155-byte GeoJSON downloaded from the portal on 12 October 2026 at `data/canal_network.geojson`.

- Dataset page: <https://nwdp.nwic.gov.in/dataset/canal>
- Direct GeoJSON resource: <https://nwdp.nwic.gov.in/dataset/dd11dfc1-6723-4603-9426-a03e4c8cf50c/resource/89bab129-cb30-41ec-8531-e7f445c170f3/download/canal_network.geojson>
- Data producer listed by portal: Central Water Commission (CWC); the portal describes the layer as canals associated with major and medium command areas.
- The source geometry contains canal lines. It does **not** supply operational flow direction, channel capacities, farm outlet inventory, or farm demand values for this model.
- The loader snaps coordinates, selects a bounded connected section, and directs a spanning tree outward from an arbitrary root for algorithm experiments. These are processing choices, not supplied flow directions. Each modeled canal segment is assigned 100 ML/day and each modeled outlet tap demand is assigned 10 ML/day. Both are explicit synthetic assumptions, not official measurements.
- Downloaded source bytes are retained unchanged; verify provenance against the official portal when refreshing the file. No farm-level or flow observations are invented or presented as government data.
- SHA-256 of the included GeoJSON: `069863b439219a085ca43e3e3f83b272ec3e6e0bbe2efd50ebf8970eaae2089f`.

For topology-based runs use the included official data file. If it is absent, `main.py` stops with an actionable error. `--synthetic` is an explicit option for generated test/scalability graphs only. The 10–200 farm scalability experiment uses controlled generated topologies because the government layer does not contain farm outlet records at those sizes.

## Research gap

Max-min fair water-filling is well established in networking (bandwidth allocation, energy-harvesting networks). Irrigation-graph research mostly addresses canal design (which canals to build, at what capacity), not fair operational allocation on an existing network with seasonally varying capacity. This project transplants a proven fairness technique into that unaddressed operational setting.

## Graph model and assumptions

Canal segments are directed edges, farm taps are outlet nodes, and a super-sink connects each farm to an edge capped at its demand. Source supply is set to 50%, 90%, or 130% of total modeled demand for dry, normal, and monsoon scenarios. Those percentages and all assigned capacities/demands are experiment assumptions. Conveyance losses are not applied. The real topology is based on the official NWIC/CWC lines; directions, root, taps, and numeric flow values are modeled.

Wastage is defined as `100 * max(0, supply released - useful delivered) / supply released`, where useful delivered is capped at each farm's demand. Source supply not delivered counts as wastage, as requested by the project definition. Head/tail order uses outlet index for generated graphs and shortest-path hop distance from the modeled root for real topology. The real root is arbitrary, not a surveyed intake location.

## Algorithms and complexity

1. **Edmonds–Karp:** BFS augmenting paths and reverse residual edges. `O(V E²)` time, `O(V+E)` space.
2. **Max-flow only:** one Edmonds–Karp run; throughput baseline.
3. **Fixed rotation:** serve farms in a fixed order, consuming residual canal capacity after each farm. `O(F V E²)` time.
4. **Progressive max-min:** binary search a common level and use max-flow to test whether every farm sink edge can be saturated at its target; freeze demand-satisfied farms and test each remaining farm individually for a small feasible increase. At most `F` rounds and `I` binary-search iterations per round cost `O(F I V E²)`; the individual raise checks cost `O(F² V E²)` in the worst case. Total `O((F I + F²) V E²)`, polynomial. This implementation uses floating-point tolerance, so results are approximate to the configured iteration precision.

Core algorithms are implemented without NetworkX. It is only used by an optional randomized test cross-check.

## Run

Python 3.10+ is required. From the workspace root, install `canal_fairness/requirements-dev.txt` for plots and tests; the core flow algorithms use only the standard library.

```powershell
python -m pip install -r canal_fairness/requirements-dev.txt
python canal_fairness/main.py --method all --season dry
python canal_fairness/webapp.py
python canal_fairness/main.py --run-all
python canal_fairness/main.py --synthetic --farms 25 --seed 7 --method fair
python -m pytest canal_fairness/tests
```

The browser UI is served locally at <http://127.0.0.1:8765> after starting `webapp.py`. It defaults to the official canal geometry and exposes the same modeled-value disclosure as the CLI. The first official run loads the large GeoJSON; later runs reuse the in-memory topology cache.

`--run-all` writes seasonal metrics, means and standard deviations, scalability data, sensitivity data, and PNG plots under `canal_fairness/results/`. Runtime values are machine-dependent. The seasonal runs use the government canal geometry plus the declared modeled values; scalability graphs are generated controls. In the fixed-topology seasonal experiment, the seed shuffles only rotation priority; max-flow and fair allocations are deterministic, so their outcome standard deviations are zero apart from floating-point noise. This is repeatability over rotation orders, not 30 independent field observations.

## References

- Perotti et al., “Fair sharing of resources in a supply network with constraints,” arXiv:1108.0025.
- Marasevic, Stein, and Zussman, “Max-min Fair Rate Allocation and Routing in Energy Harvesting Networks,” arXiv:1406.3671.
- “Max-min Fairness in 802.11 Mesh Networks,” arXiv:1002.1581.
- “Design of an Irrigation Network System in Terms of Canal Capacity Using Graph Theory,” *Journal of Irrigation and Drainage Engineering*, 143(6), 2017.
- Goldberg and Tarjan, “A new approach to the maximum-flow problem,” *Journal of the ACM*, 1988.
- Central Water Commission / National Water Informatics Centre, “Canal Network,” National Water Data Portal, <https://nwdp.nwic.gov.in/dataset/canal>.

## Limitations

The data contains canal geometry, not a complete directed operational network. The loader chooses a bounded connected subset and an arbitrary root-based spanning-tree direction, assigns model capacities and tap demands, and omits side loops in the final oriented tree. Thus this evaluates algorithms on a government-sourced mapped structure with transparent hypothetical operating values; it is not a reconstruction of actual canal operations. Rotation order and head/tail distance also need an operational intake location and farm coordinates to have field meaning. Current floating-point progressive filling provides a numerical approximation, not symbolic exactness.

## Measured run

The included `results/` files are from a 30-seed run using the included NWIC/CWC geometry, 50 modeled outlet taps, and the assumptions above. Times were measured with Python 3.10 on the authoring machine. In the dry scenario, supply and delivered water were both 250 ML/day.

| Method | Jain fairness (mean) | Minimum satisfaction (mean) | Head minus tail satisfaction (mean) | Runtime ms (mean +/- SD) |
|---|---:|---:|---:|---:|
| Max-flow only | 0.500 | 0.000 | 1.000 | 2.04 +/- 1.03 |
| Fixed rotation | 0.500 | 0.000 | 0.240 +/- 0.208 | 46.52 +/- 6.43 |
| Progressive max-min | 0.865 | 0.357 | 0.194 +/- 0.025 | 1548.46 +/- 186.42 |

Normal and monsoon scenarios kept the same modeled network bottleneck at 250 ML/day while releasing 450 and 650 ML/day. Measured wastage was 44.44% in normal and 61.54% in monsoon for every method. This reflects the release definition and modeled bottleneck, not observed canal wastage. The remaining metrics and controlled scalability results are in the CSV files under `results/`.

`results/seasonal_metrics.csv` contains every run, while `results/seasonal_summary.csv` contains means, sample standard deviations, and counts. Scalability runtimes are single measurements and should be rerun for hardware-specific comparisons.
