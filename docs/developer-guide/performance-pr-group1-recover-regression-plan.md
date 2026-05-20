# PR Group 1 Plan: Recover Regression (Tier S)

## Objective
Recover the observed SDOM runtime regression (~40%) without removing any current capability and without changing optimization outputs.

## Scope
This PR group includes only Tier S actions:

1. S1: Make memory profiling overhead opt-in (disable tracemalloc by default)
2. S2: Add a fast path in data loading to skip unnecessary per-area augmentation for legacy single-area datasets
3. S3: Reduce hot-path overhead in result collection value extraction
4. S4: Remove eager numeric rounding during CSV load to avoid full-frame copies

Out of scope:
- Resiliency module (`src/sdom/resiliency`)
- New formulations
- Solver strategy changes

## Files Expected to Change
- `src/sdom/optimization_main.py`
- `src/sdom/utils_performance_meassure.py`
- `src/sdom/io_manager.py`
- `src/sdom/common/utilities.py`
- `src/sdom/results.py` (only if needed for S3 fast-path integration)
- tests under `tests/` as needed for behavior lock

## Implementation Plan

### Step 1: S1 (Profiler overhead opt-in)
- Keep profiler timing enabled.
- Disable memory tracking (`tracemalloc`) by default.
- Add opt-in switches:
  - environment variable `SDOM_PROFILE_MEMORY`
  - optional parameter support in model initialization path if needed.
- Preserve existing profiling table output format.

Acceptance:
- Default runs do not start `tracemalloc`.
- Setting `SDOM_PROFILE_MEMORY=1` enables memory tracking.

### Step 2: S4 (Remove eager `.round(5)` during load)
- Remove `.round(5)` from large CSV reads in `load_data`.
- Keep type conversions and schema checks unchanged.
- Ensure no missing-key behavior changes.

Acceptance:
- Same data keys and same solver/model behavior.
- Numeric differences only at precision beyond prior 5-decimal rounding.

### Step 3: S2 (Legacy fast path in per-area augmentation)
- Add an early-exit branch in `_augment_with_per_area_views` when:
  - no `areas.csv` present
  - no area tags (`@...@`) found in relevant wide headers
  - no `area_id` column in relevant row-oriented tables.
- In fast path, populate required `per_area_*` fields by referencing existing loaded data under `DEFAULT_AREA_ID`.
- Preserve all existing public keys and compatibility.

Acceptance:
- Legacy single-area folders produce equivalent outputs.
- Zonal datasets continue current behavior.

### Step 4: S3 (Hot-path value extraction)
- Add a low-overhead value helper for post-solve collection loops.
- Use direct `.value` when available to avoid repeated exception-driven control flow.
- Keep fallback behavior for expressions and optional/uninitialized variables.

Acceptance:
- Result collection schema unchanged.
- No regressions in old result export paths.

## Validation Strategy
- Run targeted tests first:
  - legacy solve tests
  - zonal io/result tests
  - export tests
- Run additional regression tests if any failures appear.
- Perform one benchmark comparison using a representative legacy case to confirm runtime trend.

## Risk and Mitigation
- Risk: tiny numeric differences after removing `.round(5)`.
  - Mitigation: keep assertions tolerance-based where appropriate.
- Risk: legacy fast path missing one required per-area key.
  - Mitigation: add explicit key coverage tests.
- Risk: helper change in value extraction affects uninitialized values.
  - Mitigation: preserve `None` semantics and test optional paths.

## Delivery Checklist
- [x] Branch created
- [x] Plan doc committed
- [x] S1 implemented and tested
- [ ] S4 implemented and tested (deferred: objective parity lock)
- [x] S2 implemented and tested
- [x] S3 implemented and tested
- [ ] Summary benchmark recorded
- [ ] PR description includes before/after timing and capability parity notes

## Current Branch Status

Implemented in branch `perf/recover-regression-tier-s`:

1. S1 implemented: memory profiling is now opt-in via `SDOM_PROFILE_MEMORY`.
2. S2 implemented: `_augment_with_per_area_views` now has a legacy fast path when no area encoding exists.
3. S3 implemented: `safe_pyomo_value` now uses a low-overhead `.value` fast path before fallback evaluation.

Validation run:
- `tests/test_input_data.py`
- `tests/test_zonal_io_per_area.py`
- `tests/test_zonal_results.py`
- `tests/test_zonal_legacy_regression.py`
- Result: 49 passed, 0 failed.

S4 note:
- A first implementation that removed `.round(5)` in `load_data` changed locked legacy objective values and failed `test_zonal_legacy_regression`.
- To preserve capability parity, S4 was rolled back in this branch and should be revisited only with an explicit precision-policy decision.
