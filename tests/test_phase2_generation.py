import json
import math
from pathlib import Path

import pytest

from fiber_qot_platform.simulation.phase2 import (
    feasibility_margin,
    load_mode_config,
    load_simulation_config,
    mean_db,
    run_many,
    run_one,
)

ROOT = Path(__file__).resolve().parents[1]


def test_gnpymodes_are_loaded_from_configuration() -> None:
    modes = load_mode_config()
    assert "mode 1" in modes
    assert modes["mode 1"]["OSNR"] == 12.0


def test_mean_db_handles_scalar_and_array_values() -> None:
    assert mean_db(20.0) == 20.0


@pytest.mark.parametrize(
    ("gsnr_db_01nm", "expected_margin_db", "expected_feasible"),
    [(14.1, 2.1, True), (13.9, 1.9, False)],
)
def test_feasibility_uses_01nm_gsnr_and_design_margin(
    gsnr_db_01nm: float,
    expected_margin_db: float,
    expected_feasible: bool,
) -> None:
    margin_db, feasible = feasibility_margin(gsnr_db_01nm, 12.0, 2.0)
    assert margin_db == pytest.approx(expected_margin_db)
    assert feasible is expected_feasible


def test_real_gnpy_run_uses_matching_gsnr_bandwidth_convention() -> None:
    modes = load_mode_config()
    mode = modes["mode 1"]
    config = load_simulation_config()
    design_margin_db = float(config["sampling"]["design_margin_db"])
    row = run_one(
        "tunisia",
        ROOT / "data" / "topologies" / "tunisia.json",
        "Bizerte",
        "Sfax",
        "mode 1",
        mode,
        76,
        50e9,
        0.0,
        design_margin_db,
    )
    expected_difference_db = 10 * math.log10(mode["baud_rate"] / 12.5e9)

    assert row["gsnr_db_01nm"] - row["gsnr_db"] == pytest.approx(
        expected_difference_db,
        abs=0.1,
    )
    assert row["required_osnr_01nm_db"] == mode["OSNR"]
    assert row["margin_db"] == pytest.approx(row["gsnr_db_01nm"] - mode["OSNR"])
    assert row["feasible"] is (row["margin_db"] >= design_margin_db)
    assert "required_gsnr_db" not in row


def test_cached_networks_match_uncached_for_twenty_scenarios() -> None:
    modes = load_mode_config()
    nodes = [
        node["id"]
        for node in json.loads(
            (ROOT / "data" / "topologies" / "tunisia.json").read_text(encoding="utf-8")
        )["nodes"]
    ]
    scenarios = [
        {
            "topology_id": "tunisia",
            "unified_path": ROOT / "data" / "topologies" / "tunisia.json",
            "source": nodes[index % len(nodes)],
            "destination": nodes[(index * 5 + 1) % len(nodes)],
            "mode_name": "mode 1",
            "mode": modes["mode 1"],
            "channels": 1 + index % 10,
            "spacing_hz": 50e9,
            "power_dbm": -2.0 + index / 10,
            "design_margin_db": 2.0,
            "noise_seed": index,
        }
        for index in range(20)
    ]
    uncached = [run_one(**scenario, use_cache=False) for scenario in scenarios]
    cached = [run_one(**scenario, use_cache=True) for scenario in scenarios]

    for uncached_row, cached_row in zip(uncached, cached, strict=True):
        assert cached_row["gsnr_db"] == pytest.approx(uncached_row["gsnr_db"], abs=1e-9)
        assert cached_row["gsnr_db_01nm"] == pytest.approx(
            uncached_row["gsnr_db_01nm"],
            abs=1e-9,
        )


def test_parallel_results_match_single_worker_results() -> None:
    modes = load_mode_config()
    tasks = [
        {
            "topology_id": "tunisia",
            "unified_path": ROOT / "data" / "topologies" / "tunisia.json",
            "source": "Bizerte",
            "destination": "Sfax",
            "mode_name": "mode 1",
            "mode": modes["mode 1"],
            "channels": 12 + index,
            "spacing_hz": 50e9,
            "power_dbm": -1.0,
            "design_margin_db": 2.0,
        }
        for index in range(2)
    ]
    single_worker = run_many(tasks, workers=1)
    two_workers = run_many(tasks, workers=2)

    for single_outcome, parallel_outcome in zip(single_worker, two_workers, strict=True):
        assert single_outcome["failure"] is None
        assert parallel_outcome["failure"] is None
        single = single_outcome["row"]
        parallel = parallel_outcome["row"]
        assert parallel["gsnr_db"] == pytest.approx(single["gsnr_db"], abs=1e-9)
        assert parallel["gsnr_db_01nm"] == pytest.approx(single["gsnr_db_01nm"], abs=1e-9)
        assert parallel["gsnr_db_noisy"] == pytest.approx(single["gsnr_db_noisy"], abs=1e-9)
