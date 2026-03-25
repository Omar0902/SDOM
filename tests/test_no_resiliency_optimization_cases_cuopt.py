"""Tests for SDOM optimization using NVIDIA cuOpt solver.

cuOpt is a GPU-accelerated LP/MILP solver. These tests are skipped
automatically when the cuopt Python package is not installed or when no
compatible NVIDIA GPU (Volta+ / Compute Capability >= 7.0) is available.

Installation (Linux / WSL2, CUDA 12.x):
    pip install --extra-index-url=https://pypi.nvidia.com cuopt-cu12

See: https://github.com/NVIDIA/cuopt
"""
import os
import pytest

from sdom import load_data
from sdom import run_solver, initialize_model, get_default_solver_config_dict

from utils_tests import (
    check_supply_balance_constraint,
    check_budget_constraint,
    get_n_eq_ineq_constraints,
    get_optimization_problem_info,
    get_optimization_problem_solution_info,
)
from constants_test import (
    REL_PATH_DATA_RUN_OF_RIVER_TEST,
    REL_PATH_DATA_HYDRO_BUDGET_TEST,
    REL_PATH_DATA_DAILY_HYDRO_BUDGET_TEST,
    REL_PATH_DATA_DAILY_HYDRO_BUDGET_IMP_EXP_TEST,
)

# ---------------------------------------------------------------------------
# Availability guard — skip every test in this module if cuopt is not usable
# ---------------------------------------------------------------------------
try:
    import pyomo.environ  # registers cuopt plugin
    from pyomo.opt import SolverFactory

    _cuopt_solver = SolverFactory("cuopt")
    # available() raises ApplicationError when bindings are missing
    _cuopt_available = _cuopt_solver.available()
except Exception:
    _cuopt_available = False

pytestmark = pytest.mark.skipif(
    not _cuopt_available,
    reason="cuOpt solver is not available (requires NVIDIA GPU + cuopt Python package)",
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _get_cuopt_solver_dict():
    """Return a solver configuration dict for cuOpt."""
    return get_default_solver_config_dict(solver_name="cuopt", executable_path="")


# ---------------------------------------------------------------------------
# Run-of-river tests (no hydro budget)
# ---------------------------------------------------------------------------


def test_model_ini_cuopt_no_resiliency_24h():
    """Model initialisation with run-of-river hydro (24 h, no resiliency)."""
    test_data_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", REL_PATH_DATA_RUN_OF_RIVER_TEST)
    )
    data = load_data(test_data_path)
    model = initialize_model(data, n_hours=24, with_resilience_constraints=False)

    constraint_counts = get_n_eq_ineq_constraints(model)
    assert constraint_counts["equality"] == 194
    assert constraint_counts["inequality"] == 549


def test_optimization_res_cuopt_no_resiliency_24h():
    """Full solve with cuOpt — run-of-river hydro, 24 h, no resiliency."""
    test_data_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", REL_PATH_DATA_RUN_OF_RIVER_TEST)
    )
    data = load_data(test_data_path)
    model = initialize_model(data, n_hours=24, with_resilience_constraints=False)

    solver_dict = _get_cuopt_solver_dict()
    try:
        results = run_solver(model, solver_dict)
        assert results is not None
    except Exception as e:
        pytest.fail(f"{run_solver.__name__} failed with error: {e}")

    problem_sol_dict = get_optimization_problem_solution_info(results)
    assert problem_sol_dict["Termination condition"] == "optimal"
    assert abs(problem_sol_dict["Total_Cost"] - 3285154847.471892) <= 10
    assert abs(problem_sol_dict["Total_CapWind"] - 26681.257521521577) <= 1
    assert abs(problem_sol_dict["Total_CapPV"] - 0.0) <= 0.001
    assert abs(problem_sol_dict["Total_CapScha_Li-Ion"] - 1254.8104) <= 1
    assert abs(problem_sol_dict["Total_CapScha_CAES"] - 1340.7415) <= 1
    assert abs(problem_sol_dict["Total_CapScha_PHS"] - 0.0) <= 1
    assert abs(problem_sol_dict["Total_CapScha_H2"] - 0.0) <= 1

    # Supply balance
    supply_balance_check = check_supply_balance_constraint(results)
    assert supply_balance_check["is_satisfied"], (
        f"Supply balance violated at hours: {supply_balance_check['violations']}"
    )
    assert supply_balance_check["has_imports"] is False, (
        "Imports should not be present in this test case"
    )
    assert supply_balance_check["has_exports"] is False, (
        "Exports should not be present in this test case"
    )


