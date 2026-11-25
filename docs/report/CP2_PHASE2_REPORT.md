# CP2 - Phase 2 GNPy dataset checkpoint

## Status

The benchmark and bounded smoke generation are complete, but the full target dataset is not complete.
This is an honest compute and route-robustness checkpoint, not a claim of 100,000 rows.

## What ran

- GNPy 3.0.1 benchmark: 100/100 successful.
- Benchmark elapsed: 123.899 seconds.
- Average: 1.239 seconds/run.
- Sequential 100k extrapolation: 34.42 hours.
- Smoke generation requested: 100 rows.
- Smoke successful: 90 rows.
- Smoke failures: 0.
- Bounded 1,000-run pass: 990 successful, 0 failed.
- Smoke output: `data/generated/phase2_smoke.parquet`.

## Smoke statistics

- Topologies represented: 18.
- Modes represented: 4.
- Mean GSNR: 12.384 dB.
- Minimum GSNR: 4.510 dB.
- Maximum GSNR: 23.022 dB.
- Historical feasible/infeasible: 18 / 72 under the previous bandwidth-inconsistent convention; these
  counts are not valid under the corrected 0.1 nm convention and have not yet been recomputed.

All successful rows passed a required-column NaN check.

## Problems

The prior smoke failures were `IndexError: list index out of range` caused by incomplete reverse GNPy
routing. The converter now creates separate forward and reverse Fiber/EDFA elements and the rerun
produced 90 rows with 0 failures. A 100k run would require parallel execution or a longer uninterrupted
run, and no result is extrapolated into this smoke dataset.

## Deliverables

- `configs/simulation.yaml`
- `scripts/phase2_benchmark.py`
- `scripts/phase2_generate.py`
- `src/fiber_qot_platform/simulation/phase2.py`
- `data/generated/phase2_smoke.parquet`
- `data/generated/phase2_smoke.json`
- `docs/DATA_CARD.md`

## Next step

Stop at CP2. Reply `go` only after deciding to authorize continued routing fixes and Phase 2 generation.
