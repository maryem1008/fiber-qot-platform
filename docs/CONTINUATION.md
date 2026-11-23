# Continuation checkpoint

Updated: 2026-11-23

## Current state

- Project: `fiber-qot-platform`; GitHub remote: `https://github.com/maryem1008/fiber-qot-platform`.
- The owner changed the repository visibility to private. It was verified through GitHub's API as `private=true` on 2026-11-23.
- Primary branch: `main`. Phase 0 baseline commit: `2ba8622206d279bc7c8a6dda504c670f82ee7d10` (`Initialize fiber QoT platform Phase 0 scaffold`). Always push authorized project commits to `origin/main`.
- Phase 0 is complete. The current environment is Ubuntu 24.04 AArch64, CPython 3.12.3, GNPy 3.0.1, NumPy 2.5.5, `oopt-gnpy-libyang==0.0.14`, and CPU-only `torch==2.15.0+cpu`. Native libraries built: libyang 2.1.152 and libyang-cpp 1.1.0.
- Phase 0 checks passed: one pytest test, Ruff lint and format, `pip check`, GNPy CLI help, and the packaged `Site_A` to `Site_B` GNPy example. The sample run used one 80 km SSMF span and 76 channels at 50 GHz spacing; final path GSNR was 31.17 dB at 0.1 nm and 27.09 dB in signal bandwidth. It emitted a documented non-fatal Roadm `type_variety` default warning.
- `requirements.lock`, setup instructions, Phase 0 verification, data-source search, attribution and learning notes are in the repo. No Kaggle credential or external topology data is configured/downloaded.
- User corrected the requested next phase: **begin Phase 1**, not Phase 2. Phase 1 work is now authorized. Phase 2 has not started.

## Phase 1 scope and mandatory checkpoint

The user-provided master prompt is at `/home/ubuntu/upload/Master_Prompt_Manus_QoT_Fiber_Platform.pdf` in the current workspace. Re-read its Phase 1 and CP1 pages before implementation. Phase 1 requires:

1. At least 10 Internet Topology Zoo GraphML networks, preferably 15–60 nodes, with complete geographic coordinates and a mix of national/continental scales.
2. At least 3 SNDlib native-format networks with coordinates, plus a parser.
3. A clearly labeled illustrative synthetic Tunisia network of about 12 cities, with real city coordinates, plausible ring-plus-mesh links, configurable great-circle route factor 1.2–1.3, and no claim that it represents an operator network.
4. Configurable link/span construction with spans of at most about 80 km, EDFAs at span ends, ROADMs at cities, GNPy equipment-library SSMF parameters, and configurable connector/splice losses.
5. A converter producing both unified `data/topologies/<id>.json` files (nodes, coordinates, link lengths, spans) and valid GNPy network JSON.
6. At least one end-to-end GNPy path run per topology; document physical-output fields and bandwidth conventions.
7. Read modulation/transceiver modes and feasibility thresholds from the installed GNPy equipment configuration; do not invent or hard-code guessed thresholds.

CP1 is mandatory. Before any Phase 2 work, report the selected topologies (names, node/link counts), successful GNPy runs, example output, exact modes/thresholds, and problems, then stop and wait for the user to say `go`.

## Exact starting point for the next agent

1. Read this file, `README.md`, `docs/phase0-environment.md`, `docs/learning_notes.md`, `docs/ATTRIBUTION.md`, and the master prompt Phase 1 pages.
2. Check `git status --short --branch`, `git log -1 --oneline`, and `gh api repos/maryem1008/fiber-qot-platform --jq .private`; confirm a clean `main` and `true` visibility before editing.
3. Research official topology sources, download only candidates whose provenance/terms are understood, record source URL, license/redistribution terms, source filename, node/link counts, and coordinate completeness. Never commit credentials or unlicensed source data.
4. Implement Phase 1 in reproducible scripts/config; test conversion and GNPy runs; save learning notes and a data/provenance record. Update this handoff with exact progress as work proceeds.
5. Commit and push each durable checkpoint to the private GitHub repo. Stop at CP1 for the owner's approval; do not begin Phase 2 before the explicit `go`.

## Active topology-source research workflow

- Workflow job: `0da7f1f53084` (addon job), launched 2026-11-23. Purpose: discover and independently verify 10 Internet Topology Zoo and 3 SNDlib candidates. Research only; no files or datasets were downloaded by the workflow.
- Budget: 15 estimated/requested agent calls, effective limit 17. Planned stages are one discovery agent, one verifier per each of the 13 candidates, then one synthesis agent.
- Last observed status (2026-11-23 18:14 local): running; 14 agents spawned, 4 completed, 1 running (`0da7f1f53084_a4`), and 9 queued. The workflow result had not yet been delivered.
- If continuing in this same task, use the existing job and wait for its result; do not start a duplicate workflow. After completion, save the structured evidence and recommended candidate set in a project report, then verify licenses and coordinate completeness before any download.
- If the job is inaccessible from a new task, inspect the job list/history first. If no retained result is available, restart the source review and record that it is a rerun. Do not treat queued or incomplete research as verified.

## Phase 1 progress at this checkpoint

- No Phase 1 topologies have been downloaded or converted.
- No Phase 1 parser, converter, or generation scripts exist yet.
- Topology-source research is in progress in job `0da7f1f53084`; no candidate selection has been accepted and no source files have been downloaded.
- Do not claim the Phase 1 deliverables or CP1 are complete until actual files and simulator runs exist.
