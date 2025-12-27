import logging
#from pympler import muppy, summary
#from pympler import muppy, summary
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition, check_available_solvers
from pyomo.util.infeasible import log_infeasible_constraints
from pyomo.environ import ConcreteModel, Objective, Block, minimize

from .initializations import initialize_sets, initialize_params
from .common.utilities import safe_pyomo_value
from .models.formulations_vre import add_vre_variables, add_vre_expressions, add_vre_balance_constraints
from .models.formulations_thermal import add_thermal_variables, add_thermal_expressions, add_thermal_constraints
from .models.formulations_resiliency import add_resiliency_variables, add_resiliency_constraints
from .models.formulations_storage import add_storage_variables, add_storage_expressions, add_storage_constraints
from .models.formulations_system import objective_rule, add_system_expressions, add_system_constraints
from .models.formulations_imports_exports import add_imports_variables, add_exports_variables, add_imports_exports_cost_expressions, add_imports_constraints, add_exports_constraints
from .models.formulations_hydro import add_hydro_variables, add_hydro_run_of_river_constraints, add_hydro_budget_constraints

from .constants import MW_TO_KW

from .io_manager import get_formulation
# ---------------------------------------------------------------------------------
# Model initialization
# Safe value function for uninitialized variables/parameters

def initialize_model(data, n_hours = 8760, with_resilience_constraints=False, model_name="SDOM_Model"):
    """
    Initializes and configures a Pyomo optimization model for the SDOM framework.
    
    Sets up the complete model structure including sets (time periods, technologies,
    balancing units), parameters (costs, technical specifications, time series data),
    decision variables (capacity, generation, storage operation), objective function
    (minimize total system cost), and constraints (supply-demand balance, technology-specific
    operational limits, policy requirements).
    
    Model Structure:
        - **Objective**: Minimize total annual system cost (CAPEX + OPEX + fuel)
        - **Decision Variables**: Technology capacities, hourly dispatch, storage operation,
          imports/exports
        - **Constraints**: Energy balance, capacity limits, storage dynamics, hydro budgets,
          ramping limits, policy constraints (GenMix shares, emissions)
        - **Technologies**: Solar PV, Wind, Storage (Li-Ion, CAES, PHS, H2), Thermal,
          Hydro, Nuclear, Other Renewables, Imports/Exports
    
    Args:
        data (dict): Input data dictionary loaded from CSV files containing:
            - Time series: load, capacity factors, generation profiles
            - Technology parameters: costs, efficiencies, lifetimes
            - System scalars: discount rate, planning reserve margin
            - Formulation specifications: hydro model type, import/export settings
        n_hours (int, optional): Number of hours to simulate. Defaults to 8760 (full year).
            Use smaller values for faster testing (e.g., 168 for one week).
        with_resilience_constraints (bool, optional): If True, adds resilience-related
            constraints such as N-1 contingency requirements or diversity mandates.
            Defaults to False.
        model_name (str, optional): Name assigned to the Pyomo ConcreteModel instance.
            Useful for distinguishing multiple model runs. Defaults to "SDOM_Model".
    
    Returns:
        ConcreteModel: A fully initialized Pyomo ConcreteModel object with all sets,
            parameters, variables, objective function, and constraints defined. Ready for
            solving with run_solver().
    
    Side Effects:
        Logs INFO and DEBUG messages about model instantiation progress to the configured
        logging system.
    
    Examples:
        >>> data = load_data('./Data/base_case/')
        >>> model = initialize_model(data)
        >>> print(model.name)  # 'SDOM_Model'
        >>> print(len(model.h))  # 8760
        
        >>> # Test model with one week of data
        >>> model_test = initialize_model(data, n_hours=168, model_name="Test_Week")
        
        >>> # Model with resilience constraints
        >>> model_resilient = initialize_model(data, with_resilience_constraints=True)
    
    Notes:
        - This function does not solve the model; use run_solver() to optimize
        - Formulation choices (e.g., hydro budget vs run-of-river) are specified in
          the input data formulations.csv file
        - Model building takes ~1-10 seconds depending on n_hours and complexity
    """

    logging.info("Instantiating SDOM Pyomo optimization model...")
    model = ConcreteModel(name=model_name)

    logging.debug("Instantiating SDOM Pyomo optimization blocks...")
    model.hydro = Block()

    model.imports = Block()
    model.exports = Block()

    model.demand = Block()
    model.nuclear = Block()
    model.other_renewables = Block()
    if with_resilience_constraints:
        model.resiliency = Block() #TODO implement this block
    model.storage = Block()
    model.thermal = Block()
    model.pv = Block()
    model.wind = Block()

    logging.info("Initializing model sets...")
    initialize_sets( model, data, n_hours = n_hours )
    
    logging.info("Initializing model parameters...")
    initialize_params( model, data )    

    # ----------------------------------- Variables -----------------------------------
    logging.info("Adding variables to the model...")
    # Define VRE (wind/solar variables
    logging.debug("-- Adding VRE variables...")
    add_vre_variables( model )

    logging.debug("-- Adding VRE expressions...")
    add_vre_expressions( model )


    logging.debug("-- Adding thermal generation variables...")
    add_thermal_variables( model )

    logging.debug("-- Adding thermal generation expressions...")
    add_thermal_expressions( model )

    # Resilience variables
    if with_resilience_constraints:
        logging.debug("-- Adding resiliency variables...")
        add_resiliency_variables( model )

    # Storage-related variables
    logging.debug("--Adding storage variables...")
    add_storage_variables( model )
    logging.debug("--Adding storage expressions...")
    add_storage_expressions( model )

    logging.debug("-- Adding hydropower generation variables...")
    add_hydro_variables(model)

    # Imports
    if get_formulation(data, component="Imports") != "NotModel":
        logging.debug("-- Adding Imports variables...")
        add_imports_variables( model )
    
    # Exports
    if get_formulation(data, component="Exports") != "NotModel":
        logging.debug("-- Adding Exports variables...")
        add_exports_variables( model )

    add_imports_exports_cost_expressions(model, data)

    add_system_expressions(model)
    # -------------------------------- Objective function -------------------------------
    logging.info("Adding objective function to the model...")
    model.Obj = Objective( rule = objective_rule, sense = minimize )

    # ----------------------------------- Constraints -----------------------------------
    logging.info("Adding constraints to the model...")
    #system Constraints
    logging.debug("-- Adding system constraints...")
    add_system_constraints( model, data )    

    #resiliency Constraints
    if with_resilience_constraints:
        logging.debug("-- Adding resiliency constraints...")
        add_resiliency_constraints( model )
  
    #VRE balance constraints
    logging.debug("-- Adding VRE balance constraints...")
    add_vre_balance_constraints( model )

    #Storage constraints
    logging.debug("-- Adding storage constraints...")
    add_storage_constraints( model )

    logging.debug("-- Adding thermal generation constraints...")
    add_thermal_constraints( model )

    logging.debug("-- Adding hydropower generation constraints...")
    if get_formulation(data, component="hydro")  == "RunOfRiverFormulation":
        add_hydro_run_of_river_constraints(model, data)
    else:
        add_hydro_budget_constraints(model, data)
    

    # Imports
    if get_formulation(data, component="Imports") != "NotModel":
        logging.debug("-- Adding Imports constraints...")
        add_imports_constraints( model, data )
    
    # Imports
    if get_formulation(data, component="Exports") != "NotModel":
        logging.debug("-- Adding Exports constraints...")
        add_exports_constraints( model, data )

        #add_hydro_variables(model)
    
    # Build a model size report
    # Log memory usage before solving
    # all_objects = muppy.get_objects()
    # logging.info("Memory usage before solving:")
    # logging.info(summary.summarize(all_objects))
    # Log memory usage before solving
    # all_objects = muppy.get_objects()
    # logging.info("Memory usage before solving:")
    # logging.info(summary.summarize(all_objects))

    return model

