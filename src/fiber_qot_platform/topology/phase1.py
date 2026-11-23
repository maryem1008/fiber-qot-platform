import math
import xml.etree.ElementTree as ET
from pathlib import Path

import networkx as nx

GRAPHML_NS = {"g": "http://graphml.graphdrawing.org/xmlns"}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * radius_km * math.asin(min(1.0, math.sqrt(a)))


def parse_graphml(path: Path) -> tuple[dict[str, dict], list[dict]]:
    root = ET.parse(path).getroot()
    graph = root.find(".//g:graph", GRAPHML_NS)
    if graph is None:
        raise ValueError(f"{path}: no GraphML graph found")

    key_names = {
        key.attrib["id"]: key.attrib.get("attr.name") for key in root.findall("g:key", GRAPHML_NS)
    }
    nodes: dict[str, dict] = {}
    for node in graph.findall("g:node", GRAPHML_NS):
        data = {
            key_names[data.attrib["key"]]: (data.text or "").strip()
            for data in node.findall("g:data", GRAPHML_NS)
            if data.attrib["key"] in key_names
        }
        lat_key = "Latitude" if "Latitude" in data else "latitude"
        lon_key = "Longitude" if "Longitude" in data else "longitude"
        if lat_key not in data or lon_key not in data:
            raise ValueError(f"{path}: node {node.attrib['id']} has no latitude/longitude")
        lat = float(data[lat_key])
        lon = float(data[lon_key])
        node_id = data.get("label") or node.attrib["id"]
        nodes[node_id] = {"id": node_id, "name": node_id, "latitude": lat, "longitude": lon}

    id_to_name = {}
    for raw_id, node in zip(
        [n.attrib["id"] for n in graph.findall("g:node", GRAPHML_NS)],
        nodes.values(),
    ):
        id_to_name[raw_id] = node["id"]

    links = []
    seen = set()
    for edge in graph.findall("g:edge", GRAPHML_NS):
        source = id_to_name.get(edge.attrib["source"], edge.attrib["source"])
        target = id_to_name.get(edge.attrib["target"], edge.attrib["target"])
        if source == target:
            continue
        key = tuple(sorted((source, target)))
        if key in seen:
            continue
        seen.add(key)
        source_node = nodes[source]
        target_node = nodes[target]
        length = haversine_km(
            source_node["latitude"],
            source_node["longitude"],
            target_node["latitude"],
            target_node["longitude"],
        )
        links.append({"source": source, "target": target, "length_km": length})
    return nodes, links


def parse_sndlib(path: Path) -> tuple[dict[str, dict], list[dict]]:
    ns = {"s": "http://sndlib.zib.de/network"}
    root = ET.parse(path).getroot()
    nodes = {}
    node_container = root.find(".//s:networkStructure/s:nodes", ns)
    if node_container is None:
        raise ValueError(f"{path}: no SNDlib node structure found")
    for node in node_container.findall("s:node", ns):
        node_id = node.attrib["id"]
        coordinates = node.find("s:coordinates", ns)
        if coordinates is None:
            continue
        x = coordinates.find("s:x", ns)
        y = coordinates.find("s:y", ns)
        if x is None or y is None:
            continue
        lon = float(x.text)
        lat = float(y.text)
        nodes[node_id] = {"id": node_id, "name": node_id, "latitude": lat, "longitude": lon}

    links = []
    seen = set()
    link_container = root.find(".//s:networkStructure/s:links", ns)
    if link_container is None:
        raise ValueError(f"{path}: no SNDlib links found")
    for link in link_container.findall("s:link", ns):
        source = link.find("s:source", ns)
        target = link.find("s:target", ns)
        if source is None or target is None or source.text not in nodes or target.text not in nodes:
            continue
        source_id, target_id = source.text, target.text
        key = tuple(sorted((source_id, target_id)))
        if key in seen:
            continue
        seen.add(key)
        source_node = nodes[source_id]
        target_node = nodes[target_id]
        links.append(
            {
                "source": source_id,
                "target": target_id,
                "length_km": haversine_km(
                    source_node["latitude"],
                    source_node["longitude"],
                    target_node["latitude"],
                    target_node["longitude"],
                ),
            }
        )
    return nodes, links


