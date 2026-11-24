from pathlib import Path

from fiber_qot_platform.topology.phase1 import (
    build_tunisia,
    make_unified,
    split_link,
    to_gnpy_network,
)

ROOT = Path(__file__).resolve().parents[1]


def test_split_link_never_exceeds_limit() -> None:
    assert split_link(240.0, 80.0) == [80.0, 80.0, 80.0]
    assert split_link(161.5, 80.0) == [80.0, 80.0, 1.5]


def test_tunisia_is_illustrative_connected_and_complete() -> None:
    nodes, links = build_tunisia()
    topology = make_unified("tunisia", "synthetic", nodes, links)
    assert topology["illustrative"] is True
    assert len(topology["nodes"]) == 12
    assert len(topology["links"]) == 14


def test_gnpy_converter_emits_bidirectional_connections() -> None:
    topology = make_unified(
        "test",
        "unit-test",
        {
            "A": {"id": "A", "name": "A", "latitude": 0.0, "longitude": 0.0},
            "B": {"id": "B", "name": "B", "latitude": 1.0, "longitude": 1.0},
        },
        [{"source": "A", "target": "B", "length_km": 40.0}],
    )
    network = to_gnpy_network(topology)
    connection_set = {
        (connection["from_node"], connection["to_node"]) for connection in network["connections"]
    }
    assert ("roadm_A", "trx_A") in connection_set
    assert ("trx_A", "roadm_A") in connection_set
