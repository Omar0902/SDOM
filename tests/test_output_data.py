#include tests for csv outputs
import os

from sdom import load_data
from sdom import run_solver, initialize_model, export_results, get_default_solver_config_dict

from constants_test import REL_PATH_DATA_RUN_OF_RIVER_TEST

def test_output_files_creation_case_no_resiliency():

    test_data_path = os.path.join(os.path.dirname(__file__), '..', REL_PATH_DATA_RUN_OF_RIVER_TEST)
    test_data_path = os.path.abspath(test_data_path)
    
    data = load_data( test_data_path )

    model = initialize_model( data, n_hours = 24, with_resilience_constraints = False )

    #solver_dict = get_default_solver_config_dict(solver_name="cbc", executable_path=".\\Solver\\bin\\cbc.exe")
    solver_dict = get_default_solver_config_dict(solver_name="highs", executable_path="")
    results = run_solver( model, solver_dict )

    case_name = 'test_data'
    export_results(results, case_name)
    
    files_names = ["OutputGeneration_" + case_name, "OutputThermalGeneration_" + case_name, "OutputStorage_" + case_name, "OutputSummary_" + case_name]
    for file_name in files_names:
        assert os.path.exists(os.path.join('./results_pyomo/', f"{file_name}.csv"))

    #cleanup
    for file_name in files_names:
        os.remove(os.path.join('./results_pyomo/', f"{file_name}.csv"))