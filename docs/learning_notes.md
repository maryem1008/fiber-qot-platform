# Learning notes

## Phase 0 — Environment and simulator version

GNPy is the optical-network simulator that will generate reference QoT labels for the project. The selected release is 3.0.1, and the environment uses Python 3.12 because that version is supported by the pinned GNPy release. Version pinning matters because changes in GNPy can affect propagation, spectrum handling, and exported results. The official v3.0 release requires NumPy 2.x, which is included in the environment constraints.

The project will read transceiver modes and feasibility requirements from the installed GNPy equipment configuration. Thresholds will not be copied from memory. OSNR reporting conventions and GSNR interpretation will be documented from the actual installed version and simulation output before model labels are defined.

### Interview questions

1. **Why pin GNPy and Python?** Reproducibility: simulator versions and dependencies can change both API behavior and numerical outputs, so the same environment should reproduce the labels.
2. **Why is GNPy output not real measurement data?** GNPy computes results from a configured physical model and assumptions; it does not observe a deployed operator link.
3. **Why load thresholds from configuration instead of hard-coding them?** Mode requirements and field semantics can vary by GNPy version and equipment setup, so their exact source and bandwidth convention must be traceable.

## Phase 0 smoke-test observation

The packaged GNPy EDFA example ran successfully from Site_A to Site_B over an 80 km SSMF span with 76 channels spaced at 50 GHz. The reported end-of-line GSNR was 31.17 dB in the 0.1 nm reference bandwidth and 27.09 dB in signal bandwidth. These values are simulation outputs, not measurements. The sample equipment file also emits a non-fatal warning because its Roadm entry omits `type_variety`; the simulator uses its documented default.

## Phase 1 - Topology conversion

Zoo GraphML and SNDlib XML are converted to a common project JSON and to GNPy network JSON. Distances use
great-circle coordinates and configurable span splitting of at most 80 km. The Tunisia network uses real city
coordinates with a route factor of 1.25, but remains explicitly illustrative and synthetic.

GNPy 3.0.1 equipment configuration is the source for transceiver modes and OSNR requirements. The `vendorA_trx-type1`
modes require 11 dB and 15 dB OSNR, while `Voyager` modes require 12 dB, 18 dB, 21 dB, or 16 dB OSNR. These are
mode requirements loaded from configuration, not guessed GSNR thresholds.

GNPy OSNR is reported relative to 0.1 nm. GSNR combines ASE and nonlinear interference and can be reported in 0.1
nm or signal bandwidth; the project documents this distinction in later labels.

### Phase 2 — Feasibility bandwidth evidence (GNPy 3.0.1)

The installed `gnpy/topology/request.py` assigns each equipment mode's `OSNR` to
`required_osnr_db_01nm` and calculates the receiver margin from `snr_01nm` (with penalties and system margin).
`gnpy/core/elements.py` recalculates both signal-bandwidth and 0.1 nm values; its `update_snr()` uses 12.5 GHz
for 0.1 nm values. `gnpy/core/info.py` defines `opt_gsnr_db = gsnr_db - 10*log10(12.5e9 / baud_rate)`.

This was checked against an actual GNPy 3.0.1 Tunisia Bizerte–Sfax simulation at 32 GBd: signal-bandwidth GSNR
was 18.4516927553 dB and 0.1 nm GSNR was 22.5340924085 dB. Their 4.0823996531 dB difference matches
`10*log10(32e9 / 12.5e9)` (4.0823996531 dB). Therefore, comparing the signal-bandwidth GSNR directly with a
mode's equipment `OSNR` threshold mixes bandwidth conventions. The dataset feasibility margin must instead be
computed from `gsnr_db_01nm - required_osnr_01nm_db`, with the configured design margin applied to that result.

### Phase 2 — GNPy loading and profiling evidence

The current Makefile defaults to `.venv/Scripts/python.exe`, and the current equipment path embeds the Windows
`.venv/Lib/site-packages` layout. In this environment `gnpy.__file__` resolves to the installed package, whose
directory contains `example-data/eqpt_config.json`; package-relative resolution avoids assuming an OS-specific
virtual-environment layout.