def build_tunisia() -> tuple[dict[str, dict], list[dict]]:
    cities = [
        ("Bizerte", 37.2744, 9.8739),
        ("Tunis", 36.8065, 10.1815),
        ("Nabeul", 36.4513, 10.7351),
        ("Sousse", 35.8256, 10.6369),
        ("Monastir", 35.7780, 10.8262),
        ("Kairouan", 35.6781, 10.0963),
        ("Sfax", 34.7406, 10.7603),
        ("Gabes", 33.8885, 10.0982),
        ("Gafsa", 34.4250, 8.7842),
        ("Tozeur", 33.9197, 8.1335),
        ("Medenine", 33.3549, 10.5055),
        ("Kef", 36.1743, 8.7049),
    ]
    nodes = {
        name: {"id": name, "name": name, "latitude": lat, "longitude": lon}
        for name, lat, lon in cities
    }
    ring = [
        ("Bizerte", "Tunis"),
        ("Tunis", "Nabeul"),
        ("Nabeul", "Sousse"),
        ("Sousse", "Monastir"),
        ("Monastir", "Sfax"),
        ("Sfax", "Gabes"),
        ("Gabes", "Medenine"),
        ("Medenine", "Sfax"),
        ("Sfax", "Kairouan"),
        ("Kairouan", "Tunis"),
        ("Tunis", "Kef"),
        ("Kef", "Gafsa"),
        ("Gafsa", "Tozeur"),
        ("Tozeur", "Gabes"),
    ]
    links = []
    seen = set()
    for source, target in ring:
        key = tuple(sorted((source, target)))
        if key in seen:
            continue
        seen.add(key)
        a, b = nodes[source], nodes[target]
        length = haversine_km(a["latitude"], a["longitude"], b["latitude"], b["longitude"]) * 1.25
        links.append({"source": source, "target": target, "length_km": length})
    return nodes, links


def split_link(length_km: float, max_span_km: float = 80.0) -> list[float]:
    count = max(1, math.ceil(length_km / max_span_km))
    remainder = length_km
    spans = []
    for _ in range(count):
        span = min(max_span_km, remainder)
        spans.append(round(span, 3))
        remainder -= span
    return spans


def make_unified(
    topology_id: str,
    source: str,
    nodes: dict[str, dict],
    links: list[dict],
    route_factor: float = 1.0,
) -> dict:
    graph_links = []
    for link in links:
        length = round(float(link["length_km"]) * route_factor, 3)
        graph_links.append(
            {
                "source": link["source"],
                "target": link["target"],
                "length_km": length,
                "spans_km": split_link(length),
            }
        )
    graph = nx.Graph()
    for node_id, node in nodes.items():
        graph.add_node(node_id, **node)
    graph.add_edges_from((link["source"], link["target"]) for link in graph_links)
    if len(graph) == 0 or not nx.is_connected(graph):
        raise ValueError(f"{topology_id}: topology is empty or disconnected")
    return {
        "topology_id": topology_id,
        "source": source,
        "illustrative": topology_id == "tunisia",
        "nodes": list(nodes.values()),
        "links": graph_links,
    }


def to_gnpy_network(topology: dict) -> dict:
    elements = []
    connections = []
    for node in topology["nodes"]:
        roadm_uid = f"roadm_{node['id']}"
        trx_uid = f"trx_{node['id']}"
        elements.append(
            {
                "uid": trx_uid,
                "type": "Transceiver",
                "metadata": {
                    "location": {
                        "city": node["name"],
                        "latitude": node["latitude"],
                        "longitude": node["longitude"],
                    }
                },
            }
        )
        elements.append(
            {
                "uid": roadm_uid,
                "type": "Roadm",
                "type_variety": "roadm_type_1",
                "metadata": {
                    "location": {
                        "city": node["name"],
                        "latitude": node["latitude"],
                        "longitude": node["longitude"],
                    }
                },
            }
        )
        connections.extend(
            [
                {"from_node": trx_uid, "to_node": roadm_uid},
                {"from_node": roadm_uid, "to_node": trx_uid},
            ]
        )
    for index, link in enumerate(topology["links"]):
        left = f"roadm_{link['source']}"
        right = f"roadm_{link['target']}"
        for span_index, span_km in enumerate(link["spans_km"]):
            fiber_uid = f"fiber_{index}_{span_index}"
            edfa_uid = f"edfa_{index}_{span_index}"
            elements.append(
                {
                    "uid": fiber_uid,
                    "type": "Fiber",
                    "type_variety": "SSMF",
                    "params": {
                        "length": span_km,
                        "length_units": "km",
                        "loss_coef": 0.2,
                        "att_in": 0.0,
                        "con_in": 0.5,
                        "con_out": 0.5,
                    },
                    "metadata": {"location": {"latitude": 0.0, "longitude": 0.0}},
                }
            )
            elements.append(
                {
                    "uid": edfa_uid,
                    "type": "Edfa",
                    "type_variety": "std_medium_gain",
                    "operational": {"gain_target": 16.0, "tilt_target": 0.0, "out_voa": 0.0},
                    "metadata": {"location": {"latitude": 0.0, "longitude": 0.0}},
                }
            )
        for span_index in range(len(link["spans_km"])):
            fiber_uid = f"fiber_{index}_{span_index}"
            edfa_uid = f"edfa_{index}_{span_index}"
            previous = left if span_index == 0 else f"edfa_{index}_{span_index - 1}"
            connections.extend(
                [
                    {"from_node": previous, "to_node": fiber_uid},
                    {"from_node": fiber_uid, "to_node": edfa_uid},
                ]
            )
            if span_index == len(link["spans_km"]) - 1:
                connections.append({"from_node": edfa_uid, "to_node": right})

    return {
        "network_name": f"{topology['topology_id']} - Phase 1 GNPy network",
        "elements": elements,
        "connections": connections,
    }
