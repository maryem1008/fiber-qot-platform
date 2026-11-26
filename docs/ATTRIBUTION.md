# Attribution

This file records third-party software and data sources used by the project. Verify the precise license and citation for each topology before redistributing it.

## Software used in Phase 0

- **GNPy 3.0.1** — Telecom Infra Project, OOPT/PSE group. License reported on PyPI as BSD-3-Clause. Official project: https://github.com/Telecominfraproject/oopt-gnpy. Documentation: https://gnpy.readthedocs.io/.
- **oopt-gnpy-libyang** — Telecom Infra Project Python bindings for YANG data. BSD-3-Clause. Source: https://github.com/Telecominfraproject/oopt-gnpy-libyang. GNPy requires this dependency for its YANG input/output functionality.
- **libyang** — CESNET YANG parser/toolkit, BSD-3-Clause. Source: https://github.com/CESNET/libyang.
- **libyang-cpp** — CESNET C++ bindings, BSD-3-Clause. Source: https://github.com/CESNET/libyang-cpp.
- **Python and scientific Python packages** — resolved package versions for the verified Phase 0 environment are recorded in `requirements.lock`. Package-specific license inventory will be checked as dependencies are used; dependencies are not vendored into this repository.

## Data

The repository includes Phase 1 topology inputs and derived topology files. It contains no operator
measurement data. Candidate external QoT dataset search and access notes are recorded in
[`external_data_search.md`](external_data_search.md); no candidate dataset from that search was downloaded.

## Phase 1 topology data and rights status

- **Internet Topology Zoo**: Project records identify the GraphML inputs as obtained from the
  `mroughan/InternetTopologyZoo` GitHub repository. The files retain topology metadata, including
  network-source and provenance fields where supplied. A prior project note reported that Fishshare
  metadata presents the collection as CC BY 4.0, but that claim has not been independently verified
  against the current source repository or checked for applicability to each included topology.
  Accordingly, this file does not make a blanket license or redistribution-rights claim. Preserve
  original metadata and attribution, identify conversion changes, and verify applicable terms before
  redistributing source or derived topology data.
- **SNDlib**: Germany50, Nobel-Germany, and India35 are present as native-format XML with geographic
  coordinates and the SNDlib XML namespace. The checked-in files and Phase 1 manifest do not record
  a per-instance source URL, citation, or license; the applicable primary-source terms have not been
  verified. These files are retained as research inputs only. No license or redistribution permission
  is asserted; verify terms and required citation with SNDlib before redistributing them or derivatives.
- **Tunisia demonstration**: explicitly illustrative and synthetic. City coordinates are geographic
  anchors for a modeled ring-and-mesh; no relationship to a real operator network is claimed.

The topology graphs and modeled link geometry are abstractions, not current physical-network inventories.
The Phase 1 manifest records source filenames and topology counts but is not a license registry.

## Project code

Project source code is intended to be licensed under MIT. This does not change the licenses of third-party software or datasets.
