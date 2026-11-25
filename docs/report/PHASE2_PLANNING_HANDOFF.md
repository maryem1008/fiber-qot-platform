# Phase 2 Planning Handoff

**Status: In progress — Phase 2 is not complete.**

## Objective

Complete Phase 2 of the fiber QoT platform: produce a reliable, reproducible, documented simulation dataset at the project's target scale, with valid path- and span-level outputs.

## Last recorded project state

The latest handoff reports the repository clean on `main`, synced with `origin/main`, at commit `f1e4002`.

The Phase 2 simulator and GNPy bidirectional routing are implemented. A Germany50 route was verified, and bounded simulation runs completed. However, the dataset-generation workflow and output quality still need work.

## What has been demonstrated

- GNPy 3.0.1 simulation runs with the project's converted topologies.
- The Germany50 Hannover–Oldenburg route succeeded: 3 spans, 142.81 km, GSNR 18.8484 dB.
- A bounded run reported 990 successful rows and 0 failures across 18 topologies. Do not treat this as 1,000 attempts: the generator's integer allocation currently produces 990 rows for `--runs 1000`.
- A subsequent schema test overwrote the smoke output with 90 successful path rows. The current smoke files therefore do not represent the earlier 990-row run.
- The planned 100,000-row dataset has not been generated.

## Main issues to resolve

1. **Exact run counts:** Distribute remainders so `--runs N` produces exactly N attempts. Report requested, attempted, successful, and failed counts distinctly.
2. **Span metrics correctness:** Current span output includes placeholders or estimates: empty geometry, missing cumulative ASE, hardcoded zero NLI, repeated path-level cumulative values, and approximate input/output powers. Extract actual GNPy per-span values or omit/explicitly label unavailable fields.
3. **Resumable generation:** `--chunk-size` is not yet implemented as durable chunking/resume. Plan checkpointing and safe restart behavior.
4. **Artifact reconciliation:** Clearly identify what the existing generated files contain, and avoid presenting the 90-row smoke output as the 990-row result.
5. **Scale and runtime:** A prior 100-run benchmark took 123.899 seconds (about 1.239 seconds per run), implying roughly 34.4 hours sequentially for 100,000 runs before accounting for overhead. Rebenchmark the corrected workflow and evaluate a safe, reproducible scaling strategy.
6. **Reproducibility and provenance:** Keep deterministic seeding, document that the added 0.35 dB Gaussian GSNR noise is synthetic, and resolve or accurately disclose the SNDlib licensing/provenance caveat.

## Relevant files

- [phase2.py](../../src/fiber_qot_platform/simulation/phase2.py) — simulation execution and path/span fields.
- [phase2_generate.py](../../scripts/phase2_generate.py) — run allocation and output generation.
- [simulation.yaml](../../configs/simulation.yaml) — configured ranges and targets.
- [CP2_PHASE2_REPORT.md](./CP2_PHASE2_REPORT.md) — prior benchmark and bounded-run report.
- [DATA_CARD.md](../DATA_CARD.md) — dataset conventions and caveats.
- [CONTINUATION.md](../CONTINUATION.md) — project status and handoff history.
- [test_phase2_generation.py](../../tests/test_phase2_generation.py) — current generation tests.

## Planning request

Inspect the current repository and produce an implementation plan—not code yet—to close the gaps above. Include sequenced work items, dependencies, risks, measurable acceptance criteria, validation commands, and a go/no-go checkpoint before the 100,000-row run. Preserve existing behavior where possible, and distinguish simulated/synthetic values from actual GNPy outputs.
