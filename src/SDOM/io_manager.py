import logging
import pandas as pd
import os
import csv

from pyomo.environ import sqrt

from .common.utilities import safe_pyomo_value, check_file_exists, compare_lists, concatenate_dataframes, get_dict_string_void_list_from_keys_in_list
from .constants import INPUT_CSV_NAMES, MW_TO_KW, VALID_HYDRO_FORMULATIONS_TO_BUDGET_MAP, VALID_IMPORTS_EXPORTS_FORMULATIONS_TO_DESCRIPTION_MAP


def check_formulation( formulation:str, valid_formulations ):
    """
    Validates that a formulation string is in the list of valid formulations.
    
    Args:
        formulation (str): The formulation name to validate.
        valid_formulations (list or dict): Collection of valid formulation options.
    
    Raises:
        ValueError: If the formulation is not found in valid_formulations.
    
    Returns:
        None
    """
    if formulation not in valid_formulations:
        raise ValueError(f"Invalid formulation '{formulation}' selected by the user in file 'formulations.csv'. Valid options are: {valid_formulations}")
    return

def get_formulation(data:dict, component:str ='hydro'):
    """
    Retrieves the formulation type for a specified component from the loaded data.
    
    Args:
        data (dict): Dictionary containing model input data, including the 'formulations'
            DataFrame that specifies which formulation to use for each component.
        component (str, optional): Name of the component (e.g., 'hydro', 'imports', 
            'exports'). Case-insensitive. Defaults to 'hydro'.
    
    Returns:
        str: The formulation name for the specified component (e.g., 'MonthlyBudgetFormulation',
            'RunOfRiverFormulation', 'CapacityPriceNetLoadFormulation').
    
    Examples:
        >>> formulation = get_formulation(data, component='hydro')
        >>> print(formulation)
        'MonthlyBudgetFormulation'
    """
    formulations = data["formulations"]
    return formulations.loc[ formulations["Component"].str.lower() == component.lower() ]["Formulation"].iloc[0]


