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

The Zoo and SNDlib graphs are topology abstractions, not verified inventories of current deployed
fiber routes. The Tunisia graph is synthetic and illustrative: its link lengths use a 1.25 multiplier
on great-circle city distances. That factor is a modeling assumption, not measured cable length.

## What the values represent

- **GNPy simulation outputs:** propagated GSNR/OSNR, ASE and NLI noise powers, fiber loss, amplifier
  gain/noise figure, and total WDM power. These are outputs of the configured GNPy physical model,
  not field measurements.
- **Derived values:** feasibility margin and boolean, NLI SNR from same-bandwidth inverse-SNR
  subtraction, and path/span structural summaries computed from the simulated GNPy path.
- **Synthetic additions:** sampled amplifier-NF, span-loss and connector-loss offsets; the per-row
  Gaussian noise standard deviation and noisy GSNR target; and span geometry interpolated along a
  great-circle line. Geometry is tagged `interpolated_great_circle` and is not a surveyed fiber route.

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
- `snr_nli_db`: derived signal-bandwidth NLI SNR using `1/GSNR = 1/OSNR_ASE + 1/SNR_NLI`.
- `snr_nli_01nm_db`: the same derived NLI SNR equation using only the 0.1 nm values.
- `snr_nli_*_available` and `snr_nli_*_invalid`: distinguish a valid derived NLI value from an unavailable
  input or a non-positive inverse-SNR difference; invalid NLI values remain null, not clipped.
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

The run manifest reports per-column null counts for both merged tables. NLI values are nullable by design when
their inputs are unavailable or the inverse-SNR subtraction is non-positive; availability and invalidity flags
explain those cases.

## Per-span table schema

Each spans-table row represents one traversed GNPy Fiber and its following Edfa. Cumulative metrics are sampled
from GNPy's evolving `SpectralInformation` after that amplifier. The final row's cumulative GSNR and ASE OSNR
are taken from the final GNPy transceiver state, so they agree with the corresponding path-row values. Noise
powers are sums across the propagated channels, in watts; they are GNPy spectral-information values and do not
include separate transmitter or ROADM OSNR penalties. Power values are total WDM power across channels in dBm,
not per-channel launch power. The `_available` fields distinguish an unavailable value from a measured zero or
other numeric value. NLI SNR is derived from cumulative GSNR and ASE OSNR in the same bandwidth.

| Column | Meaning / provenance |
| --- | --- |
| `path_id` | Identifier of the associated path row. |
| `span_index` | Zero-based position of this Fiber span in the simulated path. |
| `link_span_index` | Zero-based span position in the corresponding topology link; remains the link's original index when traversed in reverse. |
| `length_km`, `length_km_available` | GNPy Fiber length in km and availability flag. |
| `loss_db`, `loss_db_available` | GNPy Fiber loss in dB and availability flag. |
| `geometry` | Two `{latitude, longitude}` points delimiting the span, interpolated by fractional span position between the topology link endpoints. |
| `geometry_source` | Always `interpolated_great_circle`; this is synthetic geometry, not the physical fiber route. |
| `geometry_available` | Whether the interpolated points were produced. |
| `power_in_dbm`, `power_in_dbm_available` | Total WDM power immediately before the Fiber. |
| `power_after_fiber_dbm`, `power_after_fiber_dbm_available` | Total WDM power immediately after the Fiber and before its Edfa. |
| `power_out_dbm`, `power_out_dbm_available` | Total WDM power immediately after the following Edfa. |
| `amplifier_gain_db`, `amplifier_gain_db_available` | Mean GNPy effective gain of the following Edfa. |
| `amplifier_nf_db`, `amplifier_nf_db_available` | Mean GNPy noise figure of the following Edfa. |
| `cum_ase_noise_w`, `cum_ase_noise_w_available` | Sum of GNPy ASE noise powers over channels after the Edfa. |
| `cum_nli_noise_w`, `cum_nli_noise_w_available` | Sum of GNPy NLI noise powers over channels after the Edfa. |
| `cum_gsnr_db`, `cum_gsnr_db_available` | Cumulative GNPy GSNR in signal bandwidth after the Edfa, including transmitter and traversed ROADM OSNR penalties. |
| `cum_gsnr_db_01nm`, `cum_gsnr_db_01nm_available` | Cumulative GNPy GSNR referenced to 0.1 nm after the Edfa; the final span equals the path-level `gsnr_db_01nm`. |
| `cum_osnr_ase_db`, `cum_osnr_ase_db_available` | Cumulative ASE OSNR in signal bandwidth after the Edfa, with transmitter and traversed ROADM OSNR penalties. |
| `cum_osnr_ase_db_01nm`, `cum_osnr_ase_db_01nm_available` | Cumulative ASE OSNR referenced to 0.1 nm after the Edfa; the final span equals the path-level `osnr_01nm_db`. |
| `cum_snr_nli_db`, `cum_snr_nli_db_available`, `cum_snr_nli_db_invalid` | NLI SNR derived in signal bandwidth from `1/GSNR = 1/OSNR_ASE + 1/SNR_NLI`. Null and unavailable if the inputs are unavailable; null and invalid if their inverse-SNR difference is non-positive or numerically invalid. |
| `cum_snr_nli_db_01nm`, `cum_snr_nli_db_01nm_available`, `cum_snr_nli_db_01nm_invalid` | Same NLI derivation, using only the 0.1 nm bandwidth values. |
| `gsnr_drop_db`, `gsnr_drop_db_available` | Previous cumulative 0.1 nm GSNR minus this span's cumulative 0.1 nm GSNR. For the first span, the reference is the GNPy source transceiver's transmitted OSNR (`snr_01nm`) before the network. A negative value is retained if observed. |

These are the current in-memory columns emitted for each span; the generator's parquet output preserves these
columns without substituting estimated or placeholder values for unavailable simulator metrics.
