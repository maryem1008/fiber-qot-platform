from pathlib import Path

import pytest

from fiber_qot_platform.topology.phase1 import (
    build_tunisia,
    make_unified,
    split_link,
    to_gnpy_network,
)

ROOT = Path(__file__).resolve().parents[1]


def test_split_link_uses_equal_spans_within_limit() -> None:
    for length_km in (240.0, 161.5, 100.0, 85.0):
        spans = split_link(length_km, 80.0)
        assert sum(spans) == pytest.approx(length_km)
        assert all(span == pytest.approx(spans[0]) for span in spans)
        assert max(spans) <= 80.0
    assert split_link(100.0, 80.0) == [50.0, 50.0]
    assert split_link(85.0, 80.0) == [42.5, 42.5]
    assert split_link(0.0, 80.0) == [0.0]


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