# ---------------------------------------------------------------------------------
# Results collection function
def collect_results( model ):
    """
    Extracts and organizes optimization results from a solved Pyomo model.
    
    Collects comprehensive results including objective value, installed capacities,
    annual generation totals, hourly dispatch profiles, and detailed cost breakdowns
    for all technologies. Results are organized into a dictionary for easy access
    and post-processing analysis.
    
    Parameters
    ----------
    model : pyomo.core.base.PyomoModel.ConcreteModel
        The solved Pyomo model instance containing optimized variables and computed parameters.
    
    Returns
    -------
    results : dict
        A dictionary containing optimization results with the following categories:
        
        **System-Level Metrics:**
            - 'Total_Cost' (float): Total system cost objective value ($US/year)
        
        **Installed Capacities (MW or MWh):**
            - 'Total_CapPV' (float): Total solar PV capacity (MW)
            - 'Total_CapWind' (float): Total wind capacity (MW)
            - 'Total_CapCC' (float): Total thermal (gas combined cycle) capacity (MW)
            - 'Total_CapScha' (dict): Storage charging power capacity by technology (MW)
            - 'Total_CapSdis' (dict): Storage discharging power capacity by technology (MW)
            - 'Total_EcapS' (dict): Storage energy capacity by technology (MWh)
        
        **Annual Generation Totals (MWh/year):**
            - 'Total_GenPV' (float): Annual solar PV generation
            - 'Total_GenWind' (float): Annual wind generation
            - 'Total_GenS' (dict): Annual storage discharge by technology
        
        **Hourly Dispatch Profiles (arrays of length n_hours):**
            - 'SolarPVGen' (list): Hourly solar PV generation (MW)
            - 'WindGen' (list): Hourly wind generation (MW)
            - 'GenGasCC' (list): Hourly thermal generation (MW)
        
        **Cost Breakdowns ($US/year):**
            - Solar: 'SolarCapex', 'SolarFOM'
            - Wind: 'WindCapex', 'WindFOM'
            - Storage (per technology j): 'Storage{j}PowerCapex', 'Storage{j}EnergyCapex',
              'Storage{j}FOM', 'Storage{j}VOM'
            - Thermal: 'GasCCCapex', 'GasCCFuel', 'GasCCFOM', 'GasCCVOM'
    
    Examples
    --------
    >>> model = run_solver(model, solver_config={'solver': 'cbc'})
    >>> results = collect_results(model)
    >>> print(f"Total Cost: ${results['Total_Cost']:,.0f}/year")
    Total Cost: $4,523,891,234/year
    >>> print(f"Solar PV Capacity: {results['Total_CapPV']:,.0f} MW")
    Solar PV Capacity: 12,345 MW
    >>> hourly_solar = results['SolarPVGen']
    >>> max_solar_hour = max(hourly_solar)
    
    Notes
    -----
    - Uses safe_pyomo_value() to handle undefined variables gracefully
    - Assumes standard SDOM model structure with expected variable names
    - Storage results are indexed by technology (j) from model.storage.j set
    - Hourly profiles useful for detailed operational analysis and visualization
    """

    logging.info("Collecting SDOM results...")
    results = {}
    results['Total_Cost'] = safe_pyomo_value(model.Obj.expr)

    # Capacity and generation results
    logging.debug("Collecting capacity results...")
    results['Total_CapCC'] = safe_pyomo_value(model.thermal.total_installed_capacity )
    results['Total_CapPV'] = safe_pyomo_value( model.pv.total_installed_capacity )
    results['Total_CapWind'] = safe_pyomo_value( model.wind.total_installed_capacity )
    results['Total_CapScha'] = {j: safe_pyomo_value(model.storage.Pcha[j]) for j in model.storage.j}
    results['Total_CapSdis'] = {j: safe_pyomo_value(model.storage.Pdis[j]) for j in model.storage.j}
    results['Total_EcapS'] = {j: safe_pyomo_value(model.storage.Ecap[j]) for j in model.storage.j}

    # Generation and dispatch results
    logging.debug("Collecting generation dispatch results...")
    results['Total_GenPV'] = safe_pyomo_value(model.pv.total_generation)
    results['Total_GenWind'] = safe_pyomo_value(model.wind.total_generation)
    results['Total_GenS'] = {j: sum(safe_pyomo_value(model.storage.PD[h, j]) for h in model.h) for j in model.storage.j}

    results['SolarPVGen'] = {h: safe_pyomo_value(model.pv.generation[h]) for h in model.h}
    results['WindGen'] = {h: safe_pyomo_value(model.wind.generation[h]) for h in model.h}
    results['AggThermalGen'] = {h: sum(safe_pyomo_value(model.thermal.generation[h, bu]) for bu in model.thermal.plants_set) for h in model.h}

    results['SolarCapex'] = safe_pyomo_value( model.pv.capex_cost_expr )
    results['WindCapex'] =  safe_pyomo_value( model.wind.capex_cost_expr )
    results['SolarFOM'] = safe_pyomo_value( model.pv.fixed_om_cost_expr )
    results['WindFOM'] =  safe_pyomo_value( model.wind.fixed_om_cost_expr )

    logging.debug("Collecting storage results...")
    storage_tech_list = list(model.storage.j)

    for tech in storage_tech_list:
        results[f'{tech}PowerCapex'] = model.storage.CRF[tech]*(MW_TO_KW*model.storage.data['CostRatio', tech] * model.storage.data['P_Capex', tech]*model.storage.Pcha[tech]
                        + MW_TO_KW*(1 - model.storage.data['CostRatio', tech]) * model.storage.data['P_Capex', tech]*model.storage.Pdis[tech])
        results[f'{tech}EnergyCapex'] = model.storage.CRF[tech]*MW_TO_KW*model.storage.data['E_Capex', tech]*model.storage.Ecap[tech]
        results[f'{tech}FOM'] = MW_TO_KW*model.storage.data['CostRatio', tech] * model.storage.data['FOM', tech]*model.storage.Pcha[tech] \
                        + MW_TO_KW*(1 - model.storage.data['CostRatio', tech]) * model.storage.data['FOM', tech]*model.storage.Pdis[tech]
        results[f'{tech}VOM'] = model.storage.data['VOM', tech] * sum(model.storage.PD[h, tech] for h in model.h)

    results['TotalThermalCapex'] = sum( model.thermal.FCR[bu] * MW_TO_KW * model.thermal.CAPEX_M[bu] * model.thermal.plant_installed_capacity[bu] for bu in model.thermal.plants_set )
    results['ThermalFuel'] = sum( (model.thermal.fuel_price[bu] * model.thermal.heat_rate[bu]) * sum(model.thermal.generation[h, bu] for h in model.h) for bu in model.thermal.plants_set )
    results['ThermalFOM'] = safe_pyomo_value( model.thermal.fixed_om_cost_expr )
    results['ThermalVOM'] = sum( model.thermal.VOM_M[bu] * sum(model.thermal.generation[h, bu] for h in model.h) for bu in model.thermal.plants_set )

    return results





