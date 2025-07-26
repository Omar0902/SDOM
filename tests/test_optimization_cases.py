import os
import pandas as pd
import pytest

from SDOM.io_manager import load_data, export_results
from SDOM.optimization_main import run_solver, initialize_model
from pyomo.environ import *

def test_optimization_model_ini_case_no_resiliency():

    test_data_path = os.path.join(os.path.dirname(__file__), '..', 'Data')
    test_data_path = os.path.abspath(test_data_path)
    
    data = load_data( test_data_path )

    model = initialize_model(data, with_resilience_constraints=False)

    # Count constraints by type
    constraint_counts = {"equality": 0, "inequality": 0}

    for constraint in model.component_objects(Constraint, active=True):
        for index in constraint:
            con = constraint[index]
            if con.equality:  # Check if it's an equality constraint
                constraint_counts["equality"] += 1
            else:  # Otherwise, it's an inequality constraint
                constraint_counts["inequality"] += 1

    assert constraint_counts["equality"] == 170
    assert constraint_counts["inequality"] == 522


def test_optimization_model_res_case_no_resiliency():

    test_data_path = os.path.join(os.path.dirname(__file__), '..', 'Data')
    test_data_path = os.path.abspath(test_data_path)
    
    data = load_data( test_data_path )

    model = initialize_model(data, with_resilience_constraints=False)

    best_result = run_solver(model, optcr=0.0, num_runs=1)
    
    assert best_result[2]['Problem'][0]["Number of constraints"] == 643
    assert best_result[2]['Problem'][0]["Number of variables"] == 628
    assert best_result[2]['Problem'][0]["Number of binary variables"] == 96
    assert best_result[2]['Problem'][0]["Number of objectives"] == 1
    assert best_result[2]['Problem'][0]["Number of nonzeros"] == 282

    assert best_result[2]['Solver'][0]["Termination condition"] =="optimal"

    assert abs( best_result[1]["Total_Cost"] - 3285154847.471892 ) <= 10 
    assert abs( best_result[1]["Total_CapWind"] - 24907.852743827232 ) <= 1
    assert abs(  best_result[1]["Total_CapScha"]["Li-Ion"] - 1254.8104 ) <= 1
    assert abs(  best_result[1]["Total_CapScha"]["CAES"] -1340.7415 ) <= 1
    # if best_result:
    #     export_results(model, 'no_resilience')
    
    