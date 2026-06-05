"""Phase 3 / Deliverable C: tests for ``build_baseline_dispatch`` / ``run_baseline_dispatch``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyomo.environ as pyo
import pytest

from sdom.resiliency import (
    BaselineDispatchResults,
    DesignedSystem,
    build_baseline_dispatch,
    load_designed_system,
    run_baseline_dispatch,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT_DIR_3MW = REPO_ROOT / "Data" / "resiliency_eval" / "3MW_critical_load_24hrs_outage_24hrs_recovery"
INPUTS_DIR_PGNE = (
    REPO_ROOT
    / "Data"
    / "resiliency_eval"
    / "inputs_previous_stage"
    / "Paper_PGnE"
    / "Paper"
)
INPUTS_DIR_MEA = REPO_ROOT / "res_runs_paper" / "inputs" / "inputs_csv" / "Paper_MEA 1"
SNAPSHOT_DIR_MEA = REPO_ROOT / "res_runs_paper" / "inputs" / "outputs_CEM" / "For_simulations_MEA"

N_HOURS = 24
YEAR = 2030
SCENARIO_ID = 1  # = "0.5SOC"


@pytest.fixture(scope="module")
def designed_system_mea() -> DesignedSystem:
    if not INPUTS_DIR_MEA.exists() or not SNAPSHOT_DIR_MEA.exists():
        pytest.skip(f"Paper_MEA fixtures missing under {INPUTS_DIR_MEA.parent.parent}")
    return load_designed_system(
        SNAPSHOT_DIR_MEA,
        inputs_dir=INPUTS_DIR_MEA,
        year=YEAR,
        scenario_id=SCENARIO_ID,
    )


@pytest.fixture(scope="module")
def baseline_model_mea(designed_system_mea):
    return build_baseline_dispatch(designed_system_mea, n_hours=N_HOURS)


@pytest.fixture(scope="module")
def baseline_results_mea(baseline_model_mea):
    return run_baseline_dispatch(baseline_model_mea, solver="highs")


# ---------------------------------------------------------------------------
# Synthetic fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def synthetic_designed_system_24h() -> DesignedSystem:
    n = 24
    idx = pd.RangeIndex(start=1, stop=n + 1, name="Hour")

    storage_caps = {
        "Li-Ion": {
            "Cap_Pch": 10.0,
            "Cap_Pdis": 10.0,
            "Cap_E": 40.0,
            "eta_ch": 0.9,
            "eta_dis": 0.9,
            "soc_min_frac": 0.0,
            "vom": 0.0,
        }
    }
    solar_caps = {"S1": 50.0}
    wind_caps = {"W1": 30.0}

    cf_solar = pd.DataFrame({"S1": [0.3] * n}, index=idx)
    cf_wind = pd.DataFrame({"W1": [0.4] * n}, index=idx)

    return DesignedSystem(
        storage_caps=storage_caps,
        thermal_caps={},
        solar_caps=solar_caps,
        wind_caps=wind_caps,
        load=pd.Series([50.0] * n, index=idx, name="Load"),
        cf_solar=cf_solar,
        cf_wind=cf_wind,
        nuclear=pd.Series([0.0] * n, index=idx, name="Nuclear"),
        hydro=pd.Series([0.0] * n, index=idx, name="Hydro"),
        other_renewables=pd.Series([0.0] * n, index=idx, name="OtherRen"),
        import_cap=pd.Series([100.0] * n, index=idx, name="Imports"),
        import_price=pd.Series([50.0] * n, index=idx, name="Imports_price"),
        export_cap=pd.Series([0.0] * n, index=idx, name="Exports"),
        export_price=pd.Series([0.0] * n, index=idx, name="Exports_price"),
        phi_fix_t=pd.Series([10.0] * n, index=idx, name="phi_fix"),
        phi_var_t=pd.Series([2.0] * n, index=idx, name="phi_var"),
        month_of_hour=pd.Series([1] * n, index=idx, name="month"),
        scenario_id=1,
        year=2030,
        formulation_map={
            "Imports": "ImportsWithDemandChargesFormulation",
            "Exports": "WithoutNetLoadConstraints",
        },
    )


# ---------------------------------------------------------------------------
# Solver helper
# ---------------------------------------------------------------------------
def _highs():
    for name in ("appsi_highs", "highs"):
        try:
            s = pyo.SolverFactory(name)
            if s is not None and s.available(exception_flag=False):
                return s
        except Exception:
            continue
    pytest.skip("HiGHS solver not available")


# ---------------------------------------------------------------------------
# 1. Structure
# ---------------------------------------------------------------------------
def test_build_baseline_dispatch_n_hours_24(synthetic_designed_system_24h):
    model = build_baseline_dispatch(synthetic_designed_system_24h, n_hours=24)
    assert isinstance(model, pyo.ConcreteModel)
    # Hour set
    assert list(model.h) == list(range(1, 25))
    # Imports block (Phase 2 builder)
    assert hasattr(model.imports, "Pimp")
    assert hasattr(model.imports, "D_fix")
    assert hasattr(model.imports, "D_var")
    # Exports block (pure-LP)
    assert hasattr(model.exports, "Pexp")
    # Storage block
    assert hasattr(model.storage, "Pcha")
    assert hasattr(model.storage, "Pdis")
    assert hasattr(model.storage, "SOC")
    # VRE blocks
    assert hasattr(model.solar, "Psolar")
    assert hasattr(model.wind, "Pwind")
    assert ("S1", 1) in model.solar.Psolar
    assert ("W1", 1) in model.wind.Pwind
    # Power balance constraint
    assert hasattr(model, "power_balance")
    for t in model.h:
        assert t in model.power_balance
    # Objective
    assert hasattr(model, "objective")
    assert isinstance(model.objective, pyo.Objective)


def test_baseline_dispatch_capacities_pinned(synthetic_designed_system_24h):
    model = build_baseline_dispatch(synthetic_designed_system_24h, n_hours=24)
    s = "Li-Ion"
    for t in model.h:
        assert model.storage.Pcha[s, t].ub == pytest.approx(10.0)
        assert model.storage.Pdis[s, t].ub == pytest.approx(10.0)
        assert model.storage.SOC[s, t].ub == pytest.approx(40.0)
        assert model.solar.Psolar["S1", t].ub == pytest.approx(0.3 * 50.0)
        assert model.wind.Pwind["W1", t].ub == pytest.approx(0.4 * 30.0)


def test_baseline_dispatch_solves_feasible(synthetic_designed_system_24h):
    solver = _highs()
    model = build_baseline_dispatch(synthetic_designed_system_24h, n_hours=24)
    res = solver.solve(model)
    assert str(res.solver.termination_condition) == "optimal"
    obj = pyo.value(model.objective)
    assert obj == pytest.approx(obj)  # finite (NaN check)
    assert obj < 1e15

    s = "Li-Ion"
    for t in model.h:
        gen = (
            sum(pyo.value(model.solar.Psolar[k, t]) for k in synthetic_designed_system_24h.solar_caps)
            + sum(pyo.value(model.wind.Pwind[w, t]) for w in synthetic_designed_system_24h.wind_caps)
            + pyo.value(model.storage.Pdis[s, t])
            + pyo.value(model.imports.Pimp[t])
        )
        cha = pyo.value(model.storage.Pcha[s, t])
        exp = pyo.value(model.exports.Pexp[t])
        load = synthetic_designed_system_24h.load.loc[t]
        assert gen - load - cha - exp == pytest.approx(0.0, abs=1e-6)


def test_baseline_dispatch_min_soc_per_tech_kwarg(synthetic_designed_system_24h):
    solver = _highs()
    model = build_baseline_dispatch(
        synthetic_designed_system_24h,
        n_hours=24,
        min_soc_per_tech={"Li-Ion": 0.5},
    )
    s = "Li-Ion"
    for t in model.h:
        assert model.storage.SOC[s, t].lb == pytest.approx(0.5 * 40.0)
    res = solver.solve(model)
    assert str(res.solver.termination_condition) == "optimal"
    for t in model.h:
        assert pyo.value(model.storage.SOC[s, t]) >= 0.5 * 40.0 - 1e-6


def test_run_baseline_dispatch_returns_results(synthetic_designed_system_24h):
    _highs()
    model = build_baseline_dispatch(synthetic_designed_system_24h, n_hours=24)
    results = run_baseline_dispatch(model)
    assert isinstance(results, BaselineDispatchResults)
    assert results.solver_status == "optimal"
    assert isinstance(results.objective_value, float)

    assert isinstance(results.soc_trajectory, pd.DataFrame)
    assert results.soc_trajectory.shape == (24, 1)
    assert isinstance(results.pcha_trajectory, pd.DataFrame)
    assert isinstance(results.pdis_trajectory, pd.DataFrame)
    assert isinstance(results.psolar_trajectory, pd.DataFrame)
    assert results.psolar_trajectory.shape == (24, 1)
    assert isinstance(results.pwind_trajectory, pd.DataFrame)
    assert results.pwind_trajectory.shape == (24, 1)
    # thermal empty in fixture
    assert isinstance(results.pthermal_trajectory, pd.DataFrame)
    assert results.pthermal_trajectory.shape[0] == 24
    assert results.pthermal_trajectory.shape[1] == 0

    for attr in ("pimp", "pexp", "nuclear", "hydro", "other_renewables", "load", "month_of_hour"):
        s = getattr(results, attr)
        assert isinstance(s, pd.Series)
        assert len(s) == 24


# ---------------------------------------------------------------------------
# Real PGnE smoke
# ---------------------------------------------------------------------------
@pytest.mark.slow
def test_baseline_dispatch_real_pgne_24h():
    _highs()
    ds = load_designed_system(
        SNAPSHOT_DIR_3MW,
        inputs_dir=INPUTS_DIR_PGNE,
        year=2030,
        scenario_id=1,
    )
    model = build_baseline_dispatch(ds, n_hours=24)
    results = run_baseline_dispatch(model)
    assert results.solver_status == "optimal"
    assert results.objective_value == pytest.approx(results.objective_value)
    assert abs(results.objective_value) < 1e15


# ---------------------------------------------------------------------------
# FOM accounting (Z^B_FOM)
# ---------------------------------------------------------------------------
@pytest.mark.integration
def test_designed_system_carries_fom(designed_system_mea):
    ds = designed_system_mea

    # Storage: fom (USD/kW-yr) and cost_ratio match StorageData_2030.csv.
    for tech, spec in ds.storage_caps.items():
        assert "fom" in spec and isinstance(spec["fom"], float)
        assert "cost_ratio" in spec and isinstance(spec["cost_ratio"], float)
    if "Li-Ion" in ds.storage_caps:
        assert ds.storage_caps["Li-Ion"]["fom"] == pytest.approx(7.9)
        assert ds.storage_caps["Li-Ion"]["cost_ratio"] == pytest.approx(0.5)
    if "H2" in ds.storage_caps:
        assert ds.storage_caps["H2"]["fom"] == pytest.approx(46.0)
        assert ds.storage_caps["H2"]["cost_ratio"] == pytest.approx(0.325)

    # Thermal: fom present (0.0 in MEA inputs).
    for bu, spec in ds.thermal_caps.items():
        assert "fom" in spec and isinstance(spec["fom"], float)
        assert spec["fom"] == pytest.approx(0.0)

    # Solar / Wind: per-plant FOM_M dicts populated.
    assert ds.solar_fom and ds.wind_fom
    for pid in ds.solar_caps:
        assert pid in ds.solar_fom
        assert isinstance(ds.solar_fom[pid], float)
        assert ds.solar_fom[pid] == pytest.approx(18.0)
    for pid in ds.wind_caps:
        assert pid in ds.wind_fom
        assert isinstance(ds.wind_fom[pid], float)
        assert ds.wind_fom[pid] == pytest.approx(29.3)


@pytest.mark.integration
def test_cost_breakdown_reconciles(baseline_results_mea):
    cb = baseline_results_mea.cost_breakdown
    assert isinstance(cb, dict) and cb
    for key in (
        "thermal_var_USD",
        "storage_var_USD",
        "imports_USD",
        "exports_USD",
        "demand_charges_USD",
        "curtailment_USD",
        "fom_USD",
        "total_USD",
    ):
        assert key in cb
        assert isinstance(cb[key], float)

    # FOM > 0 in MEA (solar=18, wind=29.3, storage non-zero).
    assert cb["fom_USD"] > 0.0

    sum_components = (
        cb["thermal_var_USD"]
        + cb["storage_var_USD"]
        + cb["imports_USD"]
        - cb["exports_USD"]
        + cb["demand_charges_USD"]
        + cb["curtailment_USD"]
        + cb["fom_USD"]
    )
    assert sum_components == pytest.approx(cb["total_USD"], rel=1e-6, abs=1.0)
    assert cb["total_USD"] == pytest.approx(baseline_results_mea.objective_value)


@pytest.mark.integration
def test_fom_constant_independent_of_dispatch(designed_system_mea):
    _highs()
    tech = next(iter(designed_system_mea.storage_caps))
    m_a = build_baseline_dispatch(designed_system_mea, n_hours=N_HOURS)
    m_b = build_baseline_dispatch(
        designed_system_mea,
        n_hours=N_HOURS,
        min_soc_per_tech={tech: 0.5},
    )
    r_a = run_baseline_dispatch(m_a)
    r_b = run_baseline_dispatch(m_b)
    assert r_a.cost_breakdown["fom_USD"] == pytest.approx(
        r_b.cost_breakdown["fom_USD"], rel=1e-9
    )
