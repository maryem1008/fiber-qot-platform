import json
import math
from itertools import islice
from pathlib import Path

import networkx as nx
import pytest

from fiber_qot_platform.simulation.phase2 import (
    apply_scenario_offsets,
    derive_nli_snr_db,
    feasibility_margin,
    graph_for,
    load_equipment,
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
    ("gsnr_db", "osnr_db", "expected"),
    [(20.0, 25.0, True), (20.0, 20.0, False), (20.0, 19.0, False)],
)
def test_derived_nli_snr_preserves_invalid_inverse_difference(
    gsnr_db: float,
    osnr_db: float,
    expected: bool,
) -> None:
    result = derive_nli_snr_db(gsnr_db, osnr_db)
    assert (result is not None) is expected
    if result is not None:
        gsnr_inverse = 10 ** (-gsnr_db / 10)
        osnr_inverse = 10 ** (-osnr_db / 10)
        assert 10 ** (-result / 10) == pytest.approx(gsnr_inverse - osnr_inverse)


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
    topology = json.loads(
        (ROOT / "data" / "topologies" / "tunisia.json").read_text(encoding="utf-8")
    )
    graph = graph_for(topology)
    route_options = list(
        islice(nx.shortest_simple_paths(graph, "Bizerte", "Sfax", weight="weight"), 3)
    )
    route = route_options[-1]
    assert len(route_options) == 3
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
        route_nodes=tuple(route),
        route_rank=3,
        amplifier_nf_offset_db=0.2,
        span_loss_offset_db=0.4,
        extra_connector_loss_db=0.2,
    )
    reference_bandwidth_hz = config["reference"]["osnr_reference_bandwidth_hz"]
    expected_difference_db = 10 * math.log10(mode["baud_rate"] / reference_bandwidth_hz)

    assert row["simulated_route"] == route
    assert row["route"] == route
    assert row["route_rank"] == 3
    assert row["gsnr_db_01nm"] - row["gsnr_db"] == pytest.approx(
        expected_difference_db,
        abs=0.1,
    )
    assert row["required_osnr_01nm_db"] == mode["OSNR"]
    assert row["margin_db"] == pytest.approx(row["gsnr_db_01nm"] - mode["OSNR"])
    assert row["feasible"] is (row["margin_db"] >= design_margin_db)
    for bandwidth_suffix, gsnr_key, osnr_key in (
        ("", "gsnr_db", "osnr_db"),
        ("_01nm", "gsnr_db_01nm", "osnr_01nm_db"),
    ):
        nli_key = f"snr_nli{bandwidth_suffix}_db"
        expected_nli = derive_nli_snr_db(row[gsnr_key], row[osnr_key])
        assert (
            row[nli_key] == pytest.approx(expected_nli)
            if expected_nli is not None
            else row[nli_key] is None
        )
        assert row[f"{nli_key}_available"] is (expected_nli is not None)
        assert row[f"{nli_key}_invalid"] is (
            expected_nli is None and row[gsnr_key] is not None and row[osnr_key] is not None
        )
    assert "required_gsnr_db" not in row


def test_gnpy_scenario_offsets_change_supported_parameters() -> None:
    from gnpy.tools.json_io import load_network

    equipment = load_equipment(use_cache=False)
    network = load_network(ROOT / "data" / "topologies" / "tunisia_gnpy.json", equipment)
    fiber = next(element for element in network if type(element).__name__ == "Fiber")
    base_con_in = fiber.params.con_in
    base_con_out = fiber.params.con_out

    apply_scenario_offsets(network, 0.4, 0.2)

    assert fiber.params.con_in == pytest.approx(base_con_in + 0.3)
    assert fiber.params.con_out == pytest.approx(base_con_out + 0.3)


def test_gnpy_amplifier_nf_offset_applies_after_network_design() -> None:
    modes = load_mode_config()
    common = {
        "topology_id": "tunisia",
        "unified_path": ROOT / "data" / "topologies" / "tunisia.json",
        "source": "Bizerte",
        "destination": "Sfax",
        "mode_name": "mode 1",
        "mode": modes["mode 1"],
        "channels": 1,
        "spacing_hz": 50e9,
        "power_dbm": 0.0,
    }
    baseline = run_one(**common)
    shifted = run_one(**common, amplifier_nf_offset_db=0.2)

    assert shifted["amp_nf_mean_db"] == pytest.approx(baseline["amp_nf_mean_db"] + 0.2)


