import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fiber_qot_platform.simulation.phase2 import load_mode_config, run_one  # noqa: E402


def main() -> int:
    topology = ROOT / "data" / "topologies" / "tunisia.json"
    modes = load_mode_config()
    mode_name = "mode 1"
    mode = modes[mode_name]
    start = time.perf_counter()
    failures = 0
    successful = 0
    for index in range(100):
        try:
            run_one(
                "tunisia",
                topology,
                "Bizerte",
                "Sfax",
                mode_name,
                mode,
                76,
                50e9,
                0.0,
                2.0,
            )
            successful += 1
        except Exception as exc:
            failures += 1
            if failures == 1:
                print(f"First benchmark failure: {type(exc).__name__}: {exc}")
    elapsed = time.perf_counter() - start
    print(
        "Phase 2 benchmark:",
        f"successful={successful}",
        f"failures={failures}",
        f"elapsed_seconds={elapsed:.3f}",
        f"seconds_per_run={elapsed / 100:.3f}",
        f"100000_run_extrapolation_hours={(elapsed / 100 * 100000) / 3600:.2f}",
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
