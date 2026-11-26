import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fiber_qot_platform.simulation.sampling import (  # noqa: E402
    sample_scenarios_with_stats,
)

PATH_REQUIRED_COLUMNS = (
    "path_id",
    "scenario_id",
    "gsnr_db",
    "gsnr_db_01nm",
    "osnr_db",
    "osnr_01nm_db",
    "required_osnr_01nm_db",
    "margin_db",
    "feasible",
    "snr_nli_db",
    "snr_nli_db_available",
    "snr_nli_db_invalid",
    "snr_nli_01nm_db",
    "snr_nli_01nm_db_available",
    "snr_nli_01nm_db_invalid",
)
SPAN_REQUIRED_COLUMNS = (
    "path_id",
    "span_index",
    "cum_ase_noise_w",
    "cum_nli_noise_w",
    "cum_gsnr_db",
    "cum_gsnr_db_available",
    "cum_gsnr_db_01nm",
    "cum_gsnr_db_01nm_available",
    "cum_osnr_ase_db",
    "cum_osnr_ase_db_available",
    "cum_osnr_ase_db_01nm",
    "cum_osnr_ase_db_01nm_available",
    "cum_snr_nli_db",
    "cum_snr_nli_db_available",
    "cum_snr_nli_db_invalid",
    "cum_snr_nli_db_01nm",
    "cum_snr_nli_db_01nm_available",
    "cum_snr_nli_db_01nm_invalid",
)


def selected_topologies() -> list[tuple[str, Path]]:
    manifest = json.loads(
        (ROOT / "data" / "topologies" / "phase1_manifest.json").read_text(encoding="utf-8")
    )
    accepted = {}
    for item in manifest["topologies"]:
        if item["status"] != "converted":
            continue
        topology_id = item["topology_id"]
        if topology_id.startswith("zoo_") or topology_id.startswith("sndlib_"):
            accepted[topology_id] = ROOT / "data" / "topologies" / f"{topology_id}.json"
    accepted["tunisia"] = ROOT / "data" / "topologies" / "tunisia.json"
    return sorted(accepted.items())