def test_cached_networks_match_uncached_for_twenty_scenarios() -> None:
    modes = load_mode_config()
    topology_path = ROOT / "data" / "topologies" / "tunisia.json"
    topology = json.loads(topology_path.read_text(encoding="utf-8"))
    nodes = [node["id"] for node in topology["nodes"]]
    graph = graph_for(topology)
    scenarios = [
        {
            "topology_id": "tunisia",
            "unified_path": topology_path,
            "source": nodes[index % len(nodes)],
            "destination": nodes[(index * 5 + 1) % len(nodes)],
            "mode_name": "mode 1",
            "mode": modes["mode 1"],
            "channels": 1 + index % 10,
            "spacing_hz": 50e9,
            "power_dbm": -2.0 + index / 10,
            "design_margin_db": 2.0,
            "noise_seed": index,
            "route_nodes": tuple(
                nx.shortest_path(
                    graph,
                    nodes[index % len(nodes)],
                    nodes[(index * 5 + 1) % len(nodes)],
                    weight="weight",
                )
            ),
        }
        for index in range(20)
    ]
    uncached = [run_one(**scenario, use_cache=False) for scenario in scenarios]
    cached = [run_one(**scenario, use_cache=True) for scenario in scenarios]

    for scenario, uncached_row, cached_row in zip(scenarios, uncached, cached, strict=True):
        profiles = uncached_row["_span_profiles"]
        span_lengths = [profile["length_km"] for profile in profiles]
        assert uncached_row["route"] == list(scenario["route_nodes"])
        assert uncached_row["simulated_route"] == list(scenario["route_nodes"])
        assert uncached_row["n_roadms"] == len(scenario["route_nodes"])
        assert uncached_row["hops"] == len(scenario["route_nodes"]) - 1
        assert uncached_row["total_length_km"] == pytest.approx(sum(span_lengths), abs=1e-6)
        assert uncached_row["n_spans"] == len(span_lengths)
        assert uncached_row["n_amps"] >= uncached_row["n_spans"]
        assert profiles[-1]["cum_gsnr_db"] == pytest.approx(uncached_row["gsnr_db"], abs=1e-6)
        assert profiles[-1]["cum_gsnr_db_01nm"] == pytest.approx(
            uncached_row["gsnr_db_01nm"],
            abs=1e-6,
        )
        assert all(
            later["cum_gsnr_db_01nm"] <= earlier["cum_gsnr_db_01nm"] + 1e-6
            for earlier, later in zip(profiles, profiles[1:])
        )
        assert any(abs(profile["gsnr_drop_db"]) > 1e-9 for profile in profiles)
        assert all(
            profile["power_out_dbm"] > profile["power_after_fiber_dbm"] for profile in profiles
        )
        assert all(
            profile["geometry_source"] == "interpolated_great_circle"
            and len(profile["geometry"]) == 2
            for profile in profiles
        )
        for profile in profiles:
            for suffix in ("", "_01nm"):
                nli_key = f"cum_snr_nli_db{suffix}"
                gsnr_key = f"cum_gsnr_db{suffix}"
                osnr_key = f"cum_osnr_ase_db{suffix}"
                expected_nli = derive_nli_snr_db(profile[gsnr_key], profile[osnr_key])
                assert (
                    profile[nli_key] == pytest.approx(expected_nli)
                    if expected_nli is not None
                    else profile[nli_key] is None
                )
                assert profile[f"{nli_key}_available"] is (expected_nli is not None)
                assert profile[f"{nli_key}_invalid"] is (
                    expected_nli is None
                    and profile[gsnr_key] is not None
                    and profile[osnr_key] is not None
                )
        for suffix in ("", "_01nm"):
            path_nli_key = f"snr_nli{suffix}_db"
            span_nli_key = f"cum_snr_nli_db{suffix}"
            if uncached_row[path_nli_key] is None:
                assert profiles[-1][span_nli_key] is None
            else:
                assert profiles[-1][span_nli_key] == pytest.approx(uncached_row[path_nli_key])
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
