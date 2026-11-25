import json
from collections import Counter
from pathlib import Path

import pytest
import yaml

from fiber_qot_platform.simulation.sampling import (
    sample_scenarios,
    sample_scenarios_with_stats,
)

ROOT = Path(__file__).resolve().parents[1]


def load_topologies() -> list[dict]:
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
    return topologies


def sampling_config() -> dict:
    config = yaml.safe_load((ROOT / "configs" / "simulation.yaml").read_text(encoding="utf-8"))
    config["transceiver"]["mode_parameters"] = {
        "mode 1": {
            "baud_rate": 32e9,
            "OSNR": 12.0,
            "min_spacing": 37.5e9,
            "bit_rate": 100e9,
            "tx_osnr": 30.0,
            "roll_off": 0.15,
        },
        "mode 3": {
            "baud_rate": 44e9,
            "OSNR": 18.0,
            "min_spacing": 62.5e9,
            "bit_rate": 200e9,
            "tx_osnr": 30.0,
            "roll_off": 0.15,
        },
        "mode 2": {
            "baud_rate": 66e9,
            "OSNR": 21.0,
            "min_spacing": 75e9,
            "bit_rate": 300e9,
            "tx_osnr": 30.0,
            "roll_off": 0.15,
        },
        "mode 4": {
            "baud_rate": 66e9,
            "OSNR": 16.0,
            "min_spacing": 75e9,
            "bit_rate": 400e9,
            "tx_osnr": 30.0,
            "roll_off": 0.15,
        },
    }
    return config


def test_sampler_returns_exact_count_and_is_seed_deterministic() -> None:
    topologies = load_topologies()
    config = sampling_config()
    first = sample_scenarios(topologies, 37, seed=7, config=config)
    same = sample_scenarios(topologies, 37, seed=7, config=config)
    other_seed = sample_scenarios(topologies, 37, seed=8, config=config)

    assert first == same
    assert first != other_seed
    assert len(first) == 37
    assert len({scenario.scenario_id for scenario in first}) == 37
    assert set(Counter(item.topology_id for item in first).values()) == {2, 3}


def test_sampler_distribution_and_channel_bandwidth_are_valid() -> None:
    topologies = load_topologies()
    config = sampling_config()
    scenarios, rejected = sample_scenarios_with_stats(
        topologies,
        5000,
        seed=20261124,
        config=config,
    )
    signature_ratio = len({item.parameter_signature for item in scenarios}) / len(scenarios)
    mode_counts = Counter(item.mode_name for item in scenarios)
    launch_power_levels = {item.launch_power_dbm for item in scenarios}
    band_ghz = (config["reference"]["f_max_hz"] - config["reference"]["f_min_hz"]) / 1e9

    assert len(scenarios) == 5000
    assert rejected == 0
    assert signature_ratio >= 0.99
    assert len({item.scenario_id for item in scenarios}) == 5000
    assert len(launch_power_levels) >= 550
    assert all(0.20 <= count / len(scenarios) <= 0.30 for count in mode_counts.values())
    assert set(item.route_rank for item in scenarios) == {1, 2, 3}
    assert all(item.channels * item.spacing_ghz <= band_ghz for item in scenarios)


def test_sampler_rejects_invalid_size() -> None:
    with pytest.raises(ValueError, match="n must not be negative"):
        sample_scenarios([], -1, seed=1, config={})
