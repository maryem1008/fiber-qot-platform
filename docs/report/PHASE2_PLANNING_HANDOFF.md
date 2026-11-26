# Phase 2 planning handoff

**Status: superseded by the Phase 2 dataset-quality work.** This file replaces the earlier open implementation
plan; its old issue list and 100,000-row benchmark estimate are historical and are not the current plan.

## Current state

- Phase 1 topology conversion is complete.
- WI-1 through WI-9 are implemented on `fix/phase2-dataset-quality`; see the commit table in
  [`../CONTINUATION.md`](../CONTINUATION.md).
- WI-10 documentation is included in the current branch checkpoint.
- The redesigned sampler, corrected labels, real per-span capture, and resumable generator are implemented.
- The 2,000-scenario pilot completed with 2,000 successful rows, no failures or rejections, and no duplicate
  scenario IDs. The pilot report recommends no-go pending controlled physical diagnostics.
- The old 100-row and 1,000-row outputs used the former sampler and bandwidth-inconsistent feasibility
  convention; their historical feasibility counts are not current labels.
- No 100,000-row dataset has been generated. Do not start that run or Phase 3 before the pilot report and
  the user's authorization.

## Key conventions

- The primary regression target is GNPy `gsnr_db_01nm`; `gsnr_db` retains signal-bandwidth GSNR.
- Feasibility uses `gsnr_db_01nm - required_osnr_01nm_db` and the configured design margin.
- GNPy values are simulator outputs, not field measurements. NLI labels are derived from same-bandwidth GSNR
  and ASE OSNR. Noise, parameter offsets, and interpolated span geometry are labeled synthetic.
- SNDlib and Topology Zoo terms are not fully verified; see [`../ATTRIBUTION.md`](../ATTRIBUTION.md).
- The configured [-3, 3] dBm range has at most 601 distinct powers when rounded to 0.01 dB; the approved
  sampler-test threshold is 550, not the impossible requirement of more than 1,000.

## Next checkpoint

Commit and push the measured pilot report and plots, then stop for the user's direction. Do not start the
100,000-row generation or Phase 3 while the recommendation remains no-go.
