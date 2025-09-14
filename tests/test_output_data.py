#include tests for csv outputs
import os

from sdom import load_data
from sdom import run_solver, initialize_model, export_results, get_default_solver_config_dict

def test_output_files_creation_case_no_resiliency():

    test_data_path = os.path.join(os.path.dirname(__file__), '..', 'Data')
    test_data_path = os.path.abspath(test_data_path)
    
    data = load_data( test_data_path )

    model = initialize_model( data, n_hours = 24, with_resilience_constraints = False )

    #solver_dict = get_default_solver_config_dict(solver_name="cbc", executable_path=".\\Solver\\bin\\cbc.exe")
    solver_dict = get_default_solver_config_dict(solver_name="highs", executable_path="")
    best_result = run_solver( model, solver_dict )

    export_results(model, 'test_data')
    
    files_names = ["OutputGeneration_test_data", "OutputStorage_test_data", "OutputSummary_test_data"]
    for file_name in files_names:
        assert os.path.exists(os.path.join('./results_pyomo/', f"{file_name}.csv"))

    #cleanup
    for file_name in files_names:
        os.remove(os.path.join('./results_pyomo/', f"{file_name}.csv"))