def configure_solver(solver_config_dict:dict):
    """
    Configures and returns a Pyomo solver instance with specified options.
    
    This function initializes a solver from Pyomo's SolverFactory, applies user-specified
    options (e.g., MIP gap tolerance, time limits), and validates solver availability.
    It handles both local executable solvers (CBC) and direct API solvers (Xpress, HiGHS).
    
    Args:
        solver_config_dict (dict): Dictionary containing solver configuration with keys:
            - 'solver_name' (str): Solver identifier ('cbc', 'xpress_direct', 'appsi_highs', etc.)
            - 'executable_path' (str, optional): Path to solver executable (for CBC)
            - 'options' (dict, optional): Solver-specific options (e.g., {'mip_rel_gap': 0.001})
    
    Returns:
        SolverFactory: Configured Pyomo solver instance ready to solve optimization problems.
    
    Raises:
        RuntimeError: If the specified solver is not available on the system.
    
    Examples:
        >>> config = get_default_solver_config_dict('cbc')
        >>> solver = configure_solver(config)
        >>> result = solver.solve(model)
    """

    
    if solver_config_dict["solver_name"]=="cbc": #or solver_config_dict["solver_name"]=="xpress_direct":
        solver = SolverFactory(solver_config_dict["solver_name"],
                               executable=solver_config_dict["executable_path"]) if solver_config_dict["executable_path"] else SolverFactory(solver_config_dict["solver_name"])
        
    else:
        solver = SolverFactory(solver_config_dict["solver_name"])

    if not solver.available():
        raise RuntimeError(f"Solver '{solver_config_dict['solver_name']}' is not available on this system.")

    # Apply solver-specific options
    if solver_config_dict["options"]:
        for key, value in solver_config_dict["options"].items():
            solver.options[key] = value

    return solver

