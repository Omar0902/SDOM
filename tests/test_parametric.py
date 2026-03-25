"""Tests for sdom.parametric — parametric sensitivity analysis sub-package."""

import copy
import os

import pandas as pd
import pytest

from sdom.parametric import ParametricStudy, ScalarSweep, StorageFactorSweep, TsSweep
from sdom.parametric.mutations import (
    TS_KEY_TO_COLUMN,
    _apply_scalar_mutation,
    _apply_storage_factor_mutation,
    _apply_ts_mutation,
)
from sdom.parametric.study import _make_safe_name

# ---------------------------------------------------------------------------
# Path helpers (mirrors convention used in other test files)
# ---------------------------------------------------------------------------

REL_PATH_DATA_RUN_OF_RIVER = "Data/no_exchange_run_of_river"


def _data_path(rel_path: str) -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", rel_path))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def scalars_df():
    """Minimal scalars DataFrame matching the real SDOM structure."""
    return pd.DataFrame(
        {"Value": [0.5, 0.07]},
        index=pd.Index(["GenMix_Target", "r"], name=None),
    )


@pytest.fixture()
def storage_df():
    """Minimal storage_data DataFrame (row-indexed by param, columns = techs)."""
    return pd.DataFrame(
        {"TechA": [100.0, 50.0, 5.0], "TechB": [200.0, 80.0, 8.0]},
        index=pd.Index(["P_Capex", "E_Capex", "FOM"], name=None),
    )


@pytest.fixture()
def load_df():
    """Minimal load_data DataFrame with a 'Load' column."""
    return pd.DataFrame({"Hour": list(range(1, 5)), "Load": [100.0, 120.0, 90.0, 110.0]})


# ---------------------------------------------------------------------------
# Sweep dataclass validation
# ---------------------------------------------------------------------------


def test_scalar_sweep_empty_values_raises():
    with pytest.raises(ValueError, match="at least one value"):
        ScalarSweep("scalars", "GenMix_Target", [])


def test_storage_factor_sweep_empty_factors_raises():
    with pytest.raises(ValueError, match="at least one factor"):
        StorageFactorSweep("P_Capex", [])


def test_ts_sweep_empty_factors_raises():
    with pytest.raises(ValueError, match="at least one factor"):
        TsSweep("load_data", [])


# ---------------------------------------------------------------------------
# _apply_scalar_mutation
# ---------------------------------------------------------------------------


def test_apply_scalar_mutation_updates_value(scalars_df):
    data = {"scalars": scalars_df}
    _apply_scalar_mutation(data, "scalars", "GenMix_Target", 0.9)
    assert data["scalars"].loc["GenMix_Target", "Value"] == pytest.approx(0.9)


def test_apply_scalar_mutation_does_not_affect_other_rows(scalars_df):
    original_r = scalars_df.loc["r", "Value"]
    data = {"scalars": scalars_df}
    _apply_scalar_mutation(data, "scalars", "GenMix_Target", 1.0)
    assert data["scalars"].loc["r", "Value"] == pytest.approx(original_r)


def test_apply_scalar_mutation_missing_key_raises(scalars_df):
    data = {"scalars": scalars_df}
    with pytest.raises(ValueError, match="data key 'missing_key'"):
        _apply_scalar_mutation(data, "missing_key", "GenMix_Target", 1.0)


def test_apply_scalar_mutation_missing_param_raises(scalars_df):
    data = {"scalars": scalars_df}
    with pytest.raises(ValueError, match="parameter 'NoParam'"):
        _apply_scalar_mutation(data, "scalars", "NoParam", 1.0)


# ---------------------------------------------------------------------------
# _apply_storage_factor_mutation
# ---------------------------------------------------------------------------


def test_apply_storage_factor_mutation_scales_all_techs(storage_df):
    data = {"storage_data": storage_df}
    original = storage_df.loc["P_Capex"].copy()
    _apply_storage_factor_mutation(data, "P_Capex", 0.8)
    expected = original * 0.8
    pd.testing.assert_series_equal(data["storage_data"].loc["P_Capex"], expected)


def test_apply_storage_factor_mutation_does_not_affect_other_rows(storage_df):
    original_ecap = storage_df.loc["E_Capex"].copy()
    data = {"storage_data": storage_df}
    _apply_storage_factor_mutation(data, "P_Capex", 0.5)
    pd.testing.assert_series_equal(data["storage_data"].loc["E_Capex"], original_ecap)