def load_data( input_data_dir:str = '.\\Data\\' ):
    """
    Loads all required SDOM input datasets from CSV files in the specified directory.
    
    This is the primary data loading function for SDOM. It reads technology specifications,
    time series data, cost parameters, and system scalars from CSV files. The function
    intelligently loads additional data based on formulation choices (e.g., hydro budget
    constraints, imports/exports) specified in the formulations.csv file.
    
    Loading Process:
        1. Loads formulations.csv to determine model configuration
        2. Loads core technology data (VRE, thermal, storage, hydro, nuclear)
        3. Loads time series data (capacity factors, load, generation profiles)
        4. Conditionally loads formulation-specific data (hydro min/max, imports/exports)
        5. Validates consistency between related datasets (e.g., CF vs CAPEX plant lists)
    
    Args:
        input_data_dir (str, optional): Path to directory containing input CSV files.
            Must contain all required CSV files listed in constants.INPUT_CSV_NAMES.
            Defaults to '.\\Data\\'.
    
    Returns:
        dict: Dictionary containing all loaded input data with the following keys:
        
        **Always Present:**
            - "formulations" (pd.DataFrame): Model formulation specifications by component
            - "solar_plants" (list): Solar plant site identifiers (extracted from CF columns)
            - "wind_plants" (list): Wind plant site identifiers (extracted from CF columns)
            - "load_data" (pd.DataFrame): Hourly electricity demand time series (MW)
            - "nuclear_data" (pd.DataFrame): Hourly nuclear generation profile (MW)
            - "large_hydro_data" (pd.DataFrame): Hourly hydropower generation/budget (MW)
            - "other_renewables_data" (pd.DataFrame): Hourly other renewables profile (MW)
            - "cf_solar" (pd.DataFrame): Solar PV capacity factors by site and hour (0-1)
            - "cf_wind" (pd.DataFrame): Wind capacity factors by site and hour (0-1)
            - "cap_solar" (pd.DataFrame): Solar site characteristics (CAPEX, transmission cost)
            - "cap_wind" (pd.DataFrame): Wind site characteristics (CAPEX, transmission cost)
            - "storage_data" (pd.DataFrame): Storage technology parameters (costs, efficiency, lifetime)
            - "STORAGE_SET_J_TECHS" (list): All storage technology names (Li-Ion, CAES, PHS, H2)
            - "STORAGE_SET_B_TECHS" (list): Coupled storage technologies (power=energy capacity)
            - "thermal_data" (pd.DataFrame): Thermal generator parameters by balancing unit
            - "scalars" (pd.DataFrame): System-level scalar parameters (discount rate, etc.)
        
        **Conditionally Loaded (based on formulations.csv):**
            - "large_hydro_max" (pd.DataFrame): Hourly max hydro generation (if budget formulation)
            - "large_hydro_min" (pd.DataFrame): Hourly min hydro generation (if budget formulation)
            - "cap_imports" (pd.DataFrame): Hourly import capacity limits (if imports enabled)
            - "price_imports" (pd.DataFrame): Hourly import prices (if imports enabled)
            - "cap_exports" (pd.DataFrame): Hourly export capacity limits (if exports enabled)
            - "price_exports" (pd.DataFrame): Hourly export prices (if exports enabled)
    
    Raises:
        FileNotFoundError: If required CSV files are missing from input_data_dir.
        ValueError: If formulation in formulations.csv is invalid.
        ValueError: If plant ID lists are inconsistent between CF and CAPEX files.
    
    Side Effects:
        - Logs INFO and DEBUG messages about data loading progress
        - Logs warnings if optional files are missing
        - Validates formulation choices and raises errors for invalid configurations
    
    Examples:
        >>> # Load data from default directory
        >>> data = load_data()
        >>> print(data.keys())
        dict_keys(['formulations', 'solar_plants', 'wind_plants', 'load_data', ...])
        
        >>> # Load from custom directory
        >>> data = load_data(input_data_dir='./Data/high_renewables_case/')
        >>> print(f"Loaded {len(data['solar_plants'])} solar sites")
        Loaded 152 solar sites
        
        >>> # Access loaded data
        >>> cf_solar = data['cf_solar']
        >>> hourly_load = data['load_data']
        >>> storage_params = data['storage_data']
    
    Notes:
        - All numeric data is automatically rounded to 5 decimal places for numerical stability
        - Plant IDs (sc_gid) are converted to strings for consistent indexing
        - Function validates that plant lists match between CF and CAPEX datasets
        - Missing optional files (imports/exports) are handled gracefully based on formulations
        - This function should be called once at the start of model initialization
        - Total loading time: ~1-5 seconds depending on number of sites and file sizes
    """
    logging.info("Loading SDOM input data...")
    
    logging.debug("- Trying to load formulations data...")
    input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["formulations"], "CSV file to specify the formulations for different components")
    if input_file_path != "":
        formulations = pd.read_csv( input_file_path )
    
    logging.debug("- Trying to load VRE data...")
    # THE SET CSV FILES WERE REMOVED
    # input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["solar_plants"])
    # if check_file_exists(input_file_path, "solar plants ids"):
    #     solar_plants = pd.read_csv( input_file_path, header=None )[0].tolist()
    
    # input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["wind_plants"])
    # if check_file_exists(input_file_path, "wind plants ids"):
    #     wind_plants = pd.read_csv( input_file_path, header=None )[0].tolist()


    input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["cf_solar"], "Capacity factors for pv solar")
    if input_file_path != "":
        cf_solar = pd.read_csv( input_file_path ).round(5)
        cf_solar.columns = cf_solar.columns.astype(str)
        solar_plants = cf_solar.columns[1:].tolist()
        logging.debug( f"-- It were loaded a total of {len( solar_plants )} solar plants profiles." )
    
    input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["cf_wind"], "Capacity factors for wind")
    if input_file_path != "":
        cf_wind = pd.read_csv( input_file_path ).round(5)
        cf_wind.columns = cf_wind.columns.astype(str)
        wind_plants = cf_wind.columns[1:].tolist()
        logging.debug( f"-- It were loaded a total of {len( wind_plants )} wind plants profiles." )

    input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["cap_solar"], "Capex information for solar")
    if input_file_path != "":
        cap_solar = pd.read_csv( input_file_path ).round(5)
        cap_solar['sc_gid'] = cap_solar['sc_gid'].astype(str)
        solar_plants_capex = cap_solar['sc_gid'].tolist()
        compare_lists(solar_plants, solar_plants_capex, text_comp="solar plants", list_names=["CF", "Capex"])

    input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["cap_wind"], "Capex information for wind")
    if input_file_path != "":
        cap_wind = pd.read_csv( input_file_path ).round(5)
        cap_wind['sc_gid'] = cap_wind['sc_gid'].astype(str)
        wind_plants_capex = cap_wind['sc_gid'].tolist()
        compare_lists(wind_plants, wind_plants_capex, text_comp="wind plants", list_names=["CF", "Capex"])

    logging.debug("- Trying to load demand data...")
    input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["load_data"], "load data")
    if input_file_path != "":
        load_data = pd.read_csv( input_file_path ).round(5)

    logging.debug("- Trying to load nuclear data...")
    input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["nuclear_data"], "nuclear data")
    if input_file_path != "":
        nuclear_data = pd.read_csv( input_file_path ).round(5)

    logging.debug("- Trying to load large hydro data...")
    input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["large_hydro_data"], "large hydro data")
    if input_file_path != "":
        large_hydro_data = pd.read_csv( input_file_path ).round(5)

    logging.debug("- Trying to load other renewables data...")
    input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["other_renewables_data"], "other renewables data")
    if input_file_path != "":
        other_renewables_data = pd.read_csv( input_file_path ).round(5)

    logging.debug("- Trying to load storage data...")
    input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["storage_data"], "Storage data")
    if input_file_path != "":
        storage_data = pd.read_csv( input_file_path, index_col=0 ).round(5)
        storage_set_j_techs = storage_data.columns[0:].astype(str).tolist()
        storage_set_b_techs = storage_data.columns[ storage_data.loc["Coupled"] == 1 ].astype( str ).tolist()

    logging.debug("- Trying to load thermal generation data...")
    input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["thermal_data"], "thermal data")
    if input_file_path != "":
        thermal_data = pd.read_csv( input_file_path ).round(5)

    logging.debug("- Trying to load scalars data...")
    input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["scalars"], "scalars")
    if input_file_path != "":
        scalars = pd.read_csv( input_file_path, index_col="Parameter" )
    #os.chdir('../')

    data_dict =  {
            "formulations": formulations,
            "solar_plants": solar_plants,
            "wind_plants": wind_plants,
            "load_data": load_data,
            "nuclear_data": nuclear_data,
            "large_hydro_data": large_hydro_data,
            "other_renewables_data": other_renewables_data,
            "cf_solar": cf_solar,
            "cf_wind": cf_wind,
            "cap_solar": cap_solar,
            "cap_wind": cap_wind,
            "storage_data": storage_data,
            "STORAGE_SET_J_TECHS": storage_set_j_techs,
            "STORAGE_SET_B_TECHS": storage_set_b_techs,
            "thermal_data": thermal_data,
            "scalars": scalars,
        }

    hydro_formulation = get_formulation(data_dict, component='hydro')
    check_formulation( hydro_formulation, VALID_HYDRO_FORMULATIONS_TO_BUDGET_MAP.keys() )

    if not (hydro_formulation == "RunOfRiverFormulation"):
        logging.debug("- Hydro was set to MonthlyBudgetFormulation. Trying to load large hydro max/min data...")
        
        input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["large_hydro_max"], "large hydro Maximum  capacity data")
        if input_file_path != "":
            large_hydro_max = pd.read_csv( input_file_path ).round(5)
        
        input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["large_hydro_min"], "large hydro Minimum capacity data")
        if input_file_path != "":
            large_hydro_min = pd.read_csv( input_file_path ).round(5)
        data_dict["large_hydro_max"] = large_hydro_max
        data_dict["large_hydro_min"] = large_hydro_min
    

    logging.debug("- Trying to load imports data...")    
    imports_formulation = get_formulation(data_dict, component='imports')
    check_formulation( imports_formulation, VALID_IMPORTS_EXPORTS_FORMULATIONS_TO_DESCRIPTION_MAP.keys() )
    if (imports_formulation == "CapacityPriceNetLoadFormulation"):
        logging.debug("- Imports was set to CapacityPriceNetLoadFormulation. Trying to load capacity and price...")
        
        input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["cap_imports"], "Imports hourly upper bound capacity data")
        if input_file_path != "":
            cap_imports = pd.read_csv( input_file_path ).round(5)

        input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["price_imports"], "Imports hourly price data")
        if input_file_path != "":
            price_imports = pd.read_csv( input_file_path ).round(5)
        data_dict["cap_imports"] = cap_imports
        data_dict["price_imports"] = price_imports

    
    logging.debug("- Trying to load exports data...")
    exports_formulation = get_formulation(data_dict, component='exports')
    check_formulation( exports_formulation, VALID_IMPORTS_EXPORTS_FORMULATIONS_TO_DESCRIPTION_MAP.keys() )
    if (exports_formulation == "CapacityPriceNetLoadFormulation"):
        logging.debug("- Exports was set to CapacityPriceNetLoadFormulation. Trying to load capacity and price...")
        
        input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["cap_exports"], "Exports hourly upper bound capacity data")
        if input_file_path != "":
            cap_exports = pd.read_csv( input_file_path ).round(5)

        input_file_path = check_file_exists(input_data_dir, INPUT_CSV_NAMES["price_exports"], "Exports hourly price data")
        if input_file_path != "":
            price_exports = pd.read_csv( input_file_path ).round(5)
        data_dict["cap_exports"] = cap_exports
        data_dict["price_exports"] = price_exports
    
    return data_dict
    



