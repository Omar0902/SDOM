from pyomo.environ import *

import logging
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
from pyomo.environ import value
from pyomo.environ import Binary
from pyomo.util.infeasible import log_infeasible_constraints
from pyomo.core import Var, Constraint
from pyomo.environ import *

from .initializations import initialize_sets, initialize_params
from .common.utilities import safe_pyomo_value
from .models.formulations_vre import add_vre_variables, add_vre_balance_constraints
from .models.formulations_thermal import add_gascc_variables
from .models.formulations_resiliency import add_resiliency_variables, add_resiliency_constraints
from .models.formulations_storage import add_storage_variables, add_storage_constraints
from .models.formulations_system import objective_rule, add_system_constraints
# ---------------------------------------------------------------------------------
# Model initialization
# Safe value function for uninitialized variables/parameters

def initialize_model(data, n_hours = 8760, with_resilience_constraints=False, model_name="SDOM_Model"):
    """
    Initializes and configures a Pyomo optimization model for the SDOM framework.
    This function sets up the model structure, including sets, parameters, variables, 
    objective function, and constraints for power system optimization. It supports 
    optional resilience constraints and allows customization of the model name and 
    simulation horizon.
    Args:
        data (dict): Input data required for model initialization, including system 
            parameters, time series, and technology characteristics.
        n_hours (int, optional): Number of hours to simulate (default is 8760, 
            representing a full year).
        with_resilience_constraints (bool, optional): If True, adds resilience-related 
            constraints to the model (default is False).
        model_name (str, optional): Name to assign to the Pyomo model instance 
            (default is "SDOM_Model").
    Returns:
        ConcreteModel: A fully initialized Pyomo ConcreteModel object ready for 
            optimization.
    """

    logging.info("Instantiating SDOM Pyomo optimization model...")
    model = ConcreteModel(name=model_name)

    logging.info("Initializing model sets and parameters...")
    initialize_sets( model, data, n_hours = n_hours )
    
    initialize_params( model, data )    

    # ----------------------------------- Variables -----------------------------------
    logging.info("Adding variables to the model...")
    # Define VRE (wind/solar variables
    add_vre_variables( model )
    
    # Capacity of backup GCC units
    add_gascc_variables( model )

    # Resilience variables
    add_resiliency_variables( model )

    # Storage-related variables
    add_storage_variables( model )

    # -------------------------------- Objective function -------------------------------
    logging.info("Adding objective function to the model...")
    model.Obj = Objective( rule = objective_rule, sense = minimize )

    # ----------------------------------- Constraints -----------------------------------
    logging.info("Adding constraints to the model...")
    #system Constraints
    add_system_constraints( model )    

    #resiliency Constraints
    if with_resilience_constraints:
        add_resiliency_constraints( model )
  
    #VRE balance constraints
    add_vre_balance_constraints( model )

    #Storage constraints
    add_storage_constraints( model )
    
    # Build a model size report
    #all_objects = muppy.get_objects()
    #print(summary.summarize(all_objects))

    return model

