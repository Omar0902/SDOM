# PR Group 3 Plan: Vectorize Model Build (A1 + A3 + A4 + A5 + A6)

## Objective
Improve model-build performance by reducing Python-loop and expression-construction overhead while preserving behavior and API compatibility.

## Scope
This slice covers:

1. A3: Use quicksum in balance/objective-adjacent expressions and constraints
2. A1: Build VRE capacity-factor mapping in one pass (no melt pipeline)
3. A6: Remove total_hourly_plant_availability expression and inline the plant sum in balance rule
4. A5: Precompute CRF/FCR as float values before Param construction (thermal/storage/VRE)
5. A4: Cache demand/nuclear/hydro/other arrays in thermal upper-bound calculation

## Target files
- src/sdom/models/formulations_system.py
- src/sdom/models/formulations_vre.py
- src/sdom/models/formulations_thermal.py
- src/sdom/models/formulations_storage.py
- (optional helper touch) src/sdom/models/models_utils.py

## Implementation approach

### 1) quicksum for system balances
- Replace Python sum calls in supply balance and generation-mix constraints with quicksum.
- Keep algebra and constraint semantics unchanged.

### 2) VRE CF dict one-pass + remove per-plant availability expression
- Replace melt/filter/set_index pipeline with direct indexed filtering + stack.
- Remove total_hourly_plant_availability Expression block.
- Update vre_balance_rule to inline quicksum(capacity_factor * max_capacity * capacity_fraction).

### 3) Precompute annualization factors (CRF/FCR)
- Compute scalar/dict values as floats in Python before constructing Params:
  - host.FCR_VRE
  - host.thermal.FCR
  - host.storage.CRF
- Preserve existing formula and parameter names.

### 4) Cache arrays for thermal upper-bound calc
- In add_thermal_variables, extract hourly demand/nuclear/hydro/other arrays once.
- Compute CapCC_upper_bound_value from vectorized NumPy operations.

## Validation plan
- Focused tests:
  - tests/test_zonal_model_build.py
  - tests/test_zonal_legacy_regression.py
  - tests/test_no_resiliency_optimization_cases.py
  - tests/test_no_resiliency_hydro_budget_optimization_cases.py
- Extend with additional tests if any parity drift appears.

## Done criteria
- No schema/API changes.
- Focused tests pass.
- Model-build path remains behaviorally equivalent.
- PR notes include expected build-time improvement range (8–20%).