# ---------------------------------------------------------------------------------
# Export results to CSV files
# ---------------------------------------------------------------------------------

def export_results( model, case, output_dir = './results_pyomo/' ):
    """
    Exports optimization results from a Pyomo model to CSV files.
    
    Extracts generation, storage, and summary results from the solved Pyomo model,
    organizes them into pandas DataFrames, and writes them to CSV files for post-processing
    analysis. Three files are generated: hourly generation profiles, hourly storage operation,
    and system-level summary statistics.
    
    Args:
        model (pyomo.environ.ConcreteModel): The solved Pyomo model instance containing
            optimized variables and computed results.
        case (str or int): Unique identifier for the simulation case or scenario. Used to
            distinguish output files from different runs (e.g., 'base_case', 'high_load', 1, 2).
        output_dir (str, optional): Directory path where CSV files will be saved. Directory
            is created if it doesn't exist. Defaults to './results_pyomo/'.
    
    Returns:
        None
    
    Side Effects:
        Creates three CSV files in output_dir:
        
        1. **OutputGeneration_{case}.csv**: Hourly generation and curtailment (8760+ rows)
           - Columns: Scenario, Hour, Solar PV Generation (MW), Solar PV Curtailment (MW),
             Wind Generation (MW), Wind Curtailment (MW), Thermal Generation (MW),
             Hydro Generation (MW), Nuclear Generation (MW), Other Renewables (MW),
             Imports (MW), Exports (MW), Storage Charge/Discharge (MW), Load (MW)
        
        2. **OutputStorage_{case}.csv**: Hourly storage operation by technology
           - Columns: Hour, Technology, Charging power (MW), Discharging power (MW),
             State of charge (MWh)
           - Includes all storage technologies: Li-Ion, CAES, PHS, H2
        
        3. **OutputSummary_{case}.csv**: System-level summary statistics
           - Includes: Total Cost, Total Capacity by Technology, Annual Generation,
             Annual Demand, Total CAPEX, Total OPEX, Capacity Factor, Curtailment Rate,
             Import/Export volumes, Storage metrics
    
    Examples:
        >>> model = optimize(input_dir='./Data/base_case/')
        >>> export_results(model, case='base_case_2025', output_dir='./results/')
        # Creates: results/OutputGeneration_base_case_2025.csv, etc.
        
        >>> for i, scenario in enumerate(['low', 'mid', 'high']):
        ...     model = optimize(input_dir=f'./Data/{scenario}/')
        ...     export_results(model, case=i, output_dir='./results/')
        # Creates: results/OutputGeneration_0.csv, OutputGeneration_1.csv, etc.
    
    Notes:
        - The function uses safe_pyomo_value() to handle undefined variables gracefully
        - Results are only written if all required data is available (no None values)
        - Assumes standard SDOM model structure with expected variable names
        - Technology availability (nuclear, imports, exports) is checked before extraction
    """

    logging.info("Exporting SDOM results...")
    os.makedirs(output_dir, exist_ok=True)

    # Initialize results dictionaries column: [values]
    logging.debug("--Initializing results dictionaries...")
    gen_results = {'Scenario':[],'Hour': [], 'Solar PV Generation (MW)': [], 'Solar PV Curtailment (MW)': [],
                   'Wind Generation (MW)': [], 'Wind Curtailment (MW)': [],
                   'All Thermal Generation (MW)': [], 'Hydro Generation (MW)': [],
                   'Nuclear Generation (MW)': [], 'Other Renewables Generation (MW)': [],
                   'Imports (MW)': [],
                   'Storage Charge/Discharge (MW)': [],
                   'Exports (MW)': [], "Load (MW)": []}

    storage_results = {'Hour': [], 'Technology': [], 'Charging power (MW)': [],
                       'Discharging power (MW)': [], 'State of charge (MWh)': []}

    # Extract generation results
