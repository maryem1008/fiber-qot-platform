import hashlib
import json
import re
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

import gnpy
import networkx as nx
import numpy as np
import yaml
from gnpy.core.elements import Edfa, Fiber, Roadm, Transceiver
from gnpy.core.exceptions import EquipmentConfigError
from gnpy.core.info import carriers_to_spectral_information, create_input_spectral_information
from gnpy.core.network import design_network
from gnpy.core.parameters import TransceiverRole
from gnpy.core.utils import db2lin, dbm2watt, lin2db, snr_sum, watt2dbm
from gnpy.tools.json_io import (
    load_equipments_and_configs,
    load_gnpy_json,
    load_network,
    network_from_json,
)
from gnpy.tools.worker_utils import designed_network
from gnpy.topology.request import PathRequest, compute_constrained_path, filter_si

ROOT = Path(__file__).resolve().parents[3]
SIMULATION_CONFIG_PATH = ROOT / "configs" / "simulation.yaml"
EQUIPMENT_PATH = Path(gnpy.__file__).resolve().parent / "example-data" / "eqpt_config.json"


def mean_db(value):
    if value is None:
        return None
    array = np.asarray(value)
    return float(np.mean(array))


def derive_nli_snr_db(gsnr_db: float, osnr_db: float) -> float | None:
    if gsnr_db is None or osnr_db is None or not np.isfinite(gsnr_db + osnr_db):
        return None
    gsnr_lin = 10 ** (gsnr_db / 10)
    osnr_lin = 10 ** (osnr_db / 10)
    nli_inverse = 1 / gsnr_lin - 1 / osnr_lin
    if nli_inverse <= 0:
        return None
    return float(10 * np.log10(1 / nli_inverse))


def _finite_mean(value) -> float | None:
    if value is None:
        return None
    array = np.asarray(value, dtype=float)
    if array.size == 0 or not np.all(np.isfinite(array)):
        return None
    return float(np.mean(array))


def _snr_after_penalties(values, bandwidth_hz: float, penalties: list) -> float | None:
    inverse_penalty = 0
    for penalty in penalties:
        if penalty is not None:
            inverse_penalty = inverse_penalty + db2lin(-np.asarray(penalty))
    added_snr_db = -lin2db(inverse_penalty)
    return _finite_mean(snr_sum(values, bandwidth_hz, added_snr_db))


def _great_circle_point(
    start: tuple[float, float],
    end: tuple[float, float],
    fraction: float,
) -> dict[str, float]:
    start_latitude, start_longitude = np.deg2rad(start)
    end_latitude, end_longitude = np.deg2rad(end)
    start_vector = np.array(
        [
            np.cos(start_latitude) * np.cos(start_longitude),
            np.cos(start_latitude) * np.sin(start_longitude),
            np.sin(start_latitude),
        ]
    )
    end_vector = np.array(
        [
            np.cos(end_latitude) * np.cos(end_longitude),
            np.cos(end_latitude) * np.sin(end_longitude),
            np.sin(end_latitude),
        ]
    )
    angle = float(np.arccos(np.clip(np.dot(start_vector, end_vector), -1.0, 1.0)))
    if angle < 1e-12:
        vector = start_vector
    elif abs(np.sin(angle)) < 1e-12:
        raise ValueError("great-circle geometry is ambiguous for antipodal link endpoints")
    else:
        vector = (
            np.sin((1 - fraction) * angle) / np.sin(angle) * start_vector
            + np.sin(fraction * angle) / np.sin(angle) * end_vector
        )
        vector /= np.linalg.norm(vector)
    latitude = np.rad2deg(np.arcsin(vector[2]))
    longitude = np.rad2deg(np.arctan2(vector[1], vector[0]))
    return {"latitude": float(latitude), "longitude": float(longitude)}