def get_default_solver_config_dict(solver_name="cbc", executable_path=".\\Solver\\bin\\cbc.exe"):
    """
    Returns a default solver configuration dictionary with standard settings.
    
    This convenience function provides pre-configured solver settings for common solvers
    used in SDOM. It includes reasonable default options for MIP gap tolerance, logging,
    and solution loading behavior.
    
    Args:
        solver_name (str, optional): Name of the solver to configure. Supported values:
            - 'cbc': Open-source COIN-OR Branch and Cut solver (default)
            - 'xpress': FICO Xpress commercial solver
            - 'highs': Open-source HiGHS solver
            Defaults to 'cbc'.
        executable_path (str, optional): Path to the CBC solver executable. Only used
            when solver_name='cbc'. Defaults to '.\\Solver\\bin\\cbc.exe'.
    
    Returns:
        dict: Solver configuration dictionary with keys:
            - 'solver_name' (str): Formatted solver name for SolverFactory
            - 'executable_path' (str): Path to executable (CBC only)
            - 'options' (dict): Solver options (MIP gap, etc.)
            - 'solve_keywords' (dict): Arguments for solver.solve() call
    
    Examples:
        >>> config = get_default_solver_config_dict('cbc')
        >>> config['options']['mip_rel_gap']
        0.002
        >>> solver = configure_solver(config)
    
    Notes:
        Default MIP gap is 0.2% (0.002). Adjust via config['options']['mip_rel_gap']
        for different solution quality/speed tradeoffs.
    """
    solver_dict = {
        "solver_name": "appsi_" + solver_name,
        "options":{
            #"loglevel": 3,
            "mip_rel_gap": 0.002,
            #"keepfiles": True,
            #"logfile": "solver_log.txt", # The filename used to store output for shell solvers
            },
        "solve_keywords":{
            "tee": True, #If true solver output is printed both to the standard output as well as saved to the log file.
            "load_solutions": True, #If True (the default), then solution values are automically transfered to Var objects on the model
            "report_timing": True, #If True (the default), then timing information is reported
            "logfile": "solver_log.txt", # The filename used to store output for shell solvers
            #"solnfile": "./results_pyomo/solver_soln.txt", # The filename used to store the solution for shell solvers
            "timelimit": None, # The number of seconds that a shell solver is run before it is terminated. (default is None)
            },  
    }
    
    if solver_name == "cbc":
        solver_dict["solver_name"] = solver_name
        solver_dict["executable_path"] = executable_path
    elif solver_name == "xpress":
        solver_dict["solver_name"] = "xpress_direct"
        #solver_dict = {"solver_name": "xpress",}
        #solver_dict["executable_path"] = executable_path

    return solver_dict


