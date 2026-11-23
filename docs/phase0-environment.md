# Phase 0 environment notes

## Verified choices

- **Python:** CPython 3.12.3 is available in the sandbox. GNPy 3.0.1 declares Python `>=3.11,<3.13`, so Python 3.12 is within the supported range.
- **GNPy:** Pin `gnpy==3.0.1`. The v3.0 release notes describe breaking changes, require NumPy 2.x, and note that channel numbering and output behavior changed. Do not mix assumptions from older tutorials with this pinned version.
- **CLI example:** Official GNPy docs identify `gnpy-transmission-example` and the package example network `gnpy/example-data/edfa_example_network.json`. The installed CLI and an end-to-end transmission run are verified below.
- **Thresholds:** Load transceiver mode/feasibility settings from the installed GNPy equipment configuration. Do not enter guessed OSNR/GSNR thresholds in project config. Record the exact field names, value, and bandwidth convention once inspected in code.
- **Kaggle:** Kaggle is an optional source, not a prerequisite for GNPy. No Kaggle credential is stored or configured. Search/download work is deferred until needed; credentials must never be committed or printed.

## ARM64 build note

This sandbox is Ubuntu 24.04 on AArch64. PyPI has no Linux AArch64 wheel for `oopt-gnpy-libyang`, a native dependency of GNPy 3.0.1, so pip falls back to a source build. The upstream package documents that this build needs `libyang`, `libyang-cpp`, CMake, and a C++ compiler. Native libraries were built from the submodules pinned by the binding's v0.0.14 release (binding source commit `26a9f5a559c44bf9c07f8917e5b724ec2780db49`): libyang 2.1.152 and libyang-cpp 1.1.0. The resulting `oopt-gnpy-libyang==0.0.14` extension compiled and installed successfully without changing the GNPy version.

## Smoke-test results

Verified on 2026-11-23 in the project `.venv`:

- CPython 3.12.3, `gnpy==3.0.1`, `numpy==2.5.5`, `oopt-gnpy-libyang==0.0.14`, and `torch==2.15.0+cpu`.
- PyTorch reports `torch.version.cuda is None` and `torch.cuda.is_available() is False`.
- `gnpy-transmission-example --help` succeeds. To run the packaged example, provide its network file explicitly (the CLI treats the first positional argument as the topology):

  ```bash
  NETWORK=".venv/lib/python3.12/site-packages/gnpy/example-data/edfa_example_network.json"
  gnpy-transmission-example --show-channels -o /tmp/gnpy-example.json "$NETWORK" Site_A Site_B
  ```

- The example completed successfully for Site_A to Site_B across one 80 km SSMF span with 76 channels at 50 GHz spacing. Final path GSNR was 31.17 dB in the 0.1 nm reference bandwidth; the Site_B GSNR in signal bandwidth was 27.09 dB. These are simulator outputs, not field measurements.
- GNPy emitted a non-fatal warning that the sample equipment file omits `type_variety` for Roadm and therefore uses its default. This is recorded rather than hidden.
- The Phase 0 configuration test passed. The console log and generated JSON/XLSX outputs were kept under `/tmp` for verification and are not project data.

## Official references

- [GNPy installation](https://gnpy.readthedocs.io/en/master/install.html)
- [GNPy introduction and transmission example](https://gnpy.readthedocs.io/en/master/intro.html)
- [GNPy v3.0 release notes](https://gnpy.readthedocs.io/en/master/release-notes.html)
- [GNPy on PyPI](https://pypi.org/project/gnpy/)
- [Official GNPy source repository](https://github.com/Telecominfraproject/oopt-gnpy)
- [GNPy libyang Python binding and source-build requirements](https://github.com/Telecominfraproject/oopt-gnpy-libyang)
- [Binding upstream CI build recipe](https://github.com/Telecominfraproject/oopt-gnpy-libyang/blob/main/.github/workflows/ci.yaml)
- [PyPI wheel inventory for oopt-gnpy-libyang](https://pypi.org/project/oopt-gnpy-libyang/)

## Phase 0 verification checklist

- [x] Create and activate `.venv` using Python 3.12.
- [x] Install the project dependencies and save a fully resolved `requirements.lock`.
- [x] Confirm `gnpy==3.0.1`, NumPy 2.x, and `gnpy-transmission-example --help`.
- [x] Run a real GNPy example and retain its sanitized result summary above.
- [x] Confirm no credentials or local data are tracked in Git; local environments and secrets are ignored.
- [x] Search optional external datasets and record findings without treating Kaggle as required.
