# fiber-qot-platform

An open-data and simulation-based project for optical Quality of Transmission (QoT) estimation. The planned platform will compare machine-learning estimates of GSNR/OSNR with GNPy simulations and visualize lightpath feasibility. No operator network data or measured QoT data is included.

**Status:** Phase 0 repository scaffold and environment verified on Ubuntu 24.04 ARM64 with CPython 3.12.3. No topology dataset, trained model, measured result, or finished application is claimed yet.

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
```

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

Project source files are intended to use the MIT License. Dataset and library licenses will be recorded separately in [`docs/ATTRIBUTION.md`](docs/ATTRIBUTION.md). No external topology or Kaggle dataset has been added at this stage.