# ---------------------------------------------------------------------------------
# Results collection function
def collect_results( model ):
    """
    Collects and computes results from a Pyomo optimization model for an energy system.
    This function extracts key results from the provided Pyomo model instance, including total costs,
    installed capacities, generation, dispatch, and detailed cost breakdowns for various technologies
    (solar PV, wind, gas, and multiple storage types such as Li-Ion, CAES, PHS, and H2).
    The results are returned as a dictionary with descriptive keys.
    Parameters
    ----------
    model : pyomo.core.base.PyomoModel.ConcreteModel
        The Pyomo model instance containing the optimization results and parameters.
    Returns
    -------
    results : dict
        A dictionary containing the following keys and their corresponding computed values:
            - 'Total_Cost': Total objective value of the model.
            - 'Total_CapCC': Installed capacity of gas combined cycle.
            - 'Total_CapPV': Total installed capacity of solar PV.
            - 'Total_CapWind': Total installed capacity of wind.
            - 'Total_CapScha': Installed charging power capacity for each storage type.
            - 'Total_CapSdis': Installed discharging power capacity for each storage type.
            - 'Total_EcapS': Installed energy capacity for each storage type.
            - 'Total_GenPV': Total generation from solar PV.
            - 'Total_GenWind': Total generation from wind.
            - 'Total_GenS': Total storage discharge for each storage type.
            - 'SolarPVGen': Hourly solar PV generation.
            - 'WindGen': Hourly wind generation.
            - 'GenGasCC': Hourly gas combined cycle generation.
            - 'SolarCapex', 'WindCapex': Annualized capital expenditures for solar and wind.
            - 'SolarFOM', 'WindFOM': Fixed O&M costs for solar and wind.
            - 'LiIonPowerCapex', 'LiIonEnergyCapex', 'LiIonFOM', 'LiIonVOM': Cost breakdowns for Li-Ion storage.
            - 'CAESPowerCapex', 'CAESEnergyCapex', 'CAESFOM', 'CAESVOM': Cost breakdowns for CAES storage.
            - 'PHSPowerCapex', 'PHSEnergyCapex', 'CAESFOM', 'CAESVOM': Cost breakdowns for PHS storage.
            - 'H2PowerCapex', 'H2EnergyCapex', 'H2FOM', 'H2VOM': Cost breakdowns for H2 storage.
            - 'GasCCCapex', 'GasCCFuel', 'GasCCFOM', 'GasCCVOM': Cost breakdowns for gas combined cycle.
    Notes
    -----
    - The function assumes the existence of a helper function `safe_pyomo_value` to safely extract values from Pyomo variables.
    - The model is expected to have specific sets and parameters (e.g., model.k, model.w, model.j, model.h, and various cost parameters).
    """

    logging.info("Collecting SDOM results...")
    results = {}
    results['Total_Cost'] = safe_pyomo_value(model.Obj.expr)

    # Capacity and generation results
    results['Total_CapCC'] = safe_pyomo_value(model.CapCC)
    results['Total_CapPV'] = sum(safe_pyomo_value(model.Ypv[k]) * model.CapSolar_CAPEX_M[k] for k in model.k)
    results['Total_CapWind'] = sum(safe_pyomo_value(model.Ywind[w]) * model.CapWind_CAPEX_M[w] for w in model.w)
    results['Total_CapScha'] = {j: safe_pyomo_value(model.Pcha[j]) for j in model.j}
    results['Total_CapSdis'] = {j: safe_pyomo_value(model.Pdis[j]) for j in model.j}
    results['Total_EcapS'] = {j: safe_pyomo_value(model.Ecap[j]) for j in model.j}

    # Generation and dispatch results
    results['Total_GenPV'] = sum(safe_pyomo_value(model.GenPV[h]) for h in model.h)
    results['Total_GenWind'] = sum(safe_pyomo_value(model.GenWind[h]) for h in model.h)
    results['Total_GenS'] = {j: sum(safe_pyomo_value(model.PD[h, j]) for h in model.h) for j in model.j}

    results['SolarPVGen'] = {h: safe_pyomo_value(model.GenPV[h]) for h in model.h}
    results['WindGen'] = {h: safe_pyomo_value(model.GenWind[h]) for h in model.h}
    results['GenGasCC'] = {h: safe_pyomo_value(model.GenCC[h]) for h in model.h}
    
    results['SolarCapex'] = sum((model.FCR_VRE * (1000 * model.CapSolar_CAPEX_M[k] + model.CapSolar_trans_cap_cost[k])) \
                                * model.CapSolar_capacity[k] * model.Ypv[k] for k in model.k)
    results['WindCapex'] =  sum((model.FCR_VRE * (1000 * model.CapWind_CAPEX_M[w] + model.CapWind_trans_cap_cost[w])) \
                                * model.CapWind_capacity[w] * model.Ywind[w] for w in model.w)
    results['SolarFOM'] = sum((model.FCR_VRE * 1000*model.CapSolar_FOM_M[k]) * model.CapSolar_capacity[k] * model.Ypv[k] for k in model.k)
    results['WindFOM'] =  sum((model.FCR_VRE * 1000*model.CapWind_FOM_M[w]) * model.CapWind_capacity[w] * model.Ywind[w] for w in model.w)

    results['LiIonPowerCapex'] = model.CRF['Li-Ion']*(1000*model.StorageData['CostRatio', 'Li-Ion'] * model.StorageData['P_Capex', 'Li-Ion']*model.Pcha['Li-Ion']
                        + 1000*(1 - model.StorageData['CostRatio', 'Li-Ion']) * model.StorageData['P_Capex', 'Li-Ion']*model.Pdis['Li-Ion'])
    results['LiIonEnergyCapex'] = model.CRF['Li-Ion']*1000*model.StorageData['E_Capex', 'Li-Ion']*model.Ecap['Li-Ion']
    results['LiIonFOM'] = 1000*model.StorageData['CostRatio', 'Li-Ion'] * model.StorageData['FOM', 'Li-Ion']*model.Pcha['Li-Ion'] \
                        + 1000*(1 - model.StorageData['CostRatio', 'Li-Ion']) * model.StorageData['FOM', 'Li-Ion']*model.Pdis['Li-Ion']
    results['LiIonVOM'] = model.StorageData['VOM', 'Li-Ion'] * sum(model.PD[h, 'Li-Ion'] for h in model.h) 
    
    results['CAESPowerCapex'] = model.CRF['CAES']*(1000*model.StorageData['CostRatio', 'CAES'] * model.StorageData['P_Capex', 'CAES']*model.Pcha['CAES']\
                                + 1000*(1 - model.StorageData['CostRatio', 'CAES']) * model.StorageData['P_Capex', 'CAES']*model.Pdis['CAES'])
    results['CAESEnergyCapex'] = model.CRF['CAES']*1000*model.StorageData['E_Capex', 'CAES']*model.Ecap['CAES']
    results['CAESFOM'] = 1000*model.StorageData['CostRatio', 'CAES'] * model.StorageData['FOM', 'CAES']*model.Pcha['CAES']\
                        + 1000*(1 - model.StorageData['CostRatio', 'CAES']) * model.StorageData['FOM', 'CAES']*model.Pdis['CAES']
    results['CAESVOM'] = model.StorageData['VOM', 'CAES'] * sum(model.PD[h, 'CAES'] for h in model.h) 
    
    results['PHSPowerCapex'] = model.CRF['PHS']*(1000*model.StorageData['CostRatio', 'PHS'] * model.StorageData['P_Capex', 'PHS']*model.Pcha['PHS']
                                + 1000*(1 - model.StorageData['CostRatio', 'PHS']) * model.StorageData['P_Capex', 'PHS']*model.Pdis['PHS'])
    results['PHSEnergyCapex'] = model.CRF['PHS']*1000*model.StorageData['E_Capex', 'PHS']*model.Ecap['PHS']

    results['PHSFOM'] = 1000*model.StorageData['CostRatio', 'PHS'] * model.StorageData['FOM', 'PHS']*model.Pcha['PHS']\
                        + 1000*(1 - model.StorageData['CostRatio', 'PHS']) * model.StorageData['FOM', 'PHS']*model.Pdis['PHS']
    results['PHSVOM'] = model.StorageData['VOM', 'PHS'] * sum(model.PD[h, 'PHS'] for h in model.h) 
    
    results['H2PowerCapex'] = model.CRF['H2']*(1000*model.StorageData['CostRatio', 'H2'] * model.StorageData['P_Capex', 'H2']*model.Pcha['H2']
                        + 1000*(1 - model.StorageData['CostRatio', 'H2']) * model.StorageData['P_Capex', 'H2']*model.Pdis['H2'])
    results['H2EnergyCapex'] = model.CRF['H2']*1000*model.StorageData['E_Capex', 'H2']*model.Ecap['H2']
    results['H2FOM'] = 1000*model.StorageData['CostRatio', 'H2'] * model.StorageData['FOM', 'H2']*model.Pcha['H2']\
                    + 1000*(1 - model.StorageData['CostRatio', 'H2']) * model.StorageData['FOM', 'H2']*model.Pdis['H2']
    results['H2VOM'] = model.StorageData['VOM', 'H2'] * sum(model.PD[h, 'H2'] for h in model.h) 
        
    results['GasCCCapex'] = model.FCR_GasCC*1000*model.CapexGasCC*model.CapCC
    results['GasCCFuel'] = (model.GasPrice * model.HR) * sum(model.GenCC[h] for h in model.h)
    results['GasCCFOM'] = 1000*model.FOM_GasCC*model.CapCC
    results['GasCCVOM'] = (model.GasPrice * model.HR) * sum(model.GenCC[h] for h in model.h)

    return results


