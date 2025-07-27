from pyomo.environ import *

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

def get_optimization_problem_info( best_result ):
    
    if best_result:
        return {
            "Number of constraints": best_result[2]['Problem'][0]["Number of constraints"],
            "Number of variables": best_result[2]['Problem'][0]["Number of variables"],
            "Number of binary variables": best_result[2]['Problem'][0]["Number of binary variables"],
            "Number of objectives": best_result[2]['Problem'][0]["Number of objectives"],
            "Number of nonzeros": best_result[2]['Problem'][0]["Number of nonzeros"]
        }
    return None

def get_optimization_problem_solution_info( best_result ):
    best_result[2]['Solver'][0]["Termination condition"] == "optimal"

    # assert abs( best_result[1]["Total_Cost"] - 3285154847.471892 ) <= 10 
    # assert abs( best_result[1]["Total_CapWind"] - 24907.852743827232 ) <= 1
    # assert abs(  best_result[1]["Total_CapScha"]["Li-Ion"] - 1254.8104 ) <= 1
    # assert abs(  best_result[1]["Total_CapScha"]["CAES"] -1340.7415 ) <= 1
    # assert abs( best_result[1]["Total_CapScha"]["PHS"] - 0.0 ) <= 1
    # assert abs( best_result[1]["Total_CapScha"]["H2"] - 0.0 ) <= 1
    if best_result:
        return {
            "Termination condition": best_result[2]['Solver'][0]["Termination condition"],
            "Total_Cost": best_result[1]["Total_Cost"],
            "Total_CapWind": best_result[1]["Total_CapWind"],
            "Total_CapScha": best_result[1]["Total_CapScha"],
            "Total_CapScha_Li-Ion": best_result[1]["Total_CapScha"]["Li-Ion"],
            "Total_CapScha_CAES": best_result[1]["Total_CapScha"]["CAES"],
            "Total_CapScha_PHS": best_result[1]["Total_CapScha"]["PHS"],
            "Total_CapScha_H2": best_result[1]["Total_CapScha"]["H2"]
        }
    return None