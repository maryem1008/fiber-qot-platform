import hashlib
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import gnpy
import networkx as nx
import numpy as np
import yaml
from gnpy.core.elements import Edfa, Fiber, Roadm, Transceiver
from gnpy.core.utils import dbm2watt
from gnpy.tools.json_io import (
    load_equipments_and_configs,
    load_gnpy_json,
    load_network,
    network_from_json,
)
from gnpy.tools.worker_utils import designed_network, transmission_simulation
from gnpy.topology.request import PathRequest

ROOT = Path(__file__).resolve().parents[3]
SIMULATION_CONFIG_PATH = ROOT / "configs" / "simulation.yaml"
EQUIPMENT_PATH = Path(gnpy.__file__).resolve().parent / "example-data" / "eqpt_config.json"


def mean_db(value):
    if value is None:
        return None
    array = np.asarray(value)
    return float(np.mean(array))


def derive_nli_snr_db(gsnr_db: float, osnr_db: float) -> float | None:
    if gsnr_db is None or osnr_db is None:
        return None
    gsnr_lin = 10 ** (gsnr_db / 10)
    osnr_lin = 10 ** (osnr_db / 10)
    nli_inverse = max(1e-12, 1 / gsnr_lin - 1 / osnr_lin)
    return 10 * np.log10(1 / nli_inverse)


@lru_cache(maxsize=8)
def _load_simulation_config_cached(config_path: str) -> dict:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError(f"{config_path}: expected a YAML mapping")
    return config


def load_simulation_config(config_path: Path = SIMULATION_CONFIG_PATH) -> dict:
    return deepcopy(_load_simulation_config_cached(str(config_path.resolve())))


def feasibility_margin(
    gsnr_db_01nm: float,
    required_osnr_01nm_db: float,
    design_margin_db: float,
) -> tuple[float, bool]:
    margin_db = gsnr_db_01nm - required_osnr_01nm_db
    return margin_db, margin_db >= design_margin_db


@lru_cache(maxsize=1)
def _load_equipment_cached() -> dict:
    return load_equipments_and_configs(EQUIPMENT_PATH, [], [])


@lru_cache(maxsize=32)
def _load_network_json_cached(path: str) -> dict:
    return load_gnpy_json(Path(path))


def load_equipment(use_cache: bool = True) -> dict:
    if use_cache:
        return _load_equipment_cached()
    return load_equipments_and_configs(EQUIPMENT_PATH, [], [])


def clear_simulation_caches() -> None:
    _load_equipment_cached.cache_clear()
    _load_network_json_cached.cache_clear()


def load_mode_config(use_cache: bool = True) -> dict:
    equipment = load_equipment(use_cache)
    transceivers = equipment.get("Transceiver", {})
    voyager = transceivers.get("Voyager")
    if voyager is None:
        raise RuntimeError("Voyager transceiver not found in GNPy 3.0.1 equipment config")
    modes = {}
    for mode in voyager.mode:
        mode_values = mode if isinstance(mode, dict) else vars(mode)
        modes[str(mode_values["format"])] = {
            "baud_rate": float(mode_values["baud_rate"]),
            "OSNR": float(mode_values["OSNR"]),
            "min_spacing": float(mode_values["min_spacing"]),
            "bit_rate": float(mode_values["bit_rate"]),
            "tx_osnr": float(mode_values["tx_osnr"]),
            "roll_off": float(mode_values.get("roll_off", 0.15)),
        }
    return modes


def _load_run_network(path: Path, equipment: dict, use_cache: bool):
    if not use_cache:
        return load_network(path, equipment)
    network_data = deepcopy(_load_network_json_cached(str(path.resolve())))
    return network_from_json(network_data, equipment)


def graph_for(topology: dict) -> nx.Graph:
    graph = nx.Graph()
    for node in topology["nodes"]:
        graph.add_node(
            node["id"],
            latitude=node["latitude"],
            longitude=node["longitude"],
        )
    for link in topology["links"]:
        graph.add_edge(
            link["source"],
            link["target"],
            weight=link["length_km"],
        )
    return graph


def apply_scenario_offsets(
    network,
    span_loss_offset_db: float,
    extra_connector_loss_db: float,
) -> None:
    connector_delta_db = (span_loss_offset_db + extra_connector_loss_db) / 2
    for element in network:
        if isinstance(element, Fiber):
            element.params.con_in += connector_delta_db
            element.params.con_out += connector_delta_db
            if element.params.con_in < 0 or element.params.con_out < 0:
                raise ValueError("scenario offsets produce negative fiber connector attenuation")


def apply_amplifier_nf_offset(network, amplifier_nf_offset_db: float) -> None:
    if not amplifier_nf_offset_db:
        return
    for element in network:
        if isinstance(element, Edfa):
            nf_model = element.params.nf_model
            if nf_model is None or not all(hasattr(nf_model, name) for name in ("nf1", "nf2")):
                raise ValueError(
                    f"{element.uid}: GNPy NF model does not support a uniform dB offset"
                )
            element.params.nf_model = nf_model._replace(
                nf1=nf_model.nf1 + amplifier_nf_offset_db,
                nf2=nf_model.nf2 + amplifier_nf_offset_db,
            )