def _fiber_geometry(fiber_uid: str, topology: dict) -> tuple[list[dict[str, float]], int]:
    match = re.fullmatch(r"fiber_(reverse_)?(\d+)_(\d+)", fiber_uid)
    if match is None:
        raise ValueError(f"{fiber_uid}: does not identify a Phase 1 link span")
    reverse, link_index_text, span_index_text = match.groups()
    link_index = int(link_index_text)
    link_span_index = int(span_index_text)
    link = topology["links"][link_index]
    span_count = len(link["spans_km"])
    if link_span_index >= span_count:
        raise ValueError(f"{fiber_uid}: span index is outside its unified topology link")
    nodes = {node["id"]: node for node in topology["nodes"]}
    start_id, end_id = (
        (link["target"], link["source"])
        if reverse
        else (
            link["source"],
            link["target"],
        )
    )
    start = (nodes[start_id]["latitude"], nodes[start_id]["longitude"])
    end = (nodes[end_id]["latitude"], nodes[end_id]["longitude"])
    start_fraction = link_span_index / span_count
    end_fraction = (link_span_index + 1) / span_count
    return [
        _great_circle_point(start, end, start_fraction),
        _great_circle_point(start, end, end_fraction),
    ], link_span_index


def _propagate_with_span_metrics(
    path: list,
    request: PathRequest,
    equipment: dict,
    topology: dict,
    path_id: str,
) -> tuple[object, list[dict]]:
    if request.initial_spectrum is not None:
        spectral_info = carriers_to_spectral_information(
            initial_spectrum=request.initial_spectrum,
            power=request.power,
        )
    else:
        spectral_info = create_input_spectral_information(
            f_min=request.f_min,
            f_max=request.f_max,
            roll_off=request.roll_off,
            baud_rate=request.baud_rate,
            spacing=request.spacing,
            tx_osnr=request.tx_osnr,
            tx_power=request.tx_power,
            required_osnr_db_01nm=request.required_osnr_db_01nm,
            penalties=request.penalties,
            rx_channel_power_min_dbm=request.rx_channel_power_min_dbm,
            rx_channel_power_max_dbm=request.rx_channel_power_max_dbm,
            detailed_rx=request.detailed_rx,
            delta_pdb=request.offset_db,
        )
    spectral_info = filter_si(path, equipment, spectral_info)
    roadm_osnr = []
    spectral_info = path[0](spectral_info, role=TransceiverRole.EMITTER)
    span_profiles = []
    current_span = None

    for previous, element, next_element in zip(path[:-2], path[1:-1], path[2:]):
        if isinstance(element, Fiber):
            if current_span is not None:
                raise RuntimeError(f"{element.uid}: encountered a second Fiber before an Edfa")
            geometry, link_span_index = _fiber_geometry(element.uid, topology)
            current_span = {
                "fiber": element,
                "link_span_index": link_span_index,
                "power_in_dbm": float(spectral_info.ptot_dbm),
            }
        if isinstance(element, Roadm):
            spectral_info = element(
                spectral_info,
                degree=next_element.uid,
                from_degree=previous.uid,
            )
            roadm_osnr.append(
                element.get_impairment(
                    "roadm-osnr",
                    spectral_info.frequency,
                    from_degree=previous.uid,
                    degree=next_element.uid,
                )
            )
        else:
            spectral_info = element(spectral_info)
        if isinstance(element, Fiber):
            current_span["power_after_fiber_dbm"] = float(spectral_info.ptot_dbm)
        elif isinstance(element, Edfa) and current_span is not None:
            penalties = [*roadm_osnr, spectral_info.tx_osnr]
            fiber = current_span["fiber"]
            gsnr_db = _snr_after_penalties(
                spectral_info.gsnr_db, spectral_info.baud_rate, penalties
            )
            gsnr_db_01nm = _snr_after_penalties(
                spectral_info.opt_gsnr_db,
                12.5e9,
                penalties,
            )
            osnr_db = _snr_after_penalties(
                spectral_info.snr_lin_db,
                spectral_info.baud_rate,
                penalties,
            )
            osnr_db_01nm = _snr_after_penalties(
                spectral_info.opt_snr_lin_db,
                12.5e9,
                penalties,
            )
            nli_snr_db = derive_nli_snr_db(gsnr_db, osnr_db)
            nli_snr_db_01nm = derive_nli_snr_db(gsnr_db_01nm, osnr_db_01nm)
            amplifier_gain_db = _finite_mean(element.effective_gain)
            amplifier_nf_db = _finite_mean(element.nf)
            ase_noise_w = _finite_mean(np.sum(spectral_info.ase))
            nli_noise_w = _finite_mean(np.sum(spectral_info.nli))
            span_profiles.append(
                {
                    "path_id": path_id,
                    "span_index": len(span_profiles),
                    "link_span_index": current_span["link_span_index"],
                    "length_km": float(fiber.params.length * 1e-3),
                    "length_km_available": True,
                    "loss_db": float(fiber.loss),
                    "loss_db_available": True,
                    "geometry": geometry,
                    "geometry_source": "interpolated_great_circle",
                    "geometry_available": True,
                    "power_in_dbm": current_span["power_in_dbm"],
                    "power_in_dbm_available": True,
                    "power_after_fiber_dbm": current_span["power_after_fiber_dbm"],
                    "power_after_fiber_dbm_available": True,
                    "power_out_dbm": float(spectral_info.ptot_dbm),
                    "power_out_dbm_available": True,
                    "amplifier_gain_db": amplifier_gain_db,
                    "amplifier_gain_db_available": amplifier_gain_db is not None,
                    "amplifier_nf_db": amplifier_nf_db,
                    "amplifier_nf_db_available": amplifier_nf_db is not None,
                    "cum_ase_noise_w": ase_noise_w,
                    "cum_ase_noise_w_available": ase_noise_w is not None,
                    "cum_nli_noise_w": nli_noise_w,
                    "cum_nli_noise_w_available": nli_noise_w is not None,
                    "cum_gsnr_db": gsnr_db,
                    "cum_gsnr_db_available": gsnr_db is not None,
                    "cum_gsnr_db_01nm": gsnr_db_01nm,
                    "cum_gsnr_db_01nm_available": gsnr_db_01nm is not None,
                    "cum_osnr_ase_db": osnr_db,
                    "cum_osnr_ase_db_available": osnr_db is not None,
                    "cum_osnr_ase_db_01nm": osnr_db_01nm,
                    "cum_osnr_ase_db_01nm_available": osnr_db_01nm is not None,
                    "cum_snr_nli_db": nli_snr_db,
                    "cum_snr_nli_db_available": nli_snr_db is not None,
                    "cum_snr_nli_db_01nm": nli_snr_db_01nm,
                    "cum_snr_nli_db_01nm_available": nli_snr_db_01nm is not None,
                    "cum_snr_nli_db_invalid": (
                        nli_snr_db is None and gsnr_db is not None and osnr_db is not None
                    ),
                    "cum_snr_nli_db_01nm_invalid": (
                        nli_snr_db_01nm is None
                        and gsnr_db_01nm is not None
                        and osnr_db_01nm is not None
                    ),
                }
            )
            current_span = None

    if current_span is not None:
        raise RuntimeError(f"{current_span['fiber'].uid}: no following Edfa was found")
    spectral_info = path[-1](spectral_info, role=TransceiverRole.RECEIVER)
    path[0].update_snr(spectral_info.tx_osnr)
    roadm_osnr.append(spectral_info.tx_osnr)
    path[-1].update_snr(*roadm_osnr)
    path[-1].update_rx_snr(spectral_info)
    path[-1].calc_feasibility(spectral_info)

    if span_profiles:
        transceiver = path[-1]
        final_values = {
            "cum_gsnr_db": _finite_mean(transceiver.snr),
            "cum_gsnr_db_01nm": _finite_mean(transceiver.snr_01nm),
            "cum_osnr_ase_db": _finite_mean(transceiver.osnr_ase),
            "cum_osnr_ase_db_01nm": _finite_mean(transceiver.osnr_ase_01nm),
        }
        last_profile = span_profiles[-1]
        for name, value in final_values.items():
            last_profile[name] = value
            last_profile[f"{name}_available"] = value is not None
        last_profile["cum_snr_nli_db"] = derive_nli_snr_db(
            final_values["cum_gsnr_db"],
            final_values["cum_osnr_ase_db"],
        )
        last_profile["cum_snr_nli_db_01nm"] = derive_nli_snr_db(
            final_values["cum_gsnr_db_01nm"],
            final_values["cum_osnr_ase_db_01nm"],
        )
        for name in ("cum_snr_nli_db", "cum_snr_nli_db_01nm"):
            last_profile[f"{name}_available"] = last_profile[name] is not None
        last_profile["cum_snr_nli_db_invalid"] = (
            last_profile["cum_snr_nli_db"] is None
            and final_values["cum_gsnr_db"] is not None
            and final_values["cum_osnr_ase_db"] is not None
        )
        last_profile["cum_snr_nli_db_01nm_invalid"] = (
            last_profile["cum_snr_nli_db_01nm"] is None
            and final_values["cum_gsnr_db_01nm"] is not None
            and final_values["cum_osnr_ase_db_01nm"] is not None
        )

    previous_gsnr = mean_db(path[0].snr_01nm)
    for profile in span_profiles:
        current_gsnr = profile["cum_gsnr_db_01nm"]
        profile["gsnr_drop_db"] = (
            previous_gsnr - current_gsnr
            if previous_gsnr is not None and current_gsnr is not None
            else None
        )
        profile["gsnr_drop_db_available"] = profile["gsnr_drop_db"] is not None
        previous_gsnr = current_gsnr
    return spectral_info, span_profiles


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
    path = compute_constrained_path(designed, req)
    if not path:
        raise RuntimeError(
            "GNPy could not compute a constrained path from "
            f"{request.source} to {request.destination}"
        )
    power_mode = equipment["Span"]["default"].power_mode
    reference_power_dbm = watt2dbm(ref_req.power)
    request_power_dbm = watt2dbm(req.power)
    power_range = [0]
    if power_mode:
        try:
            power_start, power_stop, power_step = equipment["SI"]["default"].power_range_db
            power_count = (
                abs(int(round((power_stop - power_start) / power_step))) + 1
                if power_step != 0
                else 1
            )
            power_range = list(np.linspace(power_start, power_stop, power_count))
        except TypeError as exc:
            message = (
                "invalid power range definition in eqpt_config, "
                "expected power_range_db: [lower, upper, step]"
            )
            raise EquipmentConfigError(message) from exc
    topology_data = json.loads(unified_path.read_text(encoding="utf-8"))
    span_profiles = []
    for power_offset_db in power_range:
        ref_req.power = dbm2watt(reference_power_dbm + power_offset_db)
        req.power = dbm2watt(request_power_dbm + power_offset_db)
        if len(power_range) > 1:
            design_network(
                ref_req,
                designed.subgraph(path),
                equipment,
                set_connector_losses=False,
                verbose=False,
            )
            apply_amplifier_nf_offset(path, amplifier_nf_offset_db)
        _, span_profiles = _propagate_with_span_metrics(
            path,
            req,
            equipment,
            topology_data,
            scenario_id or f"{topology_id}:{source}:{destination}",
        )
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
    for profile in span_profiles:
        profile["path_id"] = path_id
    if noise_seed is None:
        noise_seed = int(path_id[:8], 16)
    noise_rng = np.random.default_rng(noise_seed)
    if noise_std_db is None:
        noise_range = simulation_config["sampling"]["noisy_gsnr_std_db"]
        noise_std_db = float(noise_rng.uniform(float(noise_range[0]), float(noise_range[1])))
    gsnr_noisy = gsnr_signal + float(noise_rng.normal(0.0, noise_std_db))
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
