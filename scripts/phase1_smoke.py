import json
from pathlib import Path

import gnpy
from gnpy.tools.json_io import load_equipments_and_configs, load_network

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = Path(gnpy.__file__).resolve().parent / "example-data"
EQUIPMENT = PACKAGE / "eqpt_config.json"


def main() -> int:
    equipment = load_equipments_and_configs(EQUIPMENT, [], [])
    results = []
    for path in sorted((ROOT / "data" / "topologies").glob("*_gnpy.json")):
        try:
            network = load_network(path, equipment)
            node_count = len(network.nodes)
            edge_count = len(network.edges)
            results.append(
                {
                    "topology_id": path.stem.removesuffix("_gnpy"),
                    "status": "gnpy_load_ok",
                    "nodes": node_count,
                    "edges": edge_count,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "topology_id": path.stem.removesuffix("_gnpy"),
                    "status": "gnpy_load_failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    output = ROOT / "data" / "topologies" / "phase1_smoke_results.json"
    output.write_text(json.dumps({"runs": results}, indent=2), encoding="utf-8")
    print(json.dumps({"runs": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
