import argparse
import json
import random
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fiber_qot_platform.simulation.phase2 import (  # noqa: E402
    load_mode_config,
    load_simulation_config,
    run_many,
)


def selected_topologies() -> list[tuple[str, Path]]:
    manifest = json.loads(
        (ROOT / "data" / "topologies" / "phase1_manifest.json").read_text(encoding="utf-8")
    )
    accepted = {}
    for item in manifest["topologies"]:
        if item["status"] != "converted":
            continue
        topology_id = item["topology_id"]
        if topology_id.startswith("zoo_") or topology_id.startswith("sndlib_"):
            accepted[topology_id] = ROOT / "data" / "topologies" / f"{topology_id}.json"
    accepted["tunisia"] = ROOT / "data" / "topologies" / "tunisia.json"
    return sorted(accepted.items())


def candidate_pairs(topology: dict, limit: int = 40) -> list[tuple[str, str]]:
    graph = nx.Graph()
    for node in topology["nodes"]:
        graph.add_node(node["id"])
    graph.add_edges_from((link["source"], link["target"]) for link in topology["links"])
    pairs = []
    nodes = list(graph.nodes)
    for source in nodes:
        for destination in nodes:
            if source >= destination:
                continue
            if nx.has_path(graph, source, destination):
                pairs.append((source, destination))
    random.shuffle(pairs)
    return pairs[:limit]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261123)
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    modes = load_mode_config()
    simulation_config = load_simulation_config()
    design_margin_db = float(simulation_config["sampling"].get("design_margin_db", 2.0))
    mode_names = list(modes)
    tasks = []
    failures = []

    topologies = selected_topologies()
    if not topologies:
        raise RuntimeError("No accepted Phase 1 topologies found")
    per_topology = max(1, args.runs // len(topologies))
    for topology_id, unified_path in topologies:
        topology = json.loads(unified_path.read_text(encoding="utf-8"))
        pairs = candidate_pairs(topology)
        if not pairs:
            failures.append({"topology_id": topology_id, "reason": "no candidate pairs"})
            continue

        for index in range(per_topology):
            source, destination = pairs[index % len(pairs)]
            mode_name = mode_names[index % len(mode_names)]
            channels = 1 + (index * 19) % 80
            spacing_options = [50e9, 75e9] if mode_name in ("mode 1",) else [75e9, 100e9]
            spacing = spacing_options[index % len(spacing_options)]
            power = -3.0 + (index * 0.75) % 6.0
            tasks.append(
                {
                    "topology_id": topology_id,
                    "unified_path": unified_path,
                    "source": source,
                    "destination": destination,
                    "mode_name": mode_name,
                    "mode": modes[mode_name],
                    "channels": channels,
                    "spacing_hz": spacing,
                    "power_dbm": power,
                    "design_margin_db": design_margin_db,
                }
            )

    outcomes = run_many(tasks, workers=args.workers)
    rows = []
    span_rows = []
    for task, outcome in zip(tasks, outcomes, strict=True):
        if outcome["failure"] is not None:
            failures.append(
                {
                    "topology_id": task["topology_id"],
                    "source": task["source"],
                    "destination": task["destination"],
                    "reason": (f"{outcome['failure']['type']}: {outcome['failure']['reason']}"),
                }
            )
            continue
        row = outcome["row"]
        span_rows.extend(row.pop("_span_profiles", []))
        rows.append(row)

    output = ROOT / "data" / "generated"
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "phase2_smoke.json"
    json_path.write_text(
        json.dumps({"rows": rows, "failures": failures}, indent=2),
        encoding="utf-8",
    )
    if rows:
        pd.DataFrame(rows).to_parquet(
            output / "phase2_smoke.parquet",
            index=False,
        )
    if span_rows:
        pd.DataFrame(span_rows).to_parquet(
            output / "phase2_smoke_spans.parquet",
            index=False,
        )
    print(
        json.dumps(
            {
                "requested_runs": args.runs,
                "successful_rows": len(rows),
                "failures": len(failures),
                "output": str(json_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
