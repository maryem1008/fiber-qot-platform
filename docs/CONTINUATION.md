# Continuation checkpoint

## Current state

- Repository: `maryem1008/fiber-qot-platform`.
- Active branch: `fix/phase2-dataset-quality`.
- Phase 1 topology conversion is complete. Phase 2 work items WI-1 through WI-10 are committed on the branch.
- The 2,000-scenario pilot completed: 2,000 successful, 0 failed, 0 rejected, 0 duplicate IDs, two workers.
- The pilot report recommends NO-GO for 100,000 rows until controlled launch-power and channel-load checks are done.
- Do not run the 100,000-row generation or begin Phase 3.

## Phase 2 work-item commits

| Work item | Commit | Summary |
|---|---|---|
| WI-1 | `e9f556a` | Correct feasibility to compare 0.1 nm GSNR with the configured OSNR requirement. |
| WI-2 | `e86fcb9` | Resolve equipment portably, cache safe templates, and support multiprocessing. |
| WI-3 | `92bd5a7` | Add deterministic independent scenario sampling and constrained route selection. |
| WI-4 | `720b19a` | Equalize span lengths and let GNPy select amplifier design. |
| WI-5 | `2232b38` | Compute structural features from the simulated GNPy path. |
| WI-6 | `c5e0185` | Capture real per-span simulator metrics and clearly label derived geometry. |
| WI-7 | `f5ced8e` | Add atomic chunk output, manifests, resume, and merge support. |
| WI-8 | `8b48dee` | Derive NLI labels consistently across bandwidths with explicit invalid flags. |
| WI-9 | `a9ad1c9` | Mark GNPy tests, add non-GNPy CI readiness, and prepare the pilot target. |
| WI-10 | `a1a1881` | Document data provenance and the pilot checkpoint. |

These are short hashes for reference; verify the current branch history before continuing.

## Evidence and known adaptations

- GNPy 3.0.1 compares mode OSNR requirements in the 0.1 nm reference bandwidth. The primary regression
  target is `gsnr_db_01nm`; signal-bandwidth `gsnr_db` is retained separately.
- The previous index-based sampler repeated only 80 parameter combinations per topology. The replacement
  independently samples scenario parameters and route rank.
- The configured [-3, 3] dBm range rounded to 0.01 dB contains at most 601 distinct powers. The owner
  approved a sampler test threshold of at least 550 distinct values rather than the impossible >1,000.
- GNPy-dependent tests are marked `gnpy`. The marked suite last passed 12 tests in 99.68 seconds; the full
  suite last passed 21 tests. Ruff lint and format checks passed.
- Topology Zoo and SNDlib input terms are not fully verified; see `docs/ATTRIBUTION.md`.

## Next checkpoint

1. Review, commit, and push the measured pilot report and four plots.
2. Stop and wait for the user's direction. Do not start the 100,000-row run or Phase 3; the pilot recommendation
   is NO-GO until controlled launch-power and channel-load diagnostics are addressed.

Do not run 100,000 scenarios or start Phase 3.
