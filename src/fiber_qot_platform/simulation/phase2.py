import hashlib
import json
from pathlib import Path

import networkx as nx
import numpy as np
from gnpy.core.elements import Edfa, Fiber, Transceiver
from gnpy.core.utils import dbm2watt
from gnpy.tools.json_io import load_equipments_and_configs, load_network
from gnpy.tools.worker_utils import designed_network, transmission_simulation
from gnpy.topology.request import PathRequest

ROOT = Path(__file__).resolve().parents[3]
EQUIPMENT_PATH = (
    ROOT / ".venv" / "Lib" / "site-packages" / "gnpy" / "example-data" / "eqpt_config.json"
)


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


def load_mode_config() -> dict:
    equipment = load_equipments_and_configs(EQUIPMENT_PATH, [], [])
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


def load_topology_unified(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def service_request(
    source: str,
    destination: str,
    mode_name: str,
    mode: dict,
    channels: int,
    spacing_hz: float,
    power_dbm: float,
    margin_db: float,
) -> PathRequest:
    del margin_db
    return PathRequest(
        request_id=f"{source}-{destination}-{mode_name}",
        source=source,
        destination=destination,
        bidir=False,
        trx_type="Voyager",
        trx_mode=mode_name,
        baud_rate=mode["baud_rate"],
        nodes_list=[destination],
        loose_list=["STRICT"],
        format=mode_name,
        spacing=spacing_hz,
        nb_channel=channels,
        power=dbm2watt(power_dbm),
        tx_power=dbm2watt(power_dbm),
        OSNR=mode["OSNR"],
        f_min=191350000000000.0,
        f_max=196100000000000.0,
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
    margin_db: float,
) -> dict:
    gnpy_path = unified_path.with_name(f"{unified_path.stem}_gnpy.json")
    equipment = load_equipments_and_configs(EQUIPMENT_PATH, [], [])
    network = load_network(gnpy_path, equipment)
    request = service_request(
        f"trx_{source}",
        f"trx_{destination}",
        mode_name,
        mode,
        channels,
        spacing_hz,
        power_dbm,
        margin_db,
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

    if gsnr_signal is None:
        raise RuntimeError("GNPy did not return a signal-bandwidth GSNR")

    feasible = gsnr_signal >= mode["OSNR"] + margin_db

    topology = load_topology_unified(unified_path)
    route_graph = graph_for(topology)
    route = nx.shortest_path(
        route_graph,
        source,
        destination,
        weight="weight",
    )
    total_length = nx.path_weight(route_graph, route, "weight")
    span_lengths = [float(fiber.params.length * 1e-3) for fiber in fibers]
    path_id = hashlib.sha1(
        (
            f"{topology_id}|{source}|{destination}|{mode_name}|{channels}|{spacing_hz}|{power_dbm}"
        ).encode()
    ).hexdigest()
    noise_seed = int(path_id[:8], 16)
    gsnr_noisy = gsnr_signal + float(np.random.default_rng(noise_seed).normal(0.0, 0.35))
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
        "topology_id": topology_id,
        "source": source,
        "destination": destination,
        "hops": max(0, len(route) - 1),
        "route": route,
        "total_length_km": float(total_length),
        "n_spans": len(span_lengths),
        "n_amps": len(amplifiers),
        "n_roadms": len(route),
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
        "required_gsnr_db": mode["OSNR"],
        "gsnr_db": gsnr_signal,
        "gsnr_db_01nm": gsnr_01nm,
        "osnr_01nm_db": osnr_01nm,
        "osnr_db": osnr_signal,
        "snr_nli_db": snr_nli_01nm,
        "gsnr_db_noisy": gsnr_noisy,
        "feasible": feasible,
    }
    result["_span_profiles"] = span_profiles
    return result
