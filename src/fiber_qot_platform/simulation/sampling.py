import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from itertools import combinations, islice
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    topology_id: str
    unified_path: str | None
    source: str
    destination: str
    route: tuple[str, ...]
    route_rank: int
    mode_name: str
    baud_rate_hz: float
    required_osnr_01nm_db: float
    min_spacing_hz: float
    bit_rate_bps: float
    tx_osnr_db: float
    roll_off: float
    channels: int
    spacing_ghz: float
    launch_power_dbm: float
    amplifier_nf_offset_db: float
    span_loss_offset_db: float
    extra_connector_loss_db: float
    noise_std_db: float
    seed_index: int
    scenario_seed: int
    design_margin_db: float

    @property
    def parameter_signature(self) -> str:
        values = asdict(self)
        for field in ("scenario_id", "seed_index", "scenario_seed", "unified_path"):
            values.pop(field)
        return json.dumps(values, sort_keys=True, separators=(",", ":"))

    def to_run_task(self) -> dict[str, Any]:
        if self.unified_path is None:
            raise ValueError("scenario has no unified topology path")
        return {
            "topology_id": self.topology_id,
            "unified_path": Path(self.unified_path),
            "source": self.source,
            "destination": self.destination,
            "mode_name": self.mode_name,
            "mode": {
                "baud_rate": self.baud_rate_hz,
                "OSNR": self.required_osnr_01nm_db,
                "min_spacing": self.min_spacing_hz,
                "bit_rate": self.bit_rate_bps,
                "tx_osnr": self.tx_osnr_db,
                "roll_off": self.roll_off,
            },
            "channels": self.channels,
            "spacing_hz": self.spacing_ghz * 1e9,
            "power_dbm": self.launch_power_dbm,
            "design_margin_db": self.design_margin_db,
            "use_cache": True,
            "noise_seed": self.scenario_seed,
            "noise_std_db": self.noise_std_db,
            "route_nodes": self.route,
            "scenario_id": self.scenario_id,
            "seed_index": self.seed_index,
            "scenario_seed": self.scenario_seed,
            "route_rank": self.route_rank,
            "amplifier_nf_offset_db": self.amplifier_nf_offset_db,
            "span_loss_offset_db": self.span_loss_offset_db,
            "extra_connector_loss_db": self.extra_connector_loss_db,
        }


def _graph_for(topology: Mapping[str, Any]) -> nx.Graph:
    graph = nx.Graph()
    for node in sorted(topology["nodes"], key=lambda item: item["id"]):
        graph.add_node(node["id"])
    links = sorted(
        topology["links"],
        key=lambda item: (min(item["source"], item["target"]), max(item["source"], item["target"])),
    )
    for link in links:
        graph.add_edge(link["source"], link["target"], length_km=float(link["length_km"]))
    return graph


def _connected_pairs(graph: nx.Graph) -> list[tuple[str, str]]:
    return [
        pair
        for component in sorted(
            (sorted(nodes) for nodes in nx.connected_components(graph)),
            key=lambda nodes: nodes[0],
        )
        for pair in combinations(component, 2)
    ]


