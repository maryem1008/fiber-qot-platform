import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fiber_qot_platform.simulation.phase2 import (  # noqa: E402
    load_mode_config,
    load_simulation_config,
    run_many,
)
from fiber_qot_platform.simulation.sampling import (  # noqa: E402
    sample_scenarios_with_stats,
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    modes = load_mode_config()
    simulation_config = load_simulation_config()
    simulation_config["transceiver"]["mode_parameters"] = modes
    failures = []

    selected = selected_topologies()
    if not selected:
        raise RuntimeError("No accepted Phase 1 topologies found")
    topology_data = []
    for _, unified_path in selected:
        topology = json.loads(unified_path.read_text(encoding="utf-8"))
        topology["unified_path"] = str(unified_path)
        topology_data.append(topology)
    seed = args.seed if args.seed is not None else int(simulation_config["random_seed"])
    scenarios, rejected = sample_scenarios_with_stats(
        topology_data,
        args.runs,
        seed,
        simulation_config,
    )
    tasks = [scenario.to_run_task() for scenario in scenarios]
    outcomes = run_many(tasks, workers=args.workers)
    rows = []
    span_rows = []
    for scenario, outcome in zip(scenarios, outcomes, strict=True):
        if outcome["failure"] is not None:
            failures.append(
                {
                    "scenario_id": scenario.scenario_id,
                    "topology_id": scenario.topology_id,
                    "source": scenario.source,
                    "destination": scenario.destination,
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
                "attempted_runs": len(tasks),
                "successful_rows": len(rows),
                "failed_runs": len(failures),
                "rejected_scenarios": rejected,
                "duplicate_scenario_ids": len(scenarios)
                - len({scenario.scenario_id for scenario in scenarios}),
                "unique_scenario_ratio": len(
                    {scenario.parameter_signature for scenario in scenarios}
                )
                / len(scenarios)
                if scenarios
                else 1.0,
                "output": str(json_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
