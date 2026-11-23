# Data card - Phase 2 smoke dataset

## Status

Phase 2 full dataset generation was not completed. The benchmark and bounded smoke outputs below are real
GNPy-generated results, not an estimate of a larger dataset.

## Sources

- Internet Topology Zoo GraphML networks from Phase 1.
- SNDlib Germany50, Nobel-Germany, and India35 native XML networks.
- The illustrative synthetic Tunisia network.
- GNPy 3.0.1 equipment and propagation model.

## Benchmark

- 100 benchmark runs: 100 successful, 0 failed.
- Elapsed: 123.899 seconds.
- Average: 1.239 seconds per GNPy run.
- Sequential extrapolation for 100,000 runs: 34.42 hours.

## Smoke dataset

- Requested rows: 100.
- Successful rows: 19.
- Failed simulations: 71.
- Topologies represented: 10.
- GSNR mean/min/max: 13.535 / 5.010 / 23.022 dB.
- Feasible/infeasible under the loaded mode and 2 dB margin: 5 / 14.
- All 19 successful rows have no required-column NaN values.
- `IndexError: list index out of range` accounted for all recorded smoke failures.

The 71 failures require routing robustness fixes before full generation. They are retained in
`data/generated/phase2_smoke.json`; they are not represented as dataset rows.

## Label convention

- `gsnr_db`: mean GNPy signal-bandwidth GSNR.
- `gsnr_db_01nm`: mean GNPy 0.1 nm GSNR.
- `osnr_01nm_db`: mean GNPy 0.1 nm OSNR.
- `gsnr_db_noisy`: `gsnr_db` plus simulated zero-mean Gaussian noise with a 0.35 dB standard deviation.
- `feasible`: `gsnr_db >= required_gsnr_db + design_margin_db`.

The noisy target is simulated measurement uncertainty and is not real measurement noise.