def _scenario_id(values: Mapping[str, Any]) -> str:
    serialized = json.dumps(values, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def sample_scenarios_with_stats(
    topologies: Sequence[Mapping[str, Any]],
    n: int,
    seed: int,
    config: Mapping[str, Any],
) -> tuple[list[Scenario], int]:
    if n < 0:
        raise ValueError("n must not be negative")
    if seed < 0:
        raise ValueError("seed must not be negative")
    if n == 0:
        return [], 0
    if not topologies:
        raise ValueError("at least one topology is required")

    sampling = config["sampling"]
    reference = config["reference"]
    transceiver = config["transceiver"]
    mode_parameters = transceiver["mode_parameters"]
    mode_names = list(transceiver["modes"])
    if any(name not in mode_parameters for name in mode_names):
        raise ValueError("resolved mode parameters are missing configured transceiver modes")

    f_min_hz = float(reference["f_min_hz"])
    f_max_hz = float(reference["f_max_hz"])
    if f_max_hz <= f_min_hz:
        raise ValueError("reference f_max_hz must be greater than f_min_hz")
    band_ghz = (f_max_hz - f_min_hz) / 1e9
    channel_range = sampling["channel_count"]
    if int(channel_range[0]) != 1:
        raise ValueError("sampling.channel_count must start at 1")
    channel_max = int(channel_range[1])
    power_min, power_max = map(float, sampling["launch_power_dbm"])
    nf_offset_min, nf_offset_max = map(float, sampling["amplifier_nf_offset_db"])
    span_offset_min, span_offset_max = map(float, sampling["span_loss_offset_db"])
    connector_min, connector_max = map(float, sampling["extra_connector_loss_db"])
    noise_min, noise_max = map(float, sampling["noisy_gsnr_std_db"])
    spacing_options = sorted(float(value) for value in sampling["channel_spacing_ghz"])
    design_margin_db = float(sampling.get("design_margin_db", 2.0))
    max_paths = int(config["max_shortest_paths"])
    if max_paths < 1:
        raise ValueError("max_shortest_paths must be at least 1")

    topology_data = []
    for topology in topologies:
        graph = _graph_for(topology)
        pairs = _connected_pairs(graph)
        if not pairs:
            raise ValueError(f"{topology['topology_id']}: no connected node pairs")
        topology_data.append(
            (
                topology,
                graph,
                pairs,
                {name: mode_parameters[name] for name in mode_names},
            )
        )

    rng = np.random.default_rng(seed)
    base_count, remainder = divmod(n, len(topology_data))
    scenarios = []
    rejected = 0
    seed_index = 0

    for topology_index, (topology, graph, pairs, modes) in enumerate(topology_data):
        target_count = base_count + (1 if topology_index < remainder else 0)
        paths_by_pair: dict[tuple[str, str], list[tuple[str, ...]]] = {}
        accepted = 0
        attempts = 0
        max_attempts = max(100, target_count * 100)

        while accepted < target_count:
            attempts += 1
            if attempts > max_attempts:
                raise RuntimeError(
                    f"{topology['topology_id']}: unable to sample {target_count} valid scenarios"
                )
            pair_index = int(rng.integers(0, len(pairs)))
            source, destination = pairs[pair_index]
            reverse_route = bool(rng.integers(0, 2))
            key = (source, destination)
            if key not in paths_by_pair:
                paths_by_pair[key] = [
                    tuple(path)
                    for path in islice(
                        nx.shortest_simple_paths(graph, source, destination, weight="length_km"),
                        max_paths,
                    )
                ]
            routes = paths_by_pair[key]
            if not routes:
                rejected += 1
                continue
            route_rank_index = int(rng.integers(0, len(routes)))
            route = routes[route_rank_index]
            if reverse_route:
                source, destination = destination, source
                route = tuple(reversed(route))

            mode_name = mode_names[int(rng.integers(0, len(mode_names)))]
            mode = modes[mode_name]
            valid_spacings = [
                spacing
                for spacing in spacing_options
                if spacing * 1e9 >= float(mode["min_spacing"])
            ]
            if not valid_spacings:
                raise ValueError(f"{mode_name}: no configured spacing meets its minimum spacing")
            spacing_ghz = valid_spacings[int(rng.integers(0, len(valid_spacings)))]
            channels_max = min(channel_max, int(band_ghz // spacing_ghz))
            if channels_max < 1:
                rejected += 1
                continue
            channels = int(rng.integers(1, channels_max + 1))
            launch_power_dbm = round(float(rng.uniform(power_min, power_max)), 2)
            nf_offset_db = round(float(rng.uniform(nf_offset_min, nf_offset_max)), 3)
            span_offset_db = round(float(rng.uniform(span_offset_min, span_offset_max)), 3)
            connector_loss_db = round(float(rng.uniform(connector_min, connector_max)), 3)
            noise_std_db = round(float(rng.uniform(noise_min, noise_max)), 4)
            scenario_seed = int(np.random.SeedSequence([seed, seed_index]).generate_state(1)[0])
            unified_path = topology.get("unified_path")
            values = {
                "topology_id": topology["topology_id"],
                "source": source,
                "destination": destination,
                "route": list(route),
                "route_rank": route_rank_index + 1,
                "mode_name": mode_name,
                "baud_rate_hz": float(mode["baud_rate"]),
                "required_osnr_01nm_db": float(mode["OSNR"]),
                "min_spacing_hz": float(mode["min_spacing"]),
                "bit_rate_bps": float(mode["bit_rate"]),
                "tx_osnr_db": float(mode["tx_osnr"]),
                "roll_off": float(mode["roll_off"]),
                "channels": channels,
                "spacing_ghz": spacing_ghz,
                "launch_power_dbm": launch_power_dbm,
                "amplifier_nf_offset_db": nf_offset_db,
                "span_loss_offset_db": span_offset_db,
                "extra_connector_loss_db": connector_loss_db,
                "noise_std_db": noise_std_db,
                "seed_index": seed_index,
                "scenario_seed": scenario_seed,
                "design_margin_db": design_margin_db,
            }
            scenarios.append(
                Scenario(
                    scenario_id=_scenario_id(values),
                    topology_id=topology["topology_id"],
                    unified_path=str(unified_path) if unified_path is not None else None,
                    source=source,
                    destination=destination,
                    route=tuple(route),
                    route_rank=route_rank_index + 1,
                    mode_name=mode_name,
                    baud_rate_hz=float(mode["baud_rate"]),
                    required_osnr_01nm_db=float(mode["OSNR"]),
                    min_spacing_hz=float(mode["min_spacing"]),
                    bit_rate_bps=float(mode["bit_rate"]),
                    tx_osnr_db=float(mode["tx_osnr"]),
                    roll_off=float(mode["roll_off"]),
                    channels=channels,
                    spacing_ghz=spacing_ghz,
                    launch_power_dbm=launch_power_dbm,
                    amplifier_nf_offset_db=nf_offset_db,
                    span_loss_offset_db=span_offset_db,
                    extra_connector_loss_db=connector_loss_db,
                    noise_std_db=noise_std_db,
                    seed_index=seed_index,
                    scenario_seed=scenario_seed,
                    design_margin_db=design_margin_db,
                )
            )
            accepted += 1
            seed_index += 1

    return scenarios, rejected


def sample_scenarios(
    topologies: Sequence[Mapping[str, Any]],
    n: int,
    seed: int,
    config: Mapping[str, Any],
) -> list[Scenario]:
    scenarios, _ = sample_scenarios_with_stats(topologies, n, seed, config)
    return scenarios
