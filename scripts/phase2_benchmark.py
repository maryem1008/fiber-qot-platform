import argparse
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    topology = ROOT / "data" / "topologies" / "tunisia.json"
    modes = load_mode_config()
    simulation_config = load_simulation_config()
    design_margin_db = float(simulation_config["sampling"].get("design_margin_db", 2.0))
    mode_name = "mode 1"
    mode = modes[mode_name]
    tasks = [
        {
            "topology_id": "tunisia",
            "unified_path": topology,
            "source": "Bizerte",
            "destination": "Sfax",
            "mode_name": mode_name,
            "mode": mode,
            "channels": 76,
            "spacing_hz": 50e9,
            "power_dbm": 0.0,
            "design_margin_db": design_margin_db,
        }
        for _ in range(args.runs)
    ]
    start = time.perf_counter()
    outcomes = run_many(tasks, workers=args.workers)
    elapsed = time.perf_counter() - start
    successful = sum(outcome["failure"] is None for outcome in outcomes)
    failures = len(outcomes) - successful
    print(
        {
            "requested": args.runs,
            "attempted": len(outcomes),
            "successful": successful,
            "failed": failures,
            "workers": args.workers,
            "elapsed_seconds": round(elapsed, 3),
            "seconds_per_run": round(elapsed / len(outcomes), 3) if outcomes else None,
        }
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