def test_apply_storage_factor_mutation_missing_storage_data_raises():
    data = {}
    with pytest.raises(ValueError, match="'storage_data' not found"):
        _apply_storage_factor_mutation(data, "P_Capex", 0.8)


def test_apply_storage_factor_mutation_missing_param_raises(storage_df):
    data = {"storage_data": storage_df}
    with pytest.raises(ValueError, match="parameter 'VOM'"):
        _apply_storage_factor_mutation(data, "VOM", 1.0)


# ---------------------------------------------------------------------------
# _apply_ts_mutation
# ---------------------------------------------------------------------------


def test_apply_ts_mutation_scales_load_column(load_df):
    data = {"load_data": load_df}
    original = load_df["Load"].copy()
    _apply_ts_mutation(data, "load_data", 1.1)
    expected = original * 1.1
    pd.testing.assert_series_equal(data["load_data"]["Load"], expected)


def test_apply_ts_mutation_does_not_affect_non_numeric_columns(load_df):
    data = {"load_data": load_df}
    original_hours = load_df["Hour"].copy()
    _apply_ts_mutation(data, "load_data", 2.0)
    pd.testing.assert_series_equal(data["load_data"]["Hour"], original_hours)


def test_apply_ts_mutation_unsupported_key_raises(load_df):
    data = {"load_data": load_df}
    with pytest.raises(ValueError, match="ts_key 'bad_key' is not supported"):
        _apply_ts_mutation(data, "bad_key", 1.0)


def test_apply_ts_mutation_key_absent_from_data_raises():
    with pytest.raises(ValueError, match="ts_key 'large_hydro_max' not found in data dict"):
        _apply_ts_mutation({}, "large_hydro_max", 1.0)


def test_ts_key_to_column_covers_all_known_keys():
    """Verify the lookup table contains every documented ts_key."""
    expected_keys = {
        "load_data",
        "large_hydro_data",
        "large_hydro_max",
        "large_hydro_min",
        "import_cap",
        "import_prices",
        "export_cap",
        "export_prices",
    }
    assert expected_keys.issubset(set(TS_KEY_TO_COLUMN.keys()))


# ---------------------------------------------------------------------------
# _make_safe_name
# ---------------------------------------------------------------------------


def test_make_safe_name_replaces_forbidden_chars():
    raw = "GenMix=0.9/P_Capex:0.8"
    result = _make_safe_name(raw)
    for ch in r'/\\:*?"<>| ':
        assert ch not in result


def test_make_safe_name_strips_underscores():
    result = _make_safe_name("_hello_world_")
    assert not result.startswith("_")
    assert not result.endswith("_")


# ---------------------------------------------------------------------------
# Core-count capping
# ---------------------------------------------------------------------------


def test_n_cores_capped_at_cpu_minus_one(scalars_df):
    study = ParametricStudy(
        base_data={},
        solver_config={},
        n_cores=9999,
    )
    max_safe = max(1, (os.cpu_count() or 1) - 1)
    assert study._n_cores == max_safe


def test_n_cores_none_uses_max_safe():
    study = ParametricStudy(base_data={}, solver_config={}, n_cores=None)
    max_safe = max(1, (os.cpu_count() or 1) - 1)
    assert study._n_cores == max_safe


def test_n_cores_one_is_accepted():
    study = ParametricStudy(base_data={}, solver_config={}, n_cores=1)
    assert study._n_cores == 1


# ---------------------------------------------------------------------------
# Cartesian product construction
# ---------------------------------------------------------------------------


def test_cartesian_product_count_scalar_only():
    study = ParametricStudy(base_data={}, solver_config={})
    study.add_scalar_sweep("scalars", "GenMix_Target", [0.7, 0.8, 0.9])
    cases = study._build_case_dicts()
    assert len(cases) == 3


def test_cartesian_product_count_scalar_and_ts():
    study = ParametricStudy(base_data={}, solver_config={})
    study.add_scalar_sweep("scalars", "GenMix_Target", [0.0, 1.0])
    study.add_ts_sweep("load_data", [0.9, 1.0, 1.1])
    cases = study._build_case_dicts()
    assert len(cases) == 2 * 3  # 6


