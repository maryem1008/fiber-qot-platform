from pathlib import Path

from fiber_qot_platform.topology.phase1 import build_tunisia, make_unified, split_link

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
