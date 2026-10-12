"""Local browser interface for running canal allocation scenarios."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from allocators import max_min_fair, maxflow_only, fixed_rotation
from experiments import scenario
from graph import load_nwic_geojson, synthetic_network
from metrics import evaluate

PROJECT_DIR = Path(__file__).resolve().parent
DATASET = PROJECT_DIR / "data" / "canal_network.geojson"
INDEX = PROJECT_DIR / "index.html"
METHODS = {"maxflow": maxflow_only, "rotation": fixed_rotation, "fair": max_min_fair}
METHOD_LABELS = {"maxflow": "Max-flow only", "rotation": "Fixed rotation", "fair": "Progressive max-min"}
REAL_BASE = None
REAL_LOCK = threading.Lock()
SEASONS = {"dry": 0.5, "normal": 0.9, "monsoon": 1.3}


def get_real_network(farms: int):
    """Return a trimmed view of the cached official topology. O(E) per request after loading."""
    global REAL_BASE
    if REAL_BASE is None:
        with REAL_LOCK:
            if REAL_BASE is None:
                if not DATASET.is_file():
                    raise FileNotFoundError(f"Official dataset not found: {DATASET}")
                REAL_BASE = load_nwic_geojson(DATASET, farms=80, max_nodes=100)
    base = REAL_BASE
    keep = base["farms"][:farms]
    keep_set = set(keep)
    all_farms = set(base["farms"])
    caps = {edge: value for edge, value in base["capacities"].items()
            if (edge[0] not in all_farms or edge[0] in keep_set)
            and (edge[1] not in all_farms or edge[1] in keep_set)}
    demands = {farm: base["demands"][farm] for farm in keep}
    return {**base, "capacities": caps, "demands": demands, "farms": keep,
            "distance": {farm: base["distance"][farm] for farm in keep}}


def run_scenario(payload: dict):
    """Run requested algorithm(s), returning JSON-friendly results."""
    mode = payload.get("dataset", "official")
    season = payload.get("season", "dry")
    method = payload.get("method", "all")
    farms = int(payload.get("farms", 50))
    seed = int(payload.get("seed", 0))
    if mode not in {"official", "synthetic"}: raise ValueError("Unknown dataset option")
    if season not in SEASONS: raise ValueError("Unknown season")
    if method not in {*METHODS, "all"}: raise ValueError("Unknown allocation method")
    max_farms = 80 if mode == "official" else 200
    if not 1 <= farms <= max_farms: raise ValueError(f"Farm count must be between 1 and {max_farms} for this dataset")
    net = get_real_network(farms) if mode == "official" else synthetic_network(farms, seed)
    fraction = SEASONS[season]
    net, supply = scenario(net, fraction)
    method_names = list(METHODS) if method == "all" else [method]
    results = []
    for name in method_names:
        import time
        start = time.perf_counter()
        allocation = METHODS[name](net)
        elapsed = (time.perf_counter() - start) * 1000
        metrics = evaluate(net, allocation, supply, elapsed)
        by_distance = sorted(net["farms"], key=lambda f: (net.get("distance", {}).get(f, 0), f))
        results.append({
            "method": name,
            "label": METHOD_LABELS[name],
            "metrics": {key: value for key, value in metrics.items() if key != "satisfaction"},
            "farms": [{"farm": farm, "demand": net["demands"][farm],
                       "received": allocation.get(farm, 0.0),
                       "satisfaction": metrics["satisfaction"][farm],
                       "distance_hops": net.get("distance", {}).get(farm, 0)}
                      for farm in by_distance],
        })
    canal_segments = (net.get("topology_nodes", 1) - 1 if mode == "official"
                      else len(net["capacities"]) - len(net["farms"]))
    return {
        "season": season,
        "supply_fraction": fraction,
        "supply": supply,
        "demand_total": sum(net["demands"].values()),
        "dataset": mode,
        "dataset_label": "NWIC / CWC Government of India canal geometry" if mode == "official" else "Generated synthetic network",
        "source_note": "Canal geometry is government data. Capacities (100 ML/day per modeled segment) and demands (10 ML/day per modeled tap) are assumptions, not official measurements." if mode == "official" else "Generated test data; not a government dataset.",
        "farms": len(net["farms"]),
        "canal_segments": canal_segments,
        "methods": results,
    }


class Handler(BaseHTTPRequestHandler):
    """Serve the static UI and the local allocation API."""
    def _send(self, status: int, body: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlparse(self.path).path in {"/", "/index.html"}:
            self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
        elif urlparse(self.path).path == "/api/health":
            self._send(200, b'{"status":"ok"}', "application/json")
        else:
            self._send(404, b"Not found", "text/plain; charset=utf-8")

    def do_POST(self):
        if urlparse(self.path).path != "/api/run":
            self._send(404, b'{"error":"Not found"}', "application/json")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 10000: raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(length))
            result = run_scenario(payload)
            self._send(200, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
        except FileNotFoundError as exc:
            self._send(503, json.dumps({"error": str(exc)}).encode(), "application/json; charset=utf-8")
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send(400, json.dumps({"error": str(exc)}).encode(), "application/json; charset=utf-8")
        except Exception as exc:
            self._send(500, json.dumps({"error": f"Run failed: {exc}"}).encode(), "application/json; charset=utf-8")

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


def main():
    host, port = "127.0.0.1", 8765
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Canal Fairness Lab is running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping Canal Fairness Lab.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