# Run solver function
def run_solver(model, solver_config_dict:dict):
    """
    Solves the optimization model using a configured solver.
    
    Executes the optimization, handles solution status checking, collects results
    if optimal, and logs infeasible constraints if the solve fails. Supports multiple
    solver configurations through the solver_config_dict parameter.
    
    Args:
        model (ConcreteModel): The Pyomo optimization model to solve. Must be fully
            initialized with all sets, parameters, variables, objective, and constraints.
        solver_config_dict (dict): Solver configuration dictionary containing:
            - 'solver_name' (str): Solver identifier ('cbc', 'xpress_direct', 'appsi_highs')
            - 'executable_path' (str, optional): Path to solver executable (CBC)
            - 'options' (dict): Solver options like {'mip_rel_gap': 0.002}
            - 'solve_keywords' (dict): Arguments for solver.solve() including:
                - 'tee' (bool): Print solver output to console
                - 'load_solutions' (bool): Load solution into model variables
                - 'timelimit' (int): Maximum solve time in seconds
                - 'report_timing' (bool): Report solve timing statistics
                - 'keepfiles' (bool): Keep intermediate solver files for debugging
    
    Returns:
        tuple: A 3-element tuple containing:
            - results_over_runs (list): List with one dict of collected results (includes
              'GenMix_Target', installed capacities, generation totals, costs). Empty if
              solve failed.
            - best_result (dict or None): Same as results_over_runs[0] if optimal, else None
            - result (SolverResults): Pyomo solver results object with status, termination
              condition, solve time, and objective value
    
    Examples:
        >>> model = initialize_model(data)
        >>> config = get_default_solver_config_dict('cbc')
        >>> results_list, best, solver_result = run_solver(model, config)
        >>> if best is not None:
        ...     print(f"Optimal cost: ${best['Total_Cost']:,.0f}")
        Optimal cost: $4,523,891,234
        
        >>> # Use Xpress with custom gap
        >>> xpress_config = get_default_solver_config_dict('xpress')
        >>> xpress_config['options']['mip_rel_gap'] = 0.001  # 0.1% gap
        >>> results_list, best, solver_result = run_solver(model, xpress_config)
    
    Raises:
        Logs warning if solver doesn't find optimal solution and logs infeasible constraints.
    
    Notes:
        - For CBC, typical solve times: 1-30 minutes for 8760-hour problems
        - If termination_condition != optimal, check solver log for infeasibilities
        - GenMix_Target parameter must exist on model (VRE policy constraint)
    """

    logging.info("Starting to solve SDOM model...")
    solver = configure_solver(solver_config_dict)
    results_over_runs = []
    best_result = None
    best_objective_value = float('inf')

    target_value = float(model.GenMix_Target.value)
    
    logging.info(f"Running optimization for GenMix_Target = {target_value:.2f}")
    result = solver.solve(model, 
                          tee = solver_config_dict["solve_keywords"].get("tee", True),
                          load_solutions = solver_config_dict["solve_keywords"].get("load_solutions", True),
                          #logfile = solver_config_dict["solve_keywords"].get("logfile", "solver_log.txt"),
                          timelimit = solver_config_dict["solve_keywords"].get("timelimit", None),
                          report_timing = solver_config_dict["solve_keywords"].get("report_timing", True),
                          keepfiles = solver_config_dict["solve_keywords"].get("keepfiles", True),
                          #logfile='solver_log.txt'
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