# ---------------------------------------------------------------------------
# Monthly hydro budget tests
# ---------------------------------------------------------------------------


def test_model_ini_cuopt_no_resiliency_730h_monthly_budget():
    """Model initialisation with monthly hydro budget (730 h, no resiliency)."""
    test_data_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", REL_PATH_DATA_HYDRO_BUDGET_TEST)
    )
    data = load_data(test_data_path)
    model = initialize_model(data, n_hours=730, with_resilience_constraints=False)

    constraint_counts = get_n_eq_ineq_constraints(model)
    assert constraint_counts["equality"] == 5113
    assert constraint_counts["inequality"] == 25571


def test_optimization_res_cuopt_no_resiliency_730h_monthly_budget():
    """Full solve with cuOpt — monthly hydro budget, 730 h, no resiliency."""
    test_data_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", REL_PATH_DATA_HYDRO_BUDGET_TEST)
    )
    data = load_data(test_data_path)
    model = initialize_model(data, n_hours=730, with_resilience_constraints=False)

    solver_dict = _get_cuopt_solver_dict()
    try:
        results = run_solver(model, solver_dict)
        assert results is not None
    except Exception as e:
        pytest.fail(f"{run_solver.__name__} failed with error: {e}")

    problem_sol_dict = get_optimization_problem_solution_info(results)
    assert problem_sol_dict["Termination condition"] == "optimal"
    assert abs(problem_sol_dict["Total_Cost"] - 441627.4738187364) <= 10
    assert abs(problem_sol_dict["Total_CapWind"] - 0.0) <= 1
    assert abs(problem_sol_dict["Total_CapPV"] - 0.0) <= 0.001
    assert abs(problem_sol_dict["Total_CapScha_Li-Ion"] - 0.0) <= 1
    assert abs(problem_sol_dict["Total_CapScha_CAES"] - 0.0) <= 1
    assert abs(problem_sol_dict["Total_CapScha_PHS"] - 0.0) <= 1
    assert abs(problem_sol_dict["Total_CapScha_H2"] - 0.0) <= 1

    # Supply balance
    supply_balance_check = check_supply_balance_constraint(results)
    assert supply_balance_check["is_satisfied"], (
        f"Supply balance violated at hours: {supply_balance_check['violations']}"
    )
    assert supply_balance_check["has_imports"] is False, (
        "Imports should not be present in this test case"
    )
    assert supply_balance_check["has_exports"] is False, (
        "Exports should not be present in this test case"
    )

    # Hydro budget (1 monthly period)
    budget_check = check_budget_constraint(model, block_name="hydro")
    assert budget_check["is_satisfied"], (
        f"Hydro budget violated at periods: {budget_check['violations']}"
    )
    assert budget_check["n_budget_periods"] == 1, (
        f"Expected 1 monthly budget period, got {budget_check['n_budget_periods']}"
    )


# ---------------------------------------------------------------------------
# Daily hydro budget tests (no imports/exports)
# ---------------------------------------------------------------------------


def test_model_ini_cuopt_no_resiliency_168h_daily_budget():
    """Model initialisation with daily hydro budget (168 h, no resiliency)."""
    test_data_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", REL_PATH_DATA_DAILY_HYDRO_BUDGET_TEST)
    )
    data = load_data(test_data_path)
    model = initialize_model(data, n_hours=168, with_resilience_constraints=False)

    constraint_counts = get_n_eq_ineq_constraints(model)
    assert constraint_counts["equality"] == 1185
    assert constraint_counts["inequality"] == 5901


