import math
from pathlib import Path

import pytest

from fiber_qot_platform.simulation.phase2 import (
    feasibility_margin,
    load_mode_config,
    load_simulation_config,
    mean_db,
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
