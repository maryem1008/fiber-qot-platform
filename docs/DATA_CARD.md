# Data card - Phase 2 smoke dataset

## Status

Phase 2 full 100,000-row dataset generation was not completed within the available compute limit. The
benchmark and bounded outputs below are real GNPy-generated results, not estimates of unrun rows.

The feasibility counts in the historical smoke and 1,000-run sections below were computed with the
previous, bandwidth-inconsistent convention and are retained only as historical results. They are not
valid labels under the corrected convention, and the old generated files have not been regenerated.
The redesigned sampler has not yet been used to generate a dataset; the pilot is still pending.

## Sampling design

The current sampler distributes requested rows evenly across topologies and uses independent seeded draws for
connected source/destination pairs, among up to three shortest simple routes, GNPy modes, compatible channel
spacing, legal channel counts within the configured frequency band, continuous launch power, physical-parameter
offsets, and per-row synthetic noise standard deviation. The selected ROADMs are passed to GNPy as strict route
constraints. This describes the sampler implementation; it is not a claim that the pilot or full dataset has run.

Baud rate comes from the selected installed GNPy mode. The GNPy network currently models SSMF only; fiber type
is therefore not sampled. The per-scenario NF offset is applied to GNPy's variable-gain NF model; the span-loss
and extra-connector offsets are combined and split evenly across each fiber span's input and output connector
attenuations. These are synthetic perturbations applied consistently to a run's network.
EDFA gain targets and varieties are not fixed: GNPy designs loss-compensating gain from each span's modeled
loss and selects an equipment variety from its installed library based on the gain and power targets.

The configured launch-power interval is [-3, 3] dBm and values are rounded to 0.01 dB, giving at most 601
distinct rounded values. The test therefore checks for at least 550 distinct values, rather than the impossible
requirement of more than 1,000.

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
- Legacy feasible/infeasible under the old convention: 18 / 72.
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
- Legacy feasible/infeasible under the old convention: 141 / 849.
- The 990 rows have no NaN values in required path columns.
- The corresponding per-span table is written separately.

## Label convention

- `gsnr_db`: mean GNPy signal-bandwidth GSNR.
- `gsnr_db_01nm`: mean GNPy GSNR in the 0.1 nm reference bandwidth; this is the primary regression target.
- `osnr_01nm_db`: mean GNPy 0.1 nm OSNR.
- `required_osnr_01nm_db`: the selected transceiver mode's OSNR requirement, referenced to 0.1 nm.
- `margin_db`: `gsnr_db_01nm - required_osnr_01nm_db`.
- `design_margin_db`: required design margin loaded from `configs/simulation.yaml`.
- Path structure comes from the simulated GNPy path: `total_length_km` sums its Fiber lengths, `hops` is the
  number of transitions between traversed ROADMs, `n_spans` counts traversed Fiber elements, and `n_amps`
  counts traversed Edfa elements. `n_roadms` counts actual GNPy Roadm elements, including the source and
  destination ROADMs.
- `feasible`: `margin_db >= design_margin_db`.
- `noise_std_db`: per-scenario synthetic noise standard deviation sampled from configuration.
- `gsnr_db_noisy`: `gsnr_db` plus synthetic zero-mean Gaussian noise using that row's `noise_std_db`.

The prior implementation compared signal-bandwidth `gsnr_db` directly against a mode OSNR threshold
defined in 0.1 nm. The corrected convention uses `gsnr_db_01nm`. The noisy target is simulated
measurement uncertainty and is not real measurement noise.

GNPy propagation metrics are simulator outputs. Feasibility margin and topology/path statistics are derived
from those outputs and the selected scenario. Added amplifier-NF, span-loss, and connector-loss offsets and
the noisy target are synthetic scenario variations, not field measurements.