GNPy 3.0.1 `load_network()` reads and converts the network JSON on every call. `network_from_json()` mutates the
input element dictionaries (including popping `type` and `type_variety`), while `designed_network()` inserts and
designs elements in its graph. Any cached parsed network template must therefore be copied before constructing
and designing each run's network.

A `cProfile` run of one Tunisia Bizerte–Sfax scenario on Windows, CPython 3.12.10, GNPy 3.0.1 took 1.050 seconds
including profiler overhead. `designed_network()` accumulated 0.629 seconds; GNPy `design_network()` /
`build_network()` accumulated 0.615 seconds, with `set_egress_amplifier()` accounting for 0.576 seconds.
This is a single profiled run, not a general performance estimate.

### Phase 2 — Sampler and route constraints evidence

Replaying the previous sampler's formulas for 5,555 indices produced 80 unique combinations per topology and 8
distinct launch-power values. The `candidate_pairs(..., limit=40)` implementation caps the selected 18-topology
set at 720 candidate pairs. These are counts from the old deterministic formulas, not GNPy run results.

GNPy 3.0.1 `request.py::compute_constrained_path()` reads ordered intermediate UIDs from `PathRequest.nodes_list`;
its route examples construct `nodes_list` from the requested ROADMs followed by the destination transceiver and set
each corresponding `loose_list` entry to `STRICT`. The Phase 2 request can therefore constrain all intermediate
ROADMs in the sampled route and verify the resulting route sequence.

The configured launch-power interval is [-3, 3] dBm. Rounded to 0.01 dB, it contains only 601 possible values,
so a requirement for more than 1,000 distinct rounded powers in 5,000 samples is mathematically impossible. The
owner approved preserving the configured interval and using an acceptance threshold of at least 550 distinct
launch powers instead.

The installed `std_medium_gain` uses a GNPy `Model_vg` namedtuple with `nf1` and `nf2`; the GNPy EDFA NF
calculation combines those terms in linear power before converting back to dB. A common dB shift to both terms
therefore applies a common NF offset for this model. GNPy Fiber span loss includes `con_in`, `con_out`, and
`att_in`; the run-level span and connector offsets will be applied to non-negative input/output connector
attenuations. These are configured simulation perturbations, not measured properties.

### Phase 1 — Span sizing and EDFA gain evidence (GNPy 3.0.1)

Before changing the Phase 1 converter, calling the existing `split_link()` with 100 km and 85 km reproduced
uneven spans of `[80, 20]` km and `[80, 5]` km. In the installed GNPy 3.0.1 source,
`gnpy/core/parameters.py::EdfaOperational.default_values` sets an omitted `gain_target` to `None`.
`gnpy/core/network.py::compute_gain_power_and_tilt_target()` then computes the target gain from the preceding
span loss (plus the configured power adjustments) when `effective_gain` is unset. `build_network()` records
that computed target as the amplifier's `effective_gain`. The Phase 1 converter can therefore omit a fixed
gain target and let GNPy design loss-compensating gain per span.

The first regeneration also exposed zero-kilometre links in the existing Aarnet and Heanet inputs: rejecting
those lengths would have removed previously accepted topologies. `split_link()` therefore preserves a zero-length
link as one zero-length span, while still rejecting negative lengths. Whether these source edges propagate in GNPy
is checked separately by the post-regeneration smoke runs.

The first post-regeneration run still emitted 1,152 low-gain warnings across the 18 accepted topology designs,
up from 1,114 before the change. All were for the imposed `std_medium_gain` variety, whose equipment entry has a
15 dB minimum gain, while GNPy computed lower targets from the short spans. GNPy 3.0.1 `build_network()` calls
`select_edfa()` when `type_variety` is empty; that routine filters available equipment against the computed gain
and power targets and chooses the acceptable amplifier with the best noise figure. The converter therefore leaves
the variety unset as well as the gain target; the post-change warning comparison tests whether this equipment-
library selection resolves the mismatch.