# Run solver function
def run_solver(model, log_file_path='./solver_log.txt', optcr=0.0, num_runs=1, cbc_executable_path=None):
    """
    Solves the given optimization model using the CBC solver, optionally running multiple times with varying target values.
    Args:
        model: The Pyomo optimization model to be solved. The model must have an attribute 'GenMix_Target' that can be set.
        log_file_path (str, optional): Path to the solver log file. Defaults to './solver_log.txt'.
        optcr (float, optional): The relative MIP gap (optimality criterion) for the solver. Defaults to 0.0.
        num_runs (int, optional): Number of optimization runs to perform, each with a different 'GenMix_Target' value. Defaults to 1.
        cbc_executable_path (str, optional): Path to the CBC solver executable. If None, uses the default CBC solver.
    Returns:
        tuple: A tuple containing:
            - results_over_runs (list): List of dictionaries with results from each run, including 'GenMix_Target' and other collected results.
            - best_result (dict or None): The result dictionary with the lowest 'Total_Cost' found across all runs, or None if no optimal solution was found.
            - result (SolverResults): The Pyomo solver results object from the last run.
    """

    logging.info("Starting to solve SDOM model...")
    solver = SolverFactory('cbc', executable=cbc_executable_path) if cbc_executable_path else SolverFactory('cbc')
    solver.options['loglevel'] = 3
    solver.options['mip_rel_gap'] = optcr
    solver.options['tee'] = True
    solver.options['keepfiles'] = True
    solver.options['logfile'] = log_file_path

    results_over_runs = []
    best_result = None
    best_objective_value = float('inf')

    for run in range(num_runs):
        target_value = 0.95 + 0.05 * (run + 1) # REVIEW THIS. DO WE NEED THIS FOR LOOP?
        model.GenMix_Target.set_value(target_value)

        logging.info(f"Running optimization for GenMix_Target = {target_value:.2f}")
        result = solver.solve(model, 
                              #, tee=True, keepfiles = True, #working_dir='C:/Users/mkoleva/Documents/Masha/Projects/LDES_Demonstration/CBP/TEA/Results/solver_log.txt'
                             )
        
        if (result.solver.status == SolverStatus.ok) and (result.solver.termination_condition == TerminationCondition.optimal):
            # If the solution is optimal, collect the results
            run_results = collect_results(model)
            run_results['GenMix_Target'] = target_value
            results_over_runs.append(run_results)
            # Update the best result if it found a better one
            if 'Total_Cost' in run_results and run_results['Total_Cost'] < best_objective_value:
                best_objective_value = run_results['Total_Cost']
                best_result = run_results
        else:
            logging.warning(f"Solver did not find an optimal solution for GenMix_Target = {target_value:.2f}.")
            # Log infeasible constraints for debugging
            logging.warning("Logging infeasible constraints...")
            log_infeasible_constraints(model)

    return results_over_runs, best_result, result