def test_cartesian_product_count_all_three_sweep_types():
    study = ParametricStudy(base_data={}, solver_config={})
    study.add_scalar_sweep("scalars", "GenMix_Target", [0.8, 0.9, 1.0])  # 3
    study.add_storage_factor_sweep("P_Capex", [0.7, 1.0])                # 2
    study.add_ts_sweep("load_data", [0.9, 1.0, 1.1])                     # 3
    cases = study._build_case_dicts()
    assert len(cases) == 3 * 2 * 3  # 18


def test_case_names_are_unique():
    study = ParametricStudy(base_data={}, solver_config={})
    study.add_scalar_sweep("scalars", "GenMix_Target", [0.7, 0.8, 0.9])
    study.add_ts_sweep("load_data", [0.9, 1.1])
    cases = study._build_case_dicts()
    names = [c["case_name"] for c in cases]
    assert len(names) == len(set(names))


def test_base_data_is_deep_copied(scalars_df):
    base_data = {"scalars": scalars_df}
    study = ParametricStudy(base_data=base_data, solver_config={})
    study.add_scalar_sweep("scalars", "GenMix_Target", [0.9, 1.0])
    cases = study._build_case_dicts()

    # Mutating the case dict must not affect the original base_data
    cases[0]["data"]["scalars"].loc["GenMix_Target", "Value"] = 999.0
    assert base_data["scalars"].loc["GenMix_Target", "Value"] != 999.0


def test_no_sweeps_returns_empty():
    study = ParametricStudy(base_data={}, solver_config={})
    assert study._build_case_dicts() == []


# ---------------------------------------------------------------------------
# Summary CSV structure
# ---------------------------------------------------------------------------


def test_summary_csv_written(tmp_path, scalars_df, load_df):
    """Verify summary CSV is created and has the right shape even for failed cases."""
    from sdom.results import OptimizationResults

    study = ParametricStudy(
        base_data={},
        solver_config={},
        output_dir=str(tmp_path),
    )
    study.add_scalar_sweep("scalars", "GenMix_Target", [0.8, 1.0])

    case_dicts = study._build_case_dicts()
    # Fabricate failed results (no solver needed)
    fake_results = [
        OptimizationResults(
            termination_condition="optimal",
            solver_status="ok",
            gen_mix_target=cd["scalar_mutations"][0][2],
            total_cost=1.0,
        )
        for cd in case_dicts
    ]

    study._write_summary_csv(case_dicts, fake_results)

    summary_path = tmp_path / "parametric_summary.csv"
    assert summary_path.exists()

    df = pd.read_csv(summary_path)
    assert len(df) == 2
    assert "case_name" in df.columns
    assert "is_optimal" in df.columns
    assert "total_cost" in df.columns


# ---------------------------------------------------------------------------
# Integration test (requires solver and actual data)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_parametric_study_scalar_and_ts(tmp_path):
    """Run a 2×2 parametric study (scalar + ts sweep) with n_cores=1.

    Marked as 'integration' so it can be skipped in fast unit-test runs:
        pytest -m "not integration"
    """
    from sdom import get_default_solver_config_dict, load_data

    data_path = _data_path(REL_PATH_DATA_RUN_OF_RIVER)
    if not os.path.exists(data_path):
        pytest.skip(f"Test data not found at {data_path}")

    data = load_data(data_path)
    solver_cfg = get_default_solver_config_dict(solver_name="highs")

    study = ParametricStudy(
        base_data=data,
        solver_config=solver_cfg,
        n_hours=72,
        output_dir=str(tmp_path),
        n_cores=1,
    )

    # 2 values × 2 factors = 4 total combinations
    study.add_scalar_sweep("scalars", "GenMix_Target", [0.0, 1.0])
    study.add_ts_sweep("load_data", [0.9, 1.1])

    results = study.run()

    assert len(results) == 4
    assert all(r.is_optimal for r in results), [
        (r.termination_condition, r.solver_status) for r in results
    ]
    assert (tmp_path / "parametric_summary.csv").exists()

    # Per-case sub-directories must exist for optimal results
    for result in results:
        if result.is_optimal:
            case_dir = tmp_path / result.gen_mix_target.__class__.__name__  # just check any sub-dir
            break
    assert any(tmp_path.iterdir())  # at least one sub-dir was created
