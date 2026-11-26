# CP2B Phase 2 dataset-quality pilot

## Status

The 2,000-scenario pilot has not yet been run. All result sections below are intentionally pending; no pilot
counts, distributions, runtime, plots, or go/no-go recommendation are asserted here. Complete this report from
the recorded pilot outputs before considering a larger generation run.

## 1. Run counts and failures

Pending pilot: record requested, attempted, successful, failed, and rejected separately, with failure reasons.

## 2. Scenario uniqueness

Pending pilot: record unique-scenario ratio and duplicate `scenario_id` count.

## 3. Runtime

Pending pilot: record elapsed time, runtime per 1,000 requested scenarios (and per 1,000 successful rows if
failures occur), worker count, and clearly labeled 100,000-row estimate.

## 4. Scenario distributions

Pending pilot: report path length, span count, channel count, launch power, mode, and route-rank distributions.

## 5. Feasibility-label comparison

Pending pilot: calculate old- and new-convention feasible shares on the same successful rows, overall and by
mode. Mark the old convention as historical/inconsistent, not as the adopted label.

## 6. Physical sanity checks and plots

Pending pilot: include plots for GSNR versus path distance by mode, GSNR versus span count, GSNR versus launch
power on selected fixed routes, and GSNR versus channel count. State each check's result and any failure.

## 7. Per-span checks

Pending pilot: record pass rates for non-increasing cumulative GSNR, final-span/path agreement, and non-zero
GSNR drops.

## 8. GNPy warnings

The WI-4 Phase 1 design comparison recorded 1,114 warnings before and zero after automatic amplifier variety
selection across the 18 accepted topologies. Recheck and report pilot-time warnings by topology; distinguish
equipment-load warnings from per-topology design warnings.

## 9. Remaining limitations

Pending pilot: record any incomplete checks, unavailable values, topology/data licensing caveats, or other
limitations observed.

## 10. Recommendation

Pending pilot: give a go/no-go recommendation for 100,000 rows, the exact command, and an estimate based on the
measured pilot runtime. Do not start that run until the user authorizes it.
