
# fiber-qot-platform

A topology-based and simulation-based project for optical Quality of Transmission (QoT) estimation. The planned platform will compare machine-learning estimates of GSNR/OSNR with GNPy simulations and visualize lightpath feasibility. No operator network data or measured QoT data is included.

**Status:** Phase 1 topology conversion is complete. Phase 2 dataset-quality work WI-1 through WI-10 is
implemented on `fix/phase2-dataset-quality`; the 2,000-scenario pilot completed with a no-go recommendation
for scaling pending controlled physical diagnostics. The 100,000-row generation and Phase 3 have not started.
No trained model, measured QoT result, or finished application is claimed.
See [`docs/CONTINUATION.md`](docs/CONTINUATION.md) for the handoff.

## Environment

The project targets CPython 3.12 and pins GNPy 3.0.1. GNPy 3.0.1 supports Python 3.11 and 3.12 and requires NumPy 2.x. See [`docs/phase0-environment.md`](docs/phase0-environment.md) for the verified references.

Create and activate the environment from the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

On platforms with a compatible `oopt-gnpy-libyang` wheel, install the project and CPU PyTorch with:

```bash
python -m pip install -e '.[dev]' --extra-index-url https://download.pytorch.org/whl/cpu
```

On Linux ARM64, use `bash scripts/install_gnpy_arm64.sh`. That helper builds the native YANG libraries from the source revisions compatible with GNPy 3.0.1, then installs the project. The upstream binding currently has no Linux ARM64 wheel, so pip otherwise attempts an incompatible generic source build.

[`requirements.lock`](requirements.lock) records the resolved environment tested with CPython 3.12.3 on Ubuntu 24.04 ARM64. Platform-specific native dependencies still need to be installed as described above. PyTorch was verified as CPU-only in this environment.

## Useful commands

```bash
make env-check     # report Python and GNPy versions
make gnpy-help     # verify the GNPy CLI entry point
make test          # run tests
make phase1        # parse and convert Phase 1 topology sources
```

### Phase 2 scenario sampling

The Phase 2 generator samples exactly the requested number of scenarios, splits them evenly across converted
topologies, and uses a fixed seed from `configs/simulation.yaml` unless `--seed` is supplied. Modes, baud rates,
spacing limits, channel counts, launch powers, route ranks, and synthetic noise levels are sampled independently
from their configured domains. Routes are constrained through their selected intermediate ROADMs in GNPy.

Run a bounded generation with `python scripts/phase2_generate.py --runs 100 --workers 2 --run-id trial-01`.
Outputs are isolated under `data/generated/<run-id>/`, with numbered path/span Parquet chunks, failure logs,
and a manifest. Re-run the same command and run ID to resume completed chunks; completed chunks are skipped.
An existing run ID with different seed/configuration is rejected. Use `--force` only to restart that run ID
from scratch. The generator also writes merged `paths.parquet` and `spans.parquet`; to rebuild them manually,
run `python scripts/phase2_merge.py --run-id trial-01`. `make phase2-smoke` uses the run ID `smoke`.
`make phase2-pilot` runs exactly 2,000 scenarios with two workers by default; override the worker count with
`PHASE2_WORKERS`. The recorded pilot is in [`docs/report/CP2B_PILOT_REPORT.md`](docs/report/CP2B_PILOT_REPORT.md).

The `--runs` option defaults to 100; do not use the 100,000-row target until the project pilot has passed its
go/no-go checkpoint.

## Project structure

- `configs/`: versioned project and simulation configuration.
- `data/`: topology inputs and generated outputs; large or licensed data is not committed by default.
- `src/`: topology, simulation, features, models, evaluation, and API code.
- `frontend/`: planned React application.
- `tests/`: automated tests.
- `docs/`: setup notes, learning notes, attribution, and later data/model documentation.

## Scientific honesty

GNPy output is a simulated physical reference, not a field measurement. The Tunisia demo topology, if built, will be explicitly labeled illustrative and synthetic. ML estimates and simulator outputs will remain separately identified. All performance claims must be backed by reproducible runs.

## License and data

Project source files are intended to use the MIT License. Dataset and library terms are tracked separately in
[`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md); the terms for the checked-in Zoo and SNDlib topology inputs are
not fully verified, so no blanket redistribution permission is claimed.