def test_optimization_res_cuopt_no_resiliency_168h_daily_budget():
    """Full solve with cuOpt — daily hydro budget, 168 h, no resiliency."""
    test_data_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", REL_PATH_DATA_DAILY_HYDRO_BUDGET_TEST)
    )
    data = load_data(test_data_path)
    model = initialize_model(data, n_hours=168, with_resilience_constraints=False)

    solver_dict = _get_cuopt_solver_dict()
    try:
        results = run_solver(model, solver_dict)
        assert results is not None
    except Exception as e:
        pytest.fail(f"{run_solver.__name__} failed with error: {e}")

    problem_sol_dict = get_optimization_problem_solution_info(results)
    assert problem_sol_dict["Termination condition"] == "optimal"
    print(problem_sol_dict["Total_Cost"])
    assert abs(problem_sol_dict["Total_Cost"] - 578101.3) <= 10
    assert abs(problem_sol_dict["Total_CapWind"] - 0.0) <= 1
    assert abs(problem_sol_dict["Total_CapPV"] - 0.0) <= 0.001
    assert abs(problem_sol_dict["Total_CapScha_Li-Ion"] - 0.0) <= 1
    assert abs(problem_sol_dict["Total_CapScha_CAES"] - 0.0) <= 1
    assert abs(problem_sol_dict["Total_CapScha_PHS"] - 0.0) <= 1
    assert abs(problem_sol_dict["Total_CapScha_H2"] - 0.0) <= 1

    # Supply balance
    supply_balance_check = check_supply_balance_constraint(results)
    assert supply_balance_check["is_satisfied"], (
        f"Supply balance violated at hours: {supply_balance_check['violations']}"
    )
    assert supply_balance_check["has_imports"] is False, (
        "Imports should not be present in this test case"
    )
    assert supply_balance_check["has_exports"] is False, (
        "Exports should not be present in this test case"
    )

    # Hydro budget (7 daily periods of 24 h each)
    budget_check = check_budget_constraint(model, block_name="hydro")
    assert budget_check["is_satisfied"], (
        f"Hydro budget violated at periods: {budget_check['violations']}"
    )
    assert budget_check["n_budget_periods"] == 7, (
        f"Expected 7 daily budget periods, got {budget_check['n_budget_periods']}"
    )
    assert budget_check["budget_scalar"] == 24, (
        f"Expected daily budget scalar of 24 hours, got {budget_check['budget_scalar']}"
    )


# ---------------------------------------------------------------------------
# Daily hydro budget tests WITH imports/exports
# ---------------------------------------------------------------------------


def test_model_ini_cuopt_no_resiliency_168h_daily_budget_imp_exp():
    """Model initialisation with daily hydro budget + imports/exports (168 h)."""
    test_data_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", REL_PATH_DATA_DAILY_HYDRO_BUDGET_IMP_EXP_TEST
        )
    )
    data = load_data(test_data_path)
    model = initialize_model(data, n_hours=168, with_resilience_constraints=False)

    constraint_counts = get_n_eq_ineq_constraints(model)
    assert constraint_counts["equality"] == 1185
    assert constraint_counts["inequality"] == 6909


def test_optimization_res_cuopt_no_resiliency_168h_daily_budget_imp_exp():
    """Full solve with cuOpt — daily hydro budget + imports/exports, 168 h."""
    test_data_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", REL_PATH_DATA_DAILY_HYDRO_BUDGET_IMP_EXP_TEST
        )
    )
    data = load_data(test_data_path)
    model = initialize_model(data, n_hours=168, with_resilience_constraints=False)

    solver_dict = _get_cuopt_solver_dict()
    try:
        results = run_solver(model, solver_dict)
        assert results is not None
    except Exception as e:
        pytest.fail(f"{run_solver.__name__} failed with error: {e}")

    problem_sol_dict = get_optimization_problem_solution_info(results)
    assert problem_sol_dict["Termination condition"] == "optimal"
    print(problem_sol_dict["Total_Cost"])
    assert abs(problem_sol_dict["Total_Cost"] + 77686751.88) <= 10
    assert abs(problem_sol_dict["Total_CapWind"] - 1.0) <= 0.001
    assert abs(problem_sol_dict["Total_CapPV"] - 1.0) <= 0.001
    assert abs(problem_sol_dict["Total_CapScha_Li-Ion"] - 0.0) <= 1
    assert abs(problem_sol_dict["Total_CapScha_CAES"] - 0.0) <= 1
    assert abs(problem_sol_dict["Total_CapScha_PHS"] - 0.0) <= 1
    assert abs(problem_sol_dict["Total_CapScha_H2"] - 0.0) <= 1

    # Supply balance
    supply_balance_check = check_supply_balance_constraint(results)
    assert supply_balance_check["is_satisfied"], (
        f"Supply balance violated at hours: {supply_balance_check['violations']}"
    )
    assert supply_balance_check["has_exports"] is True, (
        "Exports should be present in this test case"
    )

    # Hydro budget (7 daily periods)
    budget_check = check_budget_constraint(model, block_name="hydro")
    assert budget_check["is_satisfied"], (
        f"Hydro budget violated at periods: {budget_check['violations']}"
    )
    assert budget_check["n_budget_periods"] == 7, (
        f"Expected 7 daily budget periods, got {budget_check['n_budget_periods']}"
    )