def service_request(
    source: str,
    destination: str,
    mode_name: str,
    mode: dict,
    channels: int,
    spacing_hz: float,
    power_dbm: float,
    route_nodes: tuple[str, ...] | None,
    f_min_hz: float,
    f_max_hz: float,
) -> PathRequest:
    route_uids = [f"roadm_{node}" for node in route_nodes[1:-1]] if route_nodes else []
    route_uids.append(destination)
    return PathRequest(
        request_id=f"{source}-{destination}-{mode_name}",
        source=source,
        destination=destination,
        bidir=False,
        trx_type="Voyager",
        trx_mode=mode_name,
        baud_rate=mode["baud_rate"],
        nodes_list=route_uids,
        loose_list=["STRICT"] * len(route_uids),
        format=mode_name,
        spacing=spacing_hz,
        nb_channel=channels,
        power=dbm2watt(power_dbm),
        tx_power=dbm2watt(power_dbm),
        OSNR=mode["OSNR"],
        f_min=f_min_hz,
        f_max=f_max_hz,
        bit_rate=mode["bit_rate"],
        tx_osnr=mode["tx_osnr"],
        min_spacing=mode["min_spacing"],
        path_bandwidth=mode["bit_rate"],
        roll_off=mode["roll_off"],
        equalization_offset_db=0.0,
    )