The comparison ran one 1-channel, 50 GHz, 0 dBm Voyager mode 1 request per accepted topology, using the
lexically first and last node IDs as endpoints. A Python logging handler counted `WARNING` records from `gnpy`
loggers during each GNPy run. The three columns distinguish the checked-in fixed-target baseline, the intermediate
equal-span/automatic-gain design with `std_medium_gain` still imposed, and the final design with both gain and
variety selected by GNPy:

| Topology | Before | Intermediate | After |
| --- | ---: | ---: | ---: |
| sndlib_germany50 | 128 | 210 | 0 |
| sndlib_india35 | 116 | 44 | 0 |
| sndlib_nobel-germany | 34 | 56 | 0 |
| tunisia | 14 | 28 | 0 |
| zoo_aarnet | 44 | 18 | 0 |
| zoo_agis | 42 | 32 | 0 |
| zoo_attmpls | 86 | 72 | 0 |
| zoo_bbnplanet | 42 | 40 | 0 |
| zoo_bellcanada | 108 | 150 | 0 |
| zoo_bics | 72 | 106 | 0 |
| zoo_crlnetworkservices | 48 | 44 | 0 |
| zoo_darkstrand | 46 | 32 | 0 |
| zoo_elibackbone | 46 | 20 | 0 |
| zoo_geant2009 | 84 | 66 | 0 |
| zoo_goodnet | 46 | 26 | 0 |
| zoo_palmetto | 114 | 150 | 0 |
| zoo_sago | 16 | 26 | 0 |
| zoo_spiralight | 28 | 32 | 0 |
| **Total** | **1,114** | **1,152** | **0** |

The first post-change attempt increased warnings rather than reducing them because it retained the medium-gain
amplifier's 15 dB minimum. Allowing GNPy to select amplifier varieties eliminated those per-design gain warnings
in the measured run. The packaged Roadm default warning is emitted separately at equipment load and is not
included in these per-topology design counts.

### Phase 2 — Path-feature consistency evidence

The current implementation calculates total path length from the unified NetworkX graph but takes span lengths
from the GNPy-propagated Fiber elements. On a real GNPy Tunisia Bizerte–Sfax route-rank-3 run, both calculations
returned 973.733 km, and the intended and simulated route sequences matched. This sample did not reproduce a
length discrepancy, but the code used separate path representations, so other topologies/routes could disagree.
The same run reported seven ROADMs for a seven-node route; the source and destination are included in that count.
Path features are computed from the actual simulated GNPy elements, with `n_roadms` explicitly defined as
the number of traversed Roadm elements including endpoints.

### Phase 2 — Per-span GNPy output evidence (GNPy 3.0.1)

Inspection of installed `gnpy/tools/worker_utils.py::transmission_simulation()` confirms its return tuple is
`(path, propagations, powers_dbm, infos)`: `propagations` is a list of complete propagated path copies, one per
power-sweep iteration, while `powers_dbm` is the sweep input list and `infos` is the final
`SpectralInformation`. It is not a per-element power table.

A real 2-channel Tunisia Bizerte–Sfax route-rank-3 run was inspected after propagation. Fiber elements expose
`loss`, `pch_out_dbm`, and `pch_out_db`; Edfa elements expose `pin_db`, `pout_db`, `pch_out_dbm`,
`effective_gain`, and `nf`; ROADMs expose `pch_out_dbm` and `loss_pch_db`. None of those three classes exposes
per-element `snr`, `snr_01nm`, `osnr_ase`, or `osnr_ase_01nm`. The returned `SpectralInformation` does expose
per-channel `ase`, `nli`, `snr_lin_db`, `opt_snr_lin_db`, `gsnr_db`, `opt_gsnr_db`, `snr_nli_db`, and
`opt_snr_nli_db`. In that run, the means were 17.3869 dB OSNR ASE (signal bandwidth), 21.4693 dB OSNR ASE
(0.1 nm), 16.2667 dB GSNR (signal bandwidth), and 20.3491 dB GSNR (0.1 nm). Intermediate cumulative SNR
therefore has to be sampled from GNPy's evolving spectral information during propagation; it cannot honestly be
read from a Fiber, Edfa, or Roadm attribute after the run. Total ASE and NLI powers can be obtained from the
spectral information's real `ase` and `nli` arrays.

