# Data card - Phase 2 smoke dataset

## Status

Phase 2 full 100,000-row dataset generation was not completed within the available compute limit. The
benchmark and bounded outputs below are real GNPy-generated results, not estimates of unrun rows.

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
- Successful rows: 90.
- Failed simulations: 0.
- Topologies represented: 18.
- GSNR mean/min/max: 12.384 / 4.510 / 23.022 dB.
- Feasible/infeasible under the loaded mode and 2 dB margin: 18 / 72.
- All 90 successful rows have no required-column NaN values.

The prior 19/71 routing issue was fixed by generating separate forward and reverse Fiber/EDFA
elements in each GNPy link. The rerun retained all 90 attempted rows after this correction.

## Bounded 1,000-run dataset

- Requested rows: 1,000.
- Successful rows: 990.
- Failed simulations: 0.
- Topologies represented: 18.
- Modes represented: 4.
- GSNR mean/min/max: 12.489 / 2.822 / 24.401 dB.
- Feasible/infeasible under the loaded mode and 2 dB margin: 141 / 849.
- The 990 rows have no NaN values in required path columns.
- The corresponding per-span table is written separately.

## Label convention

- `gsnr_db`: mean GNPy signal-bandwidth GSNR.
- `gsnr_db_01nm`: mean GNPy 0.1 nm GSNR.
- `osnr_01nm_db`: mean GNPy 0.1 nm OSNR.
- `gsnr_db_noisy`: `gsnr_db` plus simulated zero-mean Gaussian noise with a 0.35 dB standard deviation.
- `feasible`: `gsnr_db >= required_gsnr_db + design_margin_db`.

The noisy target is simulated measurement uncertainty and is not real measurement noise.