def run_one(
    topology_id: str,
    unified_path: Path,
    source: str,
    destination: str,
    mode_name: str,
    mode: dict,
    channels: int,
    spacing_hz: float,
    power_dbm: float,
    design_margin_db: float | None = None,
    use_cache: bool = True,
    noise_seed: int | None = None,
    noise_std_db: float | None = None,
    route_nodes: tuple[str, ...] | None = None,
    scenario_id: str | None = None,
    seed_index: int | None = None,
    scenario_seed: int | None = None,
    route_rank: int | None = None,
    amplifier_nf_offset_db: float = 0.0,
    span_loss_offset_db: float = 0.0,
    extra_connector_loss_db: float = 0.0,
) -> dict:
    gnpy_path = unified_path.with_name(f"{unified_path.stem}_gnpy.json")
    equipment = load_equipment(use_cache)
    network = _load_run_network(gnpy_path, equipment, use_cache)
    if design_margin_db is None:
        design_margin_db = float(
            load_simulation_config().get("sampling", {}).get("design_margin_db", 2.0)
        )
    simulation_config = load_simulation_config()
    request = service_request(
        f"trx_{source}",
        f"trx_{destination}",
        mode_name,
        mode,
        channels,
        spacing_hz,
        power_dbm,
        route_nodes,
        float(simulation_config["reference"]["f_min_hz"]),
        float(simulation_config["reference"]["f_max_hz"]),
    )
    apply_scenario_offsets(
        network,
        span_loss_offset_db,
        extra_connector_loss_db,
    )
    designed, req, ref_req = designed_network(
        equipment,
        network,
        source=request.source,
        destination=request.destination,
        nodes_list=request.nodes_list,
        loose_list=request.loose_list,
        service_req=request,
        args_power=power_dbm,
    )
    apply_amplifier_nf_offset(designed, amplifier_nf_offset_db)
    path, propagations, _, infos = transmission_simulation(
        equipment,
        designed,
        req,
        ref_req,
    )
    del propagations
    transceiver = [item for item in path if isinstance(item, Transceiver)][-1]
    fibers = [item for item in path if isinstance(item, Fiber)]
    amplifiers = [item for item in path if isinstance(item, Edfa)]

    gsnr_01nm = mean_db(transceiver.snr_01nm)
    gsnr_signal = mean_db(transceiver.snr)
    osnr_01nm = mean_db(transceiver.osnr_ase_01nm)
    osnr_signal = mean_db(transceiver.osnr_ase)
    snr_nli_01nm = mean_db(getattr(transceiver, "osnr_nli", None))

    if gsnr_signal is None or gsnr_01nm is None:
        raise RuntimeError("GNPy did not return GSNR in both signal and 0.1 nm bandwidths")

    required_osnr_01nm_db = float(mode["OSNR"])
    margin_db, feasible = feasibility_margin(
        gsnr_01nm,
        required_osnr_01nm_db,
        design_margin_db,
    )

    roadms = [item for item in path if isinstance(item, Roadm)]
    simulated_route = [item.uid.removeprefix("roadm_") for item in roadms]
    if route_nodes and simulated_route != list(route_nodes):
        raise RuntimeError(
            f"GNPy route {simulated_route} does not match sampled route {list(route_nodes)}"
        )
    span_lengths = [float(fiber.params.length * 1e-3) for fiber in fibers]
    total_length = sum(span_lengths)
    route = simulated_route
    path_id = (
        scenario_id
        or hashlib.sha1(
            (
                f"{topology_id}|{source}|{destination}|{route}|{mode_name}|{channels}|"
                f"{spacing_hz}|{power_dbm}|{amplifier_nf_offset_db}|{span_loss_offset_db}|"
                f"{extra_connector_loss_db}"
            ).encode()
        ).hexdigest()
    )
    if noise_seed is None:
        noise_seed = int(path_id[:8], 16)
    noise_rng = np.random.default_rng(noise_seed)
    if noise_std_db is None:
        noise_range = simulation_config["sampling"]["noisy_gsnr_std_db"]
        noise_std_db = float(noise_rng.uniform(float(noise_range[0]), float(noise_range[1])))
    gsnr_noisy = gsnr_signal + float(noise_rng.normal(0.0, noise_std_db))
    span_profiles = []
    previous_gsnr = gsnr_signal
    for span_index, fiber in enumerate(fibers):
        span_length = span_lengths[span_index]
        span_profiles.append(
            {
                "path_id": path_id,
                "span_index": span_index,
                "length_km": span_length,
                "loss_db": float(fiber.loss),
                "geometry": [],
                "power_in_dbm": power_dbm,
                "power_out_dbm": power_dbm - float(fiber.loss),
                "cum_ase_noise": None,
                "cum_nli_noise": 0.0,
                "cum_gsnr_db": gsnr_signal,
                "cum_osnr_db": osnr_01nm,
                "gsnr_drop_db": max(0.0, previous_gsnr - gsnr_signal),
            }
        )
        previous_gsnr = gsnr_signal

    result = {
        "path_id": path_id,
        "scenario_id": scenario_id or path_id,
        "seed_index": seed_index,
        "scenario_seed": scenario_seed if scenario_seed is not None else noise_seed,
        "route_rank": route_rank,
        "topology_id": topology_id,
        "source": source,
        "destination": destination,
        "hops": max(0, len(simulated_route) - 1),
        "route": route,
        "simulated_route": simulated_route,
        "total_length_km": float(total_length),
        "n_spans": len(span_lengths),
        "n_amps": len(amplifiers),
        "n_roadms": len(roadms),
        "span_len_mean_km": float(np.mean(span_lengths)) if span_lengths else 0.0,
        "span_len_max_km": float(np.max(span_lengths)) if span_lengths else 0.0,
        "span_len_std_km": float(np.std(span_lengths)) if span_lengths else 0.0,
        "span_loss_mean_db": float(np.mean([fiber.loss for fiber in fibers])) if fibers else 0.0,
        "amp_nf_mean_db": float(np.mean([amplifier.nf[0] for amplifier in amplifiers]))
        if amplifiers
        else 0.0,
        "n_channels": channels,
        "spacing_ghz": spacing_hz / 1e9,
        "baud_gbd": mode["baud_rate"] / 1e9,
        "launch_power_dbm": power_dbm,
        "total_power_dbm": power_dbm + 10 * np.log10(channels),
        "fiber_type": "SSMF",
        "modulation": mode_name,
        "amplifier_nf_offset_db": amplifier_nf_offset_db,
        "span_loss_offset_db": span_loss_offset_db,
        "extra_connector_loss_db": extra_connector_loss_db,
        "required_osnr_01nm_db": required_osnr_01nm_db,
        "gsnr_db": gsnr_signal,
        "gsnr_db_01nm": gsnr_01nm,
        "margin_db": margin_db,
        "design_margin_db": design_margin_db,
        "osnr_01nm_db": osnr_01nm,
        "osnr_db": osnr_signal,
        "snr_nli_db": snr_nli_01nm,
        "noise_std_db": noise_std_db,
        "gsnr_db_noisy": gsnr_noisy,
        "feasible": feasible,
    }
    result["_span_profiles"] = span_profiles
    return result


def _initialize_worker() -> None:
    load_equipment()
    load_mode_config()


def _run_task(task: dict) -> dict:
    try:
        return {"row": run_one(**task), "failure": None}
    except Exception as exc:
        return {
            "row": None,
            "failure": {"type": type(exc).__name__, "reason": str(exc)},
        }


def run_many(tasks: list[dict], workers: int = 1) -> list[dict]:
    if workers < 1:
        raise ValueError("workers must be at least 1")
    indexed_tasks = []
    for task_index, task in enumerate(tasks):
        indexed_task = dict(task)
        indexed_task.setdefault("noise_seed", task_index)
        indexed_tasks.append(indexed_task)
    if workers == 1:
        return [_run_task(task) for task in indexed_tasks]
    with ProcessPoolExecutor(max_workers=workers, initializer=_initialize_worker) as executor:
        return list(executor.map(_run_task, indexed_tasks))