#    for run in range(num_runs):
    logging.debug("--Extracting generation results...")
    for h in model.h:
        solar_gen = safe_pyomo_value(model.pv.generation[h])
        solar_curt = safe_pyomo_value(model.pv.curtailment[h])
        wind_gen = safe_pyomo_value(model.wind.generation[h])
        wind_curt = safe_pyomo_value(model.wind.curtailment[h])
        gas_cc_gen = sum( safe_pyomo_value(model.thermal.generation[h, bu]) for bu in model.thermal.plants_set )
        hydro = safe_pyomo_value(model.hydro.generation[h])
        nuclear = safe_pyomo_value(model.nuclear.alpha * model.nuclear.ts_parameter[h]) if hasattr(model.nuclear, 'alpha') else 0
        other_renewables = safe_pyomo_value(model.other_renewables.alpha * model.other_renewables.ts_parameter[h]) if hasattr(model.other_renewables, 'alpha') else 0
        imports = safe_pyomo_value(model.imports.variable[h]) if hasattr(model.imports, 'variable') else 0
        exports = safe_pyomo_value(model.exports.variable[h]) if hasattr(model.exports, 'variable') else 0
        load = safe_pyomo_value(model.demand.ts_parameter[h]) if hasattr(model.demand, 'ts_parameter') else 0
         # Only append results if all values are valid (not None)
        if None not in [solar_gen, solar_curt, wind_gen, wind_curt, gas_cc_gen, hydro, imports, exports, load]:
