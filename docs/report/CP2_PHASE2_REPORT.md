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
- Smoke successful: 19 rows.
- Smoke failures: 71.
- Smoke output: `data/generated/phase2_smoke.parquet`.

## Smoke statistics

- Topologies represented: 10.
- Modes represented: 4.
- Mean GSNR: 13.535 dB.
- Minimum GSNR: 5.010 dB.
- Maximum GSNR: 23.022 dB.
- Feasible: 5; infeasible: 14.

All successful rows passed a required-column NaN check.

## Problems

All 71 failures were `IndexError: list index out of range`. The failures occurred in topology-specific
source/destination/routing paths and must be fixed before generation scale. A 100k run would require
parallel execution or a longer uninterrupted run, and no result is extrapolated into this smoke dataset.

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
