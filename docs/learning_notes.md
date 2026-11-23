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
