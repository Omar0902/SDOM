from pyomo.environ import Constraint

from sdom import OptimizationResults


def get_n_eq_ineq_constraints(model):
    # Count constraints by type
    constraint_counts = {"equality": 0, "inequality": 0}

    for constraint in model.component_objects(Constraint, active=True):
        for index in constraint:
            con = constraint[index]
            if con.equality:  # Check if it's an equality constraint
                constraint_counts["equality"] += 1
            else:  # Otherwise, it's an inequality constraint
                constraint_counts["inequality"] += 1

    return constraint_counts


def get_optimization_problem_info(results: OptimizationResults) -> dict:
    """Extract problem information from optimization results.

    Parameters
    ----------
    results : OptimizationResults
        The optimization results object from run_solver().

    Returns
    -------
    dict
        Dictionary with problem information (constraints, variables, etc.).
    """
    if results is not None:
        return results.get_problem_info()
    return None


def get_optimization_problem_solution_info(results: OptimizationResults) -> dict:
    """Extract solution information from optimization results.

    Parameters
    ----------
    results : OptimizationResults
        The optimization results object from run_solver().

    Returns
    -------
    dict
        Dictionary with solution information (termination condition, costs, capacities).
    """
    if results is not None:
        return {
            "Termination condition": results.termination_condition,
            "Total_Cost": results.total_cost,
            "Total_CapWind": results.total_cap_wind,
            "Total_CapPV": results.total_cap_pv,
            "Total_CapScha": results.total_cap_storage_charge,
            "Total_CapScha_Li-Ion": results.total_cap_storage_charge.get("Li-Ion", 0.0),
            "Total_CapScha_CAES": results.total_cap_storage_charge.get("CAES", 0.0),
            "Total_CapScha_PHS": results.total_cap_storage_charge.get("PHS", 0.0),
            "Total_CapScha_H2": results.total_cap_storage_charge.get("H2", 0.0),
        }
    return None
