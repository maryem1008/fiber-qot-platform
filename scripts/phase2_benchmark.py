import argparse
import json
import sys
import time
from pathlib import Path

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--uncached", action="store_true")
    args = parser.parse_args()

    modes = load_mode_config()
    simulation_config = load_simulation_config()
    simulation_config["transceiver"]["mode_parameters"] = modes
    manifest = json.loads(
        (ROOT / "data" / "topologies" / "phase1_manifest.json").read_text(encoding="utf-8")
    )
    topology_ids = [
        item["topology_id"]
        for item in manifest["topologies"]
        if item["status"] == "converted" and (item["topology_id"].startswith(("zoo_", "sndlib_")))
    ]
    topology_ids.append("tunisia")
    topologies = []
    for topology_id in sorted(topology_ids):
        path = ROOT / "data" / "topologies" / f"{topology_id}.json"
        topology = json.loads(path.read_text(encoding="utf-8"))
        topology["unified_path"] = str(path)
        topologies.append(topology)
    seed = args.seed if args.seed is not None else int(simulation_config["random_seed"])
    scenarios, rejected = sample_scenarios_with_stats(
        topologies,
        args.runs,
        seed,
        simulation_config,
    )
    tasks = [scenario.to_run_task() for scenario in scenarios]
    for task in tasks:
        task["use_cache"] = not args.uncached
    start = time.perf_counter()
    outcomes = run_many(tasks, workers=args.workers)
    elapsed = time.perf_counter() - start
    successful = sum(outcome["failure"] is None for outcome in outcomes)
    failures = len(outcomes) - successful
    unique_signatures = len({scenario.parameter_signature for scenario in scenarios})
    print(
        json.dumps(
            {
                "requested": args.runs,
                "attempted": len(outcomes),
                "successful": successful,
                "failed": failures,
                "rejected": rejected,
                "unique_scenario_ratio": unique_signatures / len(scenarios) if scenarios else 1.0,
                "topologies": len({scenario.topology_id for scenario in scenarios}),
                "workers": args.workers,
                "cache": "disabled" if args.uncached else "enabled",
                "elapsed_seconds": round(elapsed, 3),
                "seconds_per_run": round(elapsed / len(outcomes), 3) if outcomes else None,
            },
            indent=2,
        )
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