def _sha256_json(value: object) -> str:
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(text)
            temporary.flush()
            os.fsync(temporary.fileno())
        temporary_path.replace(path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def _atomic_write_json(path: Path, value: object) -> None:
    _atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def _atomic_write_jsonl(path: Path, records: list[dict]) -> None:
    text = "".join(json.dumps(record, sort_keys=True, default=str) + "\n" for record in records)
    _atomic_write_text(path, text)


def _atomic_write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        frame.to_parquet(temporary_path, index=False)
        temporary_path.replace(path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _run_directory(output_root: Path, run_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", run_id):
        raise ValueError("run_id must use 1-128 letters, digits, dots, underscores, or hyphens")
    if run_id in {".", ".."}:
        raise ValueError("run_id must not be a path traversal component")
    root = output_root.resolve()
    run_directory = (root / run_id).resolve()
    if run_directory.parent != root:
        raise ValueError("run_id must resolve to a direct child of the generated-data directory")
    return run_directory


def _reset_run_directory(run_directory: Path) -> None:
    if not run_directory.exists():
        return
    if not run_directory.is_dir():
        raise ValueError(f"{run_directory}: expected a run directory")
    fixed_names = {"manifest.json", "failures.jsonl", "paths.parquet", "spans.parquet"}
    chunk_file = re.compile(r"chunk_\d{5}(?:_spans|_failures)?\.(?:parquet|json|jsonl)")
    temporary_file = re.compile(
        r"\.(?:manifest\.json|failures\.jsonl|paths\.parquet|spans\.parquet|"
        r"chunk_\d{5}(?:_spans|_failures)?\.(?:parquet|json|jsonl))\.[A-Za-z0-9_-]+\.tmp"
    )
    for existing in run_directory.iterdir():
        if not existing.is_file() or (
            existing.name not in fixed_names
            and not chunk_file.fullmatch(existing.name)
            and not temporary_file.fullmatch(existing.name)
        ):
            raise ValueError(f"{existing}: refusing to remove an unexpected run-directory entry")
        existing.unlink()


def _chunk_paths(run_directory: Path, chunk_number: int) -> dict[str, Path]:
    stem = f"chunk_{chunk_number:05d}"
    return {
        "paths": run_directory / f"{stem}.parquet",
        "spans": run_directory / f"{stem}_spans.parquet",
        "failures": run_directory / f"{stem}_failures.jsonl",
        "metadata": run_directory / f"{stem}.json",
    }


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"{path}: required chunk failure log is missing")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _validate_required_columns(
    frame: pd.DataFrame,
    required_columns: tuple[str, ...],
    table_name: str,
) -> dict[str, int]:
    missing_columns = sorted(set(required_columns) - set(frame.columns))
    if missing_columns:
        raise RuntimeError(f"{table_name}: missing required columns {missing_columns}")
    return {str(column): int(frame[column].isna().sum()) for column in frame.columns}


def _write_aggregate_failures(run_directory: Path, chunk_summaries: list[dict]) -> None:
    failure_records = []
    for summary in sorted(chunk_summaries, key=lambda item: item["chunk_number"]):
        failure_records.extend(
            _read_jsonl(_chunk_paths(run_directory, summary["chunk_number"])["failures"])
        )
    _atomic_write_jsonl(run_directory / "failures.jsonl", failure_records)


def _chunk_summaries(run_directory: Path, chunk_count: int) -> list[dict]:
    summaries = []
    for chunk_number in range(1, chunk_count + 1):
        paths = _chunk_paths(run_directory, chunk_number)
        if not paths["metadata"].exists():
            continue
        summary = json.loads(paths["metadata"].read_text(encoding="utf-8"))
        if summary["chunk_number"] != chunk_number:
            raise RuntimeError(f"{paths['metadata']}: chunk number does not match its filename")
        if not all(paths[name].is_file() for name in ("paths", "spans", "failures")):
            raise RuntimeError(f"{paths['metadata']}: completed chunk has missing output files")
        if len(_read_jsonl(paths["failures"])) != summary["failed"]:
            raise RuntimeError(f"{paths['metadata']}: failure count does not match chunk log")
        if (
            summary["attempted"] != len(summary["scenario_ids"])
            or summary["attempted"] != summary["successful"] + summary["failed"]
        ):
            raise RuntimeError(f"{paths['metadata']}: chunk counts are inconsistent")
        summaries.append(summary)
    return summaries


def merge_run_directory(run_directory: Path) -> tuple[Path, Path, dict[str, dict[str, int]]]:
    run_directory = run_directory.resolve()
    manifest_path = run_directory / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"{run_directory}: manifest.json is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise RuntimeError(f"{run_directory}: cannot merge an incomplete run")
    chunk_numbers = sorted(
        int(match.group(1))
        for item in run_directory.iterdir()
        if (match := re.fullmatch(r"chunk_(\d{5})\.json", item.name))
    )
    if not chunk_numbers:
        raise RuntimeError(f"{run_directory}: no completed chunks to merge")
    if chunk_numbers != list(range(1, len(chunk_numbers) + 1)):
        raise RuntimeError(f"{run_directory}: chunk sequence has gaps")
    if chunk_numbers != list(range(1, manifest["chunk_count"] + 1)):
        raise RuntimeError(f"{run_directory}: completed chunk count does not match manifest")
    if manifest["attempted"] != manifest["successful"] + manifest["failed"]:
        raise RuntimeError(f"{run_directory}: manifest counts are inconsistent")

    path_frames = []
    span_frames = []
    failure_records = []
    for chunk_number in chunk_numbers:
        paths = _chunk_paths(run_directory, chunk_number)
        if not all(paths[name].is_file() for name in ("paths", "spans", "failures")):
            raise RuntimeError(f"{paths['metadata']}: completed chunk has missing output files")
        summary = json.loads(paths["metadata"].read_text(encoding="utf-8"))
        path_frame = pd.read_parquet(paths["paths"])
        span_frame = pd.read_parquet(paths["spans"])
        chunk_failures = _read_jsonl(paths["failures"])
        if (
            summary["chunk_number"] != chunk_number
            or len(path_frame) != summary["successful"]
            or len(chunk_failures) != summary["failed"]
            or summary["attempted"] != summary["successful"] + summary["failed"]
        ):
            raise RuntimeError(f"{paths['metadata']}: chunk contents do not match its counts")
        path_frames.append(path_frame)
        span_frames.append(span_frame)
        failure_records.extend(chunk_failures)

    paths_frame = pd.concat(path_frames, ignore_index=True) if path_frames else pd.DataFrame()
    spans_frame = pd.concat(span_frames, ignore_index=True) if span_frames else pd.DataFrame()
    if len(paths_frame) != manifest["successful"] or len(failure_records) != manifest["failed"]:
        raise RuntimeError(f"{run_directory}: merged rows do not match manifest counts")
    if manifest["attempted"] != manifest["requested"]:
        raise RuntimeError(
            f"{run_directory}: completed run did not attempt every requested scenario"
        )
    null_counts = {
        "paths": _validate_required_columns(paths_frame, PATH_REQUIRED_COLUMNS, "paths"),
        "spans": _validate_required_columns(spans_frame, SPAN_REQUIRED_COLUMNS, "spans"),
    }
    output_paths = run_directory / "paths.parquet"
    output_spans = run_directory / "spans.parquet"
    _atomic_write_parquet(paths_frame, output_paths)
    _atomic_write_parquet(spans_frame, output_spans)
    _atomic_write_jsonl(run_directory / "failures.jsonl", failure_records)
    return output_paths, output_spans, null_counts


def _manifest_counts(
    identity: dict,
    existing_manifest: dict,
    chunk_summaries: list[dict],
    rejected: int,
    unique_scenario_count: int,
    requested: int,
    chunk_count: int,
    workers: int,
) -> dict:
    failure_reason_counts = Counter()
    for summary in chunk_summaries:
        failure_reason_counts.update(summary["failure_reason_counts"])
    attempted = sum(summary["attempted"] for summary in chunk_summaries)
    successful = sum(summary["successful"] for summary in chunk_summaries)
    failed = sum(summary["failed"] for summary in chunk_summaries)
    return {
        **identity,
        "created_at_utc": existing_manifest.get("created_at_utc", datetime.now(UTC).isoformat()),
        "updated_at_utc": datetime.now(UTC).isoformat(),
        "status": "complete" if len(chunk_summaries) == chunk_count else "running",
        "workers": workers,
        "requested": requested,
        "attempted": attempted,
        "successful": successful,
        "failed": failed,
        "rejected": rejected,
        "duplicate_scenario_ids": requested - unique_scenario_count,
        "unique_scenario_ratio": unique_scenario_count / requested if requested else 1.0,
        "completed_chunks": len(chunk_summaries),
        "chunk_count": chunk_count,
        "elapsed_seconds": sum(summary["elapsed_seconds"] for summary in chunk_summaries),
        "chunk_timings_seconds": [
            {"chunk": summary["chunk_number"], "elapsed_seconds": summary["elapsed_seconds"]}
            for summary in chunk_summaries
        ],
        "failure_reason_counts": dict(sorted(failure_reason_counts.items())),
    }


def generate_run(
    run_id: str,
    runs: int,
    seed: int,
    chunk_size: int,
    workers: int,
    simulation_config: dict,
    output_root: Path,
    force: bool = False,
    runner=None,
    gnpy_version: str | None = None,
) -> dict:
    if runs < 1:
        raise ValueError("runs must be at least 1")
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    if workers < 1:
        raise ValueError("workers must be at least 1")
    output_root.mkdir(parents=True, exist_ok=True)
    run_directory = _run_directory(output_root, run_id)
    if force:
        _reset_run_directory(run_directory)
    run_directory.mkdir(parents=True, exist_ok=True)

    selected = selected_topologies()
    if not selected:
        raise RuntimeError("No accepted Phase 1 topologies found")
    topology_data = []
    topology_hashes = []
    for topology_id, unified_path in selected:
        raw_data = unified_path.read_bytes()
        topology = json.loads(raw_data)
        topology["unified_path"] = str(unified_path)
        topology_data.append(topology)
        topology_hashes.append((topology_id, hashlib.sha256(raw_data).hexdigest()))

    scenarios, rejected = sample_scenarios_with_stats(
        topology_data,
        runs,
        seed,
        simulation_config,
    )
    if len(scenarios) != runs:
        raise RuntimeError(f"sampler returned {len(scenarios)} scenarios for {runs} requested")
    config_hash = _sha256_json(simulation_config)
    topology_hash = _sha256_json(topology_hashes)
    git_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if gnpy_version is None:
        gnpy_version = importlib.metadata.version("gnpy")
    chunk_count = (runs + chunk_size - 1) // chunk_size
    identity = {
        "run_id": run_id,
        "seed": seed,
        "config_hash": config_hash,
        "topology_hash": topology_hash,
        "git_commit": git_commit,
        "gnpy_version": gnpy_version,
        "requested": runs,
        "chunk_size": chunk_size,
        "chunk_count": chunk_count,
    }
    manifest_path = run_directory / "manifest.json"
    existing_manifest = {}
    if manifest_path.exists():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        mismatches = [key for key, value in identity.items() if existing_manifest.get(key) != value]
        if mismatches:
            raise RuntimeError(
                f"{run_directory}: run identity differs in {', '.join(mismatches)}; "
                "choose a new run_id or pass --force to restart"
            )
    elif any(run_directory.iterdir()):
        raise RuntimeError(
            f"{run_directory}: existing files have no manifest; pass --force to restart"
        )

    scenario_ids = [scenario.scenario_id for scenario in scenarios]
    unique_scenario_count = len(set(scenario_ids))
    chunk_summaries = _chunk_summaries(run_directory, chunk_count)
    for summary in chunk_summaries:
        chunk_number = summary["chunk_number"]
        expected_ids = [
            scenario.scenario_id
            for scenario in scenarios[(chunk_number - 1) * chunk_size : chunk_number * chunk_size]
        ]
        if summary["scenario_ids"] != expected_ids:
            raise RuntimeError(
                f"{run_directory}: chunk {chunk_number} scenario IDs do not match this run"
            )
    unexpected_chunks = [
        item.name
        for item in run_directory.iterdir()
        if (match := re.fullmatch(r"chunk_(\d{5})\.json", item.name))
        and int(match.group(1)) > chunk_count
    ]
    if unexpected_chunks:
        raise RuntimeError(
            f"{run_directory}: unexpected chunks for this run: {', '.join(unexpected_chunks)}"
        )

    if (
        existing_manifest.get("status") == "complete"
        and len(chunk_summaries) == chunk_count
        and (run_directory / "paths.parquet").is_file()
        and (run_directory / "spans.parquet").is_file()
        and (run_directory / "failures.jsonl").is_file()
        and "required_column_null_counts" in existing_manifest
    ):
        return existing_manifest

    manifest = _manifest_counts(
        identity,
        existing_manifest,
        chunk_summaries,
        rejected,
        unique_scenario_count,
        runs,
        chunk_count,
        workers,
    )
    _atomic_write_json(manifest_path, manifest)
    existing_manifest = manifest
    _write_aggregate_failures(run_directory, chunk_summaries)
    completed_numbers = {summary["chunk_number"] for summary in chunk_summaries}
    if runner is None:
        from fiber_qot_platform.simulation.phase2 import run_many

        runner = run_many
    for chunk_number in range(1, chunk_count + 1):
        if chunk_number in completed_numbers:
            continue
        start = (chunk_number - 1) * chunk_size
        chunk_scenarios = scenarios[start : start + chunk_size]
        tasks = [scenario.to_run_task() for scenario in chunk_scenarios]
        started = time.perf_counter()
        outcomes = runner(tasks, workers=workers)
        if len(outcomes) != len(chunk_scenarios):
            raise RuntimeError(
                f"chunk {chunk_number}: runner returned {len(outcomes)} outcomes "
                f"for {len(chunk_scenarios)} scenarios"
            )
        rows = []
        span_rows = []
        failures = []
        for scenario, outcome in zip(chunk_scenarios, outcomes, strict=True):
            if outcome["failure"] is not None:
                failure = outcome["failure"]
                failures.append(
                    {
                        "scenario_id": scenario.scenario_id,
                        "topology_id": scenario.topology_id,
                        "source": scenario.source,
                        "destination": scenario.destination,
                        "reason": f"{failure['type']}: {failure['reason']}",
                    }
                )
                continue
            row = dict(outcome["row"])
            span_rows.extend(row.pop("_span_profiles", []))
            rows.append(row)

        paths = _chunk_paths(run_directory, chunk_number)
        paths_frame = pd.DataFrame(rows) if rows else pd.DataFrame(columns=PATH_REQUIRED_COLUMNS)
        spans_frame = (
            pd.DataFrame(span_rows) if span_rows else pd.DataFrame(columns=SPAN_REQUIRED_COLUMNS)
        )
        _atomic_write_parquet(paths_frame, paths["paths"])
        _atomic_write_parquet(spans_frame, paths["spans"])
        _atomic_write_jsonl(paths["failures"], failures)
        failure_reason_counts = dict(Counter(item["reason"] for item in failures))
        elapsed_seconds = time.perf_counter() - started
        summary = {
            "chunk_number": chunk_number,
            "scenario_ids": [scenario.scenario_id for scenario in chunk_scenarios],
            "attempted": len(chunk_scenarios),
            "successful": len(rows),
            "failed": len(failures),
            "elapsed_seconds": elapsed_seconds,
            "failure_reason_counts": failure_reason_counts,
        }
        _atomic_write_json(paths["metadata"], summary)
        chunk_summaries.append(summary)
        chunk_summaries.sort(key=lambda item: item["chunk_number"])
        manifest = _manifest_counts(
            identity,
            existing_manifest,
            chunk_summaries,
            rejected,
            unique_scenario_count,
            runs,
            chunk_count,
            workers,
        )
        _atomic_write_json(manifest_path, manifest)
        _write_aggregate_failures(run_directory, chunk_summaries)

    _, _, null_counts = merge_run_directory(run_directory)
    manifest = _manifest_counts(
        identity,
        existing_manifest,
        chunk_summaries,
        rejected,
        unique_scenario_count,
        runs,
        chunk_count,
        workers,
    )
    manifest["required_column_null_counts"] = null_counts
    _atomic_write_json(manifest_path, manifest)
    return manifest


def main() -> int:
    from fiber_qot_platform.simulation.phase2 import load_mode_config, load_simulation_config

    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=100)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--chunk-size", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--run-id")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    modes = load_mode_config()
    simulation_config = load_simulation_config()
    simulation_config["transceiver"]["mode_parameters"] = modes
    seed = args.seed if args.seed is not None else int(simulation_config["random_seed"])
    run_id = args.run_id or (
        datetime.now(UTC).strftime("run-%Y%m%dT%H%M%SZ") + f"-{uuid4().hex[:8]}"
    )
    manifest = generate_run(
        run_id=run_id,
        runs=args.runs,
        seed=seed,
        chunk_size=args.chunk_size,
        workers=args.workers,
        simulation_config=simulation_config,
        output_root=ROOT / "data" / "generated",
        force=args.force,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
