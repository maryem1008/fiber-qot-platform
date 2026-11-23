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

### Interview questions

1. **Why split sources into a unified schema?** It separates source parsing from GNPy conversion and downstream ML.
2. **Why reject missing coordinates?** A missing coordinate can silently produce invalid distances or paths.
3. **Why is the Tunisia network not operator data?** It is a project demonstration assembled from public city
   coordinates and a modeled route factor.