The span tracer follows GNPy's `request.propagate()` order: emitter, frequency filtering, each element (collecting
ROADM OSNR penalties), receiver, then the transceiver's existing SNR update. In a real 12-channel, -1 dBm,
Bizerte–Sfax route-rank-1 run, it produced five Fiber/Edfa span rows; the final span's 0.1 nm GSNR was
23.1693537699 dB, matching the path result. On the first span, total WDM power changed from 1.6388 dBm after
the Fiber to 18.8330 dBm after its Edfa. The final cumulative GSNR drop was 0.7232 dB. Focused real-GNPy
checks across 20 scenarios also passed for last-span/path GSNR agreement, non-increasing cumulative 0.1 nm GSNR,
non-zero GSNR drops, and amplifier output power above post-Fiber power. For the same route/scenario, the custom
tracer's path-level signal-band GSNR, 0.1 nm GSNR, and 0.1 nm ASE OSNR matched the installed GNPy
`transmission_simulation()` outputs exactly (0.0 dB difference for each).

### Phase 2 — Chunk/resume behavior evidence

Source inspection of `scripts/phase2_generate.py` confirms that it parses `--chunk-size` but sends the complete
scenario list to one `run_many()` call, then writes fixed `phase2_smoke.*` filenames without a run manifest,
atomic replacement, or collision check. The existing legacy smoke outputs are ignored by Git; the new
run-directory implementation will leave them untouched.

After implementation, the generator ran one real scenario with `--chunk-size 1`: 1 requested, 1 attempted,
1 successful, 0 failed, 0 rejected, and 0 duplicate IDs. It wrote one chunk and a complete manifest; the merged
tables contained 1 path row and 6 span rows. The manual merge command also completed and reproduced those row
counts. The 600-scenario interruption/resume test uses the real deterministic sampler with a stubbed simulation
runner; it verifies six 100-scenario chunks, skips the first two on resume, and compares resumed versus
uninterrupted path/span Parquet rows and failure logs.

### Phase 2 — Path NLI-label evidence

The GNPy 3.0.1 source shows `Transceiver._calc_snr()` copies `SpectralInformation.snr_nli_db` to
`raw_osnr_nli`, while `update_snr()` applies transmitter/ROADM penalties to ASE OSNR and GSNR but does not update
that raw NLI-only value. In a real 12-channel, -1 dBm Bizerte–Sfax run, `transceiver.osnr_nli` was present:
the existing path field reported 28.1846046799 dB, while deriving signal-band NLI SNR from the path GSNR and
ASE OSNR gave 28.1713447518 dB. The prompt's concern that the attribute may be empty was not reproduced in
this case; it is nevertheless the wrong value to label as path-level NLI SNR because it excludes the final
transceiver penalty convention. Also, `phase2_generate.py` currently has no required-column or null-count
validation. WI-8 uses the same-bandwidth equation for both path NLI columns, preserves invalid results as
null with explicit flags, and report null counts in the run manifest.

The post-change one-row GNPy generator check emitted 30.8919 dB signal-band `snr_nli_db` and 34.9743 dB
`snr_nli_01nm_db`; both availability flags were true. Its manifest reported zero nulls for every column in the
one path row and six span rows, and the standalone merge/validation command succeeded.

### Phase 2 — CI/test selection evidence

The WI-9 local non-GNPy selection (`pytest -m "not gnpy"`) passed 9 tests and deselected 12 marked tests.
The selection covers pure topology/sampler tests, generator resume logic with a stubbed simulation runner, and
the source portability scan; the workflow is manual-only with no push or pull-request trigger.

### Interview questions

1. **Why split sources into a unified schema?** It separates source parsing from GNPy conversion and downstream ML.
2. **Why reject missing coordinates?** A missing coordinate can silently produce invalid distances or paths.
3. **Why is the Tunisia network not operator data?** It is a project demonstration assembled from public city
   coordinates and a modeled route factor.
