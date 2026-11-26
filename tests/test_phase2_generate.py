import json
from pathlib import Path

import pandas as pd
import pytest

from fiber_qot_platform.simulation.phase2 import load_mode_config, load_simulation_config
from fiber_qot_platform.simulation.sampling import sample_scenarios_with_stats
from scripts import phase2_generate

ROOT = Path(__file__).resolve().parents[1]


def _fake_outcomes(tasks: list[dict], workers: int = 1) -> list[dict]:
    outcomes = []
    for task in tasks:
        scenario_id = task["scenario_id"]
        index = task["seed_index"]
        if index % 17 == 0:
            outcomes.append(
                {
                    "row": None,
                    "failure": {"type": "TestFailure", "reason": "deterministic test failure"},
                }
            )
        else:
            outcomes.append(
                {
                    "row": {
                        "scenario_id": scenario_id,
                        "sample_value": index,
                        "_span_profiles": [{"path_id": scenario_id, "span_index": 0}],
                    },
                    "failure": None,
                }
            )
    return outcomes


def test_generation_resumes_completed_chunks_identically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_simulation_config()
    config["transceiver"]["mode_parameters"] = load_mode_config()
    selected = [
        ("tunisia", ROOT / "data" / "topologies" / "tunisia.json"),
    ]
    monkeypatch.setattr(phase2_generate, "selected_topologies", lambda: selected)
    topology = json.loads(selected[0][1].read_text(encoding="utf-8"))
    topology["unified_path"] = str(selected[0][1])
    _, expected_rejected = sample_scenarios_with_stats([topology], 600, 41, config)
    interrupted_calls = 0

    def interrupt_after_two_chunks(tasks: list[dict], workers: int) -> list[dict]:
        nonlocal interrupted_calls
        interrupted_calls += 1
        if interrupted_calls == 3:
            raise RuntimeError("simulated interruption after two chunks")
        return _fake_outcomes(tasks)

    with pytest.raises(RuntimeError, match="simulated interruption"):
        phase2_generate.generate_run(
            "resumed",
            600,
            41,
            100,
            1,
            config,
            tmp_path,
            runner=interrupt_after_two_chunks,
        )

    resumed_dir = tmp_path / "resumed"
    partial_manifest = json.loads((resumed_dir / "manifest.json").read_text(encoding="utf-8"))
    assert partial_manifest["status"] == "running"
    assert partial_manifest["attempted"] == 200
    assert (resumed_dir / "chunk_00002_spans.parquet").is_file()
    assert len((resumed_dir / "failures.jsonl").read_text(encoding="utf-8").splitlines()) == 12
    assert not (resumed_dir / "chunk_00003.json").exists()

    resumed_calls = []

    def resumed_runner(tasks: list[dict], workers: int) -> list[dict]:
        resumed_calls.append(len(tasks))
        return _fake_outcomes(tasks)

    resumed_manifest = phase2_generate.generate_run(
        "resumed",
        600,
        41,
        100,
        1,
        config,
        tmp_path,
        runner=resumed_runner,
    )
    uninterrupted_manifest = phase2_generate.generate_run(
        "uninterrupted",
        600,
        41,
        100,
        1,
        config,
        tmp_path,
        runner=_fake_outcomes,
    )

    assert resumed_calls == [100, 100, 100, 100]
    assert resumed_manifest["status"] == "complete"
    assert resumed_manifest["requested"] == 600
    assert resumed_manifest["attempted"] == 600
    assert resumed_manifest["successful"] == 564
    assert resumed_manifest["failed"] == 36
    assert resumed_manifest["rejected"] == expected_rejected
    assert resumed_manifest["duplicate_scenario_ids"] == 0

    pd.testing.assert_frame_equal(
        pd.read_parquet(resumed_dir / "paths.parquet"),
        pd.read_parquet(tmp_path / "uninterrupted" / "paths.parquet"),
    )
    pd.testing.assert_frame_equal(
        pd.read_parquet(resumed_dir / "spans.parquet"),
        pd.read_parquet(tmp_path / "uninterrupted" / "spans.parquet"),
    )
    assert (resumed_dir / "failures.jsonl").read_bytes() == (
        tmp_path / "uninterrupted" / "failures.jsonl"
    ).read_bytes()
    assert uninterrupted_manifest["attempted"] == 600

    def fail_if_run(tasks: list[dict], workers: int) -> list[dict]:
        raise AssertionError("completed run must not be overwritten")

    unchanged_manifest = phase2_generate.generate_run(
        "resumed",
        600,
        41,
        100,
        1,
        config,
        tmp_path,
        runner=fail_if_run,
    )
    assert unchanged_manifest == resumed_manifest
