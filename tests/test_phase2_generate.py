import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import phase2_generate

ROOT = Path(__file__).resolve().parents[1]


class FakeScenario:
    def __init__(self, index: int) -> None:
        self.scenario_id = f"scenario-{index:04d}"
        self.topology_id = "tunisia"
        self.source = "Bizerte"
        self.destination = "Sfax"

    def to_run_task(self) -> dict:
        return {"scenario_id": self.scenario_id, "seed_index": int(self.scenario_id[-4:])}


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
            path_row = dict.fromkeys(phase2_generate.PATH_REQUIRED_COLUMNS, 0)
            path_row.update(
                {
                    "path_id": scenario_id,
                    "scenario_id": scenario_id,
                    "feasible": False,
                    "snr_nli_db": None if index == 1 else 30.0,
                    "snr_nli_db_available": index != 1,
                    "snr_nli_db_invalid": index == 1,
                    "snr_nli_01nm_db": None if index == 1 else 34.0,
                    "snr_nli_01nm_db_available": index != 1,
                    "snr_nli_01nm_db_invalid": index == 1,
                }
            )
            span_row = dict.fromkeys(phase2_generate.SPAN_REQUIRED_COLUMNS, 0)
            span_row.update(
                {
                    "path_id": scenario_id,
                    "span_index": 0,
                    "cum_snr_nli_db": None if index == 1 else 30.0,
                    "cum_snr_nli_db_available": index != 1,
                    "cum_snr_nli_db_invalid": index == 1,
                    "cum_snr_nli_db_01nm": None if index == 1 else 34.0,
                    "cum_snr_nli_db_01nm_available": index != 1,
                    "cum_snr_nli_db_01nm_invalid": index == 1,
                }
            )
            outcomes.append(
                {
                    "row": {
                        **path_row,
                        "sample_value": index,
                        "_span_profiles": [span_row],
                    },
                    "failure": None,
                }
            )
    return outcomes


def test_generation_resumes_completed_chunks_identically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = {"test_config": "chunk-resume"}
    monkeypatch.setattr(
        phase2_generate,
        "sample_scenarios_with_stats",
        lambda topologies, n, seed, config: ([FakeScenario(i) for i in range(n)], 3),
    )
    selected = [
        ("tunisia", ROOT / "data" / "topologies" / "tunisia.json"),
    ]
    monkeypatch.setattr(phase2_generate, "selected_topologies", lambda: selected)
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
            gnpy_version="test-stub",
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
        gnpy_version="test-stub",
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
        gnpy_version="test-stub",
    )

    assert resumed_calls == [100, 100, 100, 100]
    assert resumed_manifest["status"] == "complete"
    assert resumed_manifest["requested"] == 600
    assert resumed_manifest["attempted"] == 600
    assert resumed_manifest["successful"] == 564
    assert resumed_manifest["failed"] == 36
    assert resumed_manifest["rejected"] == 3
    assert resumed_manifest["duplicate_scenario_ids"] == 0
    assert resumed_manifest["required_column_null_counts"]["paths"]["snr_nli_db"] == 1
    assert resumed_manifest["required_column_null_counts"]["spans"]["cum_snr_nli_db"] == 1

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
        gnpy_version="test-stub",
    )
    assert unchanged_manifest == resumed_manifest

    all_failed_manifest = phase2_generate.generate_run(
        "all-failed",
        1,
        41,
        1,
        1,
        config,
        tmp_path,
        runner=_fake_outcomes,
        gnpy_version="test-stub",
    )
    assert all_failed_manifest["successful"] == 0
    assert all_failed_manifest["failed"] == 1
    empty_paths = pd.read_parquet(tmp_path / "all-failed" / "paths.parquet")
    empty_spans = pd.read_parquet(tmp_path / "all-failed" / "spans.parquet")
    assert set(phase2_generate.PATH_REQUIRED_COLUMNS) <= set(empty_paths.columns)
    assert set(phase2_generate.SPAN_REQUIRED_COLUMNS) <= set(empty_spans.columns)
    assert all_failed_manifest["required_column_null_counts"]["paths"]["snr_nli_db"] == 0
