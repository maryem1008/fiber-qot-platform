import argparse
import json
from pathlib import Path

from fiber_qot_platform.topology.phase1 import (
    build_tunisia,
    make_unified,
    parse_graphml,
    parse_sndlib,
    to_gnpy_network,
)

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_ZOO = [
    "Aarnet",
    "Abilene",
    "AttMpls",
    "Bics",
    "BtEurope",
    "Cernet",
    "Cesnet201006",
    "Colt",
    "CrlNetworkServices",
    "Dfn",
    "Airtel",
    "Arpanet196912",
    "Bellcanada",
    "Biznet",
    "Cogentco",
    "Columbus",
    "Darkstrand",
    "EliBackbone",
    "Forthnet",
    "Garr201201",
    "HiberniaGlobal",
    "Internode",
    "Kdl",
    "Litnet",
    "TataNld",
    "VtlWavenet2011",
    "Bbnplanet",
    "Carnet",
    "Chinanet",
    "Deltacom",
    "Eunetworks",
    "Gambia",
    "Goodnet",
    "Heanet",
    "Kentman",
    "RedIris",
    "Sago",
    "SwitchL3",
    "Palmetto",
    "Pern",
    "Agis",
    "Spiralight",
    "Iris",
    "Cesnet200511",
    "Switch",
    "Geant2009",
    "Ulaknet",
    "Uunet",
]
DEFAULT_SNDLIB = ["germany50.xml", "nobel-germany.xml", "india35.xml"]


def complete_coordinates(nodes: dict[str, dict]) -> int:
    return sum(
        1
        for node in nodes.values()
        if node["latitude"] is not None
        and node["longitude"] is not None
        and -90 <= node["latitude"] <= 90
        and -180 <= node["longitude"] <= 180
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "topologies")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "topologies")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    candidate_paths: list[tuple[str, str, Path]] = []
    for name in DEFAULT_ZOO:
        path = args.raw_dir / f"{name}.graphml"
        if path.exists():
            candidate_paths.append(("zoo", f"zoo_{name.lower()}", path))
    for filename in DEFAULT_SNDLIB:
        path = args.raw_dir / filename
        if path.exists():
            candidate_paths.append(("sndlib", f"sndlib_{filename.removesuffix('.xml')}", path))

    results = []
    for source, topology_id, path in candidate_paths:
        try:
            if source == "zoo":
                nodes, links = parse_graphml(path)
            else:
                nodes, links = parse_sndlib(path)
            topology = make_unified(topology_id, f"{source}:{path.name}", nodes, links)
        except (ValueError, KeyError, TypeError) as exc:
            results.append({"topology_id": topology_id, "status": "rejected", "reason": str(exc)})
            continue

        coordinate_count = complete_coordinates(nodes)
        if source == "zoo" and (coordinate_count != len(nodes) or not 15 <= len(nodes) <= 60):
            results.append(
                {
                    "topology_id": topology_id,
                    "status": "rejected",
                    "reason": (
                        f"coordinate_complete={coordinate_count == len(nodes)}; "
                        f"node_count={len(nodes)}; preferred Zoo range is 15-60"
                    ),
                }
            )
            continue
        if source == "sndlib" and coordinate_count != len(nodes):
            results.append(
                {
                    "topology_id": topology_id,
                    "status": "rejected",
                    "reason": f"incomplete coordinates: {coordinate_count}/{len(nodes)}",
                }
            )
            continue

        unified_path = args.output_dir / f"{topology_id}.json"
        gnpy_path = args.output_dir / f"{topology_id}_gnpy.json"
        unified_path.write_text(json.dumps(topology, indent=2), encoding="utf-8")
        gnpy_path.write_text(json.dumps(to_gnpy_network(topology), indent=2), encoding="utf-8")
        results.append(
            {
                "topology_id": topology_id,
                "status": "converted",
                "source": source,
                "source_file": path.name,
                "nodes": len(topology["nodes"]),
                "links": len(topology["links"]),
                "coordinate_complete": complete_coordinates(nodes) == len(nodes),
            }
        )

    nodes, links = build_tunisia()
    tunisia = make_unified(
        "tunisia",
        "illustrative synthetic: Phase 1 project definition",
        nodes,
        links,
    )
    (args.output_dir / "tunisia.json").write_text(json.dumps(tunisia, indent=2), encoding="utf-8")
    (args.output_dir / "tunisia_gnpy.json").write_text(
        json.dumps(to_gnpy_network(tunisia), indent=2),
        encoding="utf-8",
    )
    results.append(
        {
            "topology_id": "tunisia",
            "status": "converted",
            "source": "illustrative_synthetic",
            "nodes": len(tunisia["nodes"]),
            "links": len(tunisia["links"]),
            "coordinate_complete": True,
        }
    )

    (args.output_dir / "phase1_manifest.json").write_text(
        json.dumps({"topologies": results}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"topologies": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
