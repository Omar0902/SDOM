# PR Group 2 Plan: Vectorize Result Collection (Tier A2 + B6 + B3)

## Objective
Reduce result-collection wall time by moving from Python row-by-row loops to one-pass NumPy extraction and vectorized DataFrame assembly, while preserving the current schema and behavior.

## Scope
This slice targets:

1. A2: One-pass extraction of solved variable values into NumPy arrays
2. B6: Reuse extracted arrays for totals and DataFrame outputs
3. B3: Vectorize interregional exchanges DataFrame creation

Out of scope:
- Model formulation changes
- Solver configuration changes
- Resiliency module changes

## Target Files
- src/sdom/results.py
- tests/ (only if assertions need adjustment for equivalent behavior)

## Implementation Strategy

### 1. Vectorize _collect_host_metrics
- Build reusable arrays once for:
  - solar/wind generation and curtailment
  - thermal generation matrix (hour x plant)
  - storage charge/discharge/SOC matrix (hour x tech)
  - hydro, nuclear, other-renewables, imports, exports, load, net-load
- Build `generation_df` from arrays in one DataFrame constructor call.
- Build `storage_df` using flattened matrices (`repeat`/`tile`) and one constructor call.
- Build `thermal_generation_df` from thermal matrix directly.
- Keep output column names and ordering unchanged.

### 2. Reuse arrays for totals
- Compute technology totals from already-extracted arrays (avoid repeated symbolic traversals).
- Keep `cost_breakdown` structure unchanged.

### 3. Vectorize _build_interregional_exchanges_df
- Build flattened arrays for `(line, hour)` combinations once.
- Compute signed and directional flows via vectorized operations.
- Compute utilization columns with `np.where` as today.
- Preserve exact output schema and column order.

## Validation Plan
- Run targeted tests:
  - tests/test_zonal_results.py
  - tests/test_zonal_io_export.py
  - tests/test_zonal_model_build.py
  - tests/test_zonal_legacy_regression.py
- If needed, run additional result/export tests.

## Risks and Mitigation
- Risk: subtle schema drift in DataFrame columns/order.
  - Mitigation: keep explicit ordered-column creation.
- Risk: NaN handling differences for uninitialized values.
  - Mitigation: preserve existing row filtering semantics.
- Risk: aggregation mismatches vs. legacy helper behavior.
  - Mitigation: compare totals against current tests and adjust only for exact parity.

## Done Criteria
- Result schemas unchanged.
- Targeted tests pass.
- Measurable runtime improvement on long-horizon zonal case.