#            gen_results['Scenario'].append(run)
            gen_results['Hour'].append(h)
            gen_results['Solar PV Generation (MW)'].append(solar_gen)
            gen_results['Solar PV Curtailment (MW)'].append(solar_curt)
            gen_results['Wind Generation (MW)'].append(wind_gen)
            gen_results['Wind Curtailment (MW)'].append(wind_curt)
            gen_results['All Thermal Generation (MW)'].append(gas_cc_gen)
            gen_results['Hydro Generation (MW)'].append(hydro)
            gen_results['Nuclear Generation (MW)'].append(nuclear)
            gen_results['Other Renewables Generation (MW)'].append(other_renewables)
            gen_results['Imports (MW)'].append(imports)

            power_to_storage = sum(safe_pyomo_value(model.storage.PC[h, j]) or 0 for j in model.storage.j) - sum(safe_pyomo_value(model.storage.PD[h, j]) or 0 for j in model.storage.j)
            gen_results['Storage Charge/Discharge (MW)'].append(power_to_storage)
            gen_results['Exports (MW)'].append(exports)
            gen_results['Load (MW)'].append(load)
        gen_results['Scenario'].append(case)

    


    # Extract storage results
    logging.debug("--Extracting storage results...")
    for h in model.h:
        for j in model.storage.j:
            charge_power = safe_pyomo_value(model.storage.PC[h, j])
            discharge_power = safe_pyomo_value(model.storage.PD[h, j])
            soc = safe_pyomo_value(model.storage.SOC[h, j])
            if None not in [charge_power, discharge_power, soc]:
                storage_results['Hour'].append(h)
                storage_results['Technology'].append(j)
                storage_results['Charging power (MW)'].append(charge_power)
                storage_results['Discharging power (MW)'].append(discharge_power)
                storage_results['State of charge (MWh)'].append(soc)



    # Summary results (total capacities and costs)
    ## Total cost
    logging.debug("--Extracting summary results...")
    total_cost = pd.DataFrame.from_dict({'Total cost':[None, 1,safe_pyomo_value(model.Obj()), '$US']}, orient='index',
                                        columns=['Technology','Run','Optimal Value', 'Unit'])
    total_cost = total_cost.reset_index(names='Metric')
    summary_results = total_cost

    ## Total capacity
    cap = {}
    cap['Thermal'] = sum( safe_pyomo_value( model.thermal.plant_installed_capacity[bu] ) for bu in model.thermal.plants_set )
    cap['Solar PV'] = safe_pyomo_value( model.pv.total_installed_capacity ) #TODO REVIEW THIS
    cap['Wind'] = safe_pyomo_value( model.wind.total_installed_capacity )
    cap['All'] = cap['Thermal'] + cap['Solar PV'] + cap['Wind']

    summary_results = concatenate_dataframes( summary_results, cap, run=1, unit='MW', metric='Capacity' )
    
    ## Charge power capacity
    storage_tech_list = list(model.storage.j)
    charge = {}
    sum_all = 0.0
    for tech in storage_tech_list:
        charge[tech] = safe_pyomo_value(model.storage.Pcha[tech])
        sum_all += charge[tech]
    charge['All'] = sum_all

    summary_results = concatenate_dataframes( summary_results, charge, run=1, unit='MW', metric='Charge power capacity' )

    ## Discharge power capacity
    dcharge = {}
    sum_all = 0.0

    for tech in storage_tech_list:
        dcharge[tech] = safe_pyomo_value(model.storage.Pdis[tech])
        sum_all += dcharge[tech]
    dcharge['All'] = sum_all

    summary_results = concatenate_dataframes( summary_results, dcharge, run=1, unit='MW', metric='Discharge power capacity' )

    ## Average power capacity
    avgpocap = {}
    sum_all = 0.0
    for tech in storage_tech_list:
        avgpocap[tech] = (charge[tech] + dcharge[tech]) / 2
        sum_all += avgpocap[tech]
    avgpocap['All'] = sum_all

    summary_results = concatenate_dataframes( summary_results, avgpocap, run=1, unit='MW', metric='Average power capacity' )

    ## Energy capacity
    encap = {}
    sum_all = 0.0
    for tech in storage_tech_list:
        encap[tech] = safe_pyomo_value(model.storage.Ecap[tech])
        sum_all += encap[tech]
    encap['All'] = sum_all

    summary_results = concatenate_dataframes( summary_results, encap, run=1, unit='MWh', metric='Energy capacity' )

    ## Discharge duration
    dis_dur = {}
    for tech in storage_tech_list:
        dis_dur[tech] = safe_pyomo_value(sqrt(model.storage.data['Eff', tech]) * model.storage.Ecap[tech] / (model.storage.Pdis[tech] + 1e-15))

    summary_results = concatenate_dataframes( summary_results, dis_dur, run=1, unit='h', metric='Duration' )

    ## Generation
    gen = {}
    gen['Thermal'] =  safe_pyomo_value( model.thermal.total_generation )
    gen['Solar PV'] = safe_pyomo_value(model.pv.total_generation)
    gen['Wind'] = safe_pyomo_value(model.wind.total_generation)
    gen['Other renewables'] = safe_pyomo_value(sum(model.other_renewables.ts_parameter[h] for h in model.h))
    gen['Hydro'] = safe_pyomo_value(sum(model.hydro.generation[h] for h in model.h))
    gen['Nuclear'] = safe_pyomo_value(sum(model.nuclear.ts_parameter[h] for h in model.h))

    # Storage energy discharging
    sum_all = 0.0
    storage_tech_list = list(model.storage.j)
    for tech in storage_tech_list:
        gen[tech] = safe_pyomo_value( sum( model.storage.PD[h, tech] for h in model.h ) )
        sum_all += gen[tech]

    gen['All'] = gen['Thermal'] + gen['Solar PV'] + gen['Wind'] + gen['Other renewables'] + gen['Hydro'] + \
                gen['Nuclear'] + sum_all

    summary_results = concatenate_dataframes( summary_results, gen, run=1, unit='MWh', metric='Total generation' )
    
    imp_exp = {}
    imp_exp['Imports'] = safe_pyomo_value(sum(model.imports.variable[h] for h in model.h)) if hasattr(model.imports, 'variable') else 0
    imp_exp['Exports'] = safe_pyomo_value(sum(model.exports.variable[h] for h in model.h)) if hasattr(model.exports, 'variable') else 0
    summary_results = concatenate_dataframes( summary_results, imp_exp, run=1, unit='MWh', metric='Total Imports/Exports' )

    ## Storage energy discharging
    sum_all = 0.0
    stodisch = {}
    for tech in storage_tech_list:
        stodisch[tech] = safe_pyomo_value( sum( model.storage.PD[h, tech] for h in model.h ) )
        sum_all += stodisch[tech]
    stodisch['All'] = sum_all

    summary_results = concatenate_dataframes( summary_results, stodisch, run=1, unit='MWh', metric='Storage energy discharging' )
    

    ## Demand
    dem = {}
    dem['demand'] = sum(model.demand.ts_parameter[h] for h in model.h)

    summary_results = concatenate_dataframes( summary_results, dem, run=1, unit='MWh', metric='Total demand' )
    
    ## Storage energy charging
    sum_all = 0.0
    stoch = {}
    for tech in storage_tech_list:
        stoch[tech] = safe_pyomo_value( sum( model.storage.PC[h, tech] for h in model.h ) )
        sum_all += stoch[tech]
    stoch['All'] = sum_all

    summary_results = concatenate_dataframes( summary_results, stoch, run=1, unit='MWh', metric='Storage energy charging' )
    
    
    ## CAPEX
    capex = {}
    capex['Solar PV'] = safe_pyomo_value( model.pv.capex_cost_expr )
    capex['Wind'] = safe_pyomo_value( model.wind.capex_cost_expr )
    capex['Thermal'] = safe_pyomo_value( model.thermal.capex_cost_expr )
    capex['All'] = capex['Solar PV'] + capex['Wind'] + capex['Thermal']

    summary_results = concatenate_dataframes( summary_results, capex, run=1, unit='$US', metric='CAPEX' )
    
    ## Power CAPEX
    pcapex = {}
    sum_all = 0.0
    for tech in storage_tech_list:
        pcapex[tech] = safe_pyomo_value(model.storage.power_capex_cost_expr[tech])
        sum_all += pcapex[tech]
    
    pcapex['All'] = sum_all

    summary_results = concatenate_dataframes( summary_results, pcapex, run=1, unit='$US', metric='Power-CAPEX' )

    ## Energy CAPEX and Total CAPEX
    ecapex = {}
    tcapex = {}
    sum_all = 0.0
    sum_all_t = 0.0
    for tech in storage_tech_list:
        ecapex[tech] = safe_pyomo_value(model.storage.energy_capex_cost_expr[tech])
        sum_all += ecapex[tech]
        tcapex[tech] = pcapex[tech] + ecapex[tech]
        sum_all_t += tcapex[tech]
    ecapex['All'] = sum_all
    tcapex['All'] = sum_all_t

    summary_results = concatenate_dataframes( summary_results, ecapex, run=1, unit='$US', metric='Energy-CAPEX' )
    summary_results = concatenate_dataframes( summary_results, tcapex, run=1, unit='$US', metric='Total-CAPEX' )

    ## FOM
    fom = {}
    sum_all = 0.0
    fom['Thermal'] = safe_pyomo_value( model.thermal.fixed_om_cost_expr )
    fom['Solar PV'] = safe_pyomo_value( model.pv.fixed_om_cost_expr )
    fom['Wind'] = safe_pyomo_value( model.wind.fixed_om_cost_expr )
     
    for tech in storage_tech_list:
        fom[tech] = safe_pyomo_value(MW_TO_KW*model.storage.data['CostRatio', tech] * model.storage.data['FOM', tech]*model.storage.Pcha[tech]
                            + MW_TO_KW*(1 - model.storage.data['CostRatio', tech]) * model.storage.data['FOM', tech]*model.storage.Pdis[tech])
        sum_all += fom[tech]

    fom['All'] = fom['Thermal'] + fom['Solar PV'] + fom['Wind'] + sum_all 

    summary_results = concatenate_dataframes( summary_results, fom, run=1, unit='$US', metric='FOM' )
    
    ## VOM
    vom = {}
    sum_all = 0.0
    #TODO review this calculation
    vom['Thermal'] = safe_pyomo_value( model.thermal.total_vom_cost_expr )

    for tech in storage_tech_list:
        vom[tech] = safe_pyomo_value(model.storage.data['VOM', tech] * sum(model.storage.PD[h, tech] for h in model.h))
        sum_all += vom[tech]
    vom['All'] = vom['Thermal'] + sum_all

    summary_results = concatenate_dataframes( summary_results, vom, run=1, unit='$US', metric='VOM' )

    fuel_cost = {}
    fuel_cost['Thermal'] = safe_pyomo_value( model.thermal.total_fuel_cost_expr )
    summary_results = concatenate_dataframes( summary_results, fuel_cost, run=1, unit='$US', metric='Fuel-Cost' )
    
    ## OPEX
    opex = {}
    sum_all = 0.0
    opex['Thermal'] = fom['Thermal'] + vom['Thermal']
    opex['Solar PV'] = fom['Solar PV'] 
    opex['Wind'] = fom['Wind']

    for tech in storage_tech_list:
        opex[tech] = fom[tech] + vom[tech]
        sum_all += opex[tech]
    opex['All'] = opex['Thermal'] + opex['Solar PV'] + opex['Wind'] + sum_all

    summary_results = concatenate_dataframes( summary_results, opex, run=1, unit='$US', metric='OPEX' )

    #IMPORTS/EXPORTS COSTS
    cost_revenue = {}
    cost_revenue["Imports Cost"] = safe_pyomo_value( model.imports.total_cost_expr )
    summary_results = concatenate_dataframes( summary_results, cost_revenue, run=1, unit='$US', metric='Cost' )
    cost_revenue = {}
    cost_revenue["Exports Revenue"] = safe_pyomo_value( model.exports.total_cost_expr )
    summary_results = concatenate_dataframes( summary_results, cost_revenue, run=1, unit='$US', metric='Revenue' )
   


    ## Equivalent number of cycles
    cyc = {}
    for tech in storage_tech_list:
        cyc[tech] = safe_pyomo_value(gen[tech] / (model.storage.Ecap[tech] + 1e-15))

    summary_results = concatenate_dataframes( summary_results, cyc, run=1, unit='-', metric='Equivalent number of cycles' )
    

    logging.info("Exporting csv files containing SDOM results...")
    # Save generation results to CSV
    logging.debug("-- Saving generation results to CSV...")
    if gen_results['Hour']:
        with open(output_dir + f'OutputGeneration_{case}.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=gen_results.keys())
            writer.writeheader()
            writer.writerows([dict(zip(gen_results, t))
                             for t in zip(*gen_results.values())])

    # Save storage results to CSV
    logging.debug("-- Saving storage results to CSV...")
    if storage_results['Hour']:
        with open(output_dir + f'OutputStorage_{case}.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=storage_results.keys())
            writer.writeheader()
            writer.writerows([dict(zip(storage_results, t))
                             for t in zip(*storage_results.values())])

    # Save summary results to CSV
    logging.debug("-- Saving summary results to CSV...")
    if len(summary_results) > 0:
        summary_results.to_csv(output_dir + f'OutputSummary_{case}.csv', index=False)



    if len(model.thermal.plants_set) <= 1:
        return
    thermal_gen_columns = ['Hour'] + [str(plant) for plant in model.thermal.plants_set]
    disaggregated_thermal_gen_results = get_dict_string_void_list_from_keys_in_list(thermal_gen_columns)
   
    for h in model.h:
        disaggregated_thermal_gen_results['Hour'].append(h)
        for plant in model.thermal.plants_set:
            disaggregated_thermal_gen_results[plant].append(safe_pyomo_value(model.thermal.generation[h, plant]))

    logging.debug("-- Saving disaggregated thermal generation results to CSV...")
    if disaggregated_thermal_gen_results['Hour']:
        with open(output_dir + f'OutputThermalGeneration_{case}.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=disaggregated_thermal_gen_results.keys())
            writer.writeheader()
            writer.writerows([dict(zip(disaggregated_thermal_gen_results, t))
                             for t in zip(*disaggregated_thermal_gen_results.values())])