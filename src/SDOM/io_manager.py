import logging
import pandas as pd
import os
import csv

from pyomo.environ import sqrt

from .common.utilities import safe_pyomo_value, check_file_exists
from .constants import INPUT_CSV_NAMES, MW_TO_KW


def load_data( input_data_dir = '.\\Data\\' ):
    """
    Loads the required SDOM datasets from CSV files located in the specified input directory.
    Parameters:
        input_data_dir (str): Path to the directory containing the input CSV files. Defaults to '.\\Data\\'.
    Returns:
        dict: A dictionary containing the following keys and their corresponding loaded data:
            - "solar_plants" (list): List of solar plant identifiers.
            - "wind_plants" (list): List of wind plant identifiers.
            - "load_data" (pd.DataFrame): Hourly load data for the year 2050.
            - "nuclear_data" (pd.DataFrame): Hourly nuclear generation data for 2019.
            - "large_hydro_data" (pd.DataFrame): Hourly large hydro generation data for 2019.
            - "other_renewables_data" (pd.DataFrame): Hourly other renewables generation data for 2019.
            - "cf_solar" (pd.DataFrame): Solar capacity factors for 2050.
            - "cf_wind" (pd.DataFrame): Wind capacity factors for 2050.
            - "cap_solar" (pd.DataFrame): Solar plant capacities for 2050.
            - "cap_wind" (pd.DataFrame): Wind plant capacities for 2050.
            - "storage_data" (pd.DataFrame): Storage data for 2050, indexed by the first column.
            - "scalars" (pd.DataFrame): Scalar parameters, indexed by the "Parameter" column.
    Notes:
        - All numeric data is rounded to 5 decimal places.
        - Some columns are explicitly converted to string type for consistency.
    """
    logging.info("Loading SDOM input data...")
    #os.chdir('./Data/.')
    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["solar_plants"])
    if check_file_exists(input_file_path, "solar plants ids"):
        solar_plants = pd.read_csv( input_file_path, header=None )[0].tolist()
    
    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["wind_plants"])
    if check_file_exists(input_file_path, "wind plants ids"):
        wind_plants = pd.read_csv( input_file_path, header=None )[0].tolist()

    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["load_data"])
    if check_file_exists(input_file_path, "load data"):
        load_data = pd.read_csv( input_file_path ).round(5)

    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["nuclear_data"])
    if check_file_exists(input_file_path, "nuclear data"):
        nuclear_data = pd.read_csv( input_file_path ).round(5)

    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["large_hydro_data"])
    if check_file_exists(input_file_path, "large hydro data"):
        large_hydro_data = pd.read_csv( input_file_path ).round(5)

    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["other_renewables_data"])
    if check_file_exists(input_file_path, "other renewables data"):
        other_renewables_data = pd.read_csv( input_file_path ).round(5)
    
    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["cf_solar"])
    if check_file_exists(input_file_path, "Capacity factors for pv solar"):
        cf_solar = pd.read_csv( input_file_path ).round(5)
        cf_solar.columns = cf_solar.columns.astype(str)

    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["cf_wind"])
    if check_file_exists(input_file_path, "Capacity factors for wind"):
        cf_wind = pd.read_csv( input_file_path ).round(5)
        cf_wind.columns = cf_wind.columns.astype(str)
    
    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["cap_solar"])
    if check_file_exists(input_file_path, "Capex information for solar"):
        cap_solar = pd.read_csv( input_file_path ).round(5)
        cap_solar['sc_gid'] = cap_solar['sc_gid'].astype(str)
    
    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["cap_wind"])
    if check_file_exists(input_file_path, "Capex information for wind"):
        cap_wind = pd.read_csv( input_file_path ).round(5)
        cap_wind['sc_gid'] = cap_wind['sc_gid'].astype(str)
    
    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["storage_data"])
    if check_file_exists(input_file_path, "Storage data"):
        storage_data = pd.read_csv( input_file_path, index_col=0 ).round(5)
        storage_set_j_techs = storage_data.columns[0:].astype(str).tolist()
        #storage_set_b_techs = storage_data.columns[ storage_data.loc["Coupled"] == True ].astype( str ).tolist()

    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["scalars"])
    if check_file_exists(input_file_path, "scalars"):
        scalars = pd.read_csv( input_file_path, index_col="Parameter" )
    #os.chdir('../')
    return {
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
        "STORAGE_SET_B_TECHS": [],#storage_set_b_techs,
        "scalars": scalars,
    }
    



# ---------------------------------------------------------------------------------
# Export results to CSV files
# ---------------------------------------------------------------------------------

def export_results( model, case, output_dir = './results_pyomo/' ):
    """
    Exports optimization results from a Pyomo model to CSV files.
    This function extracts generation, storage, and summary results from the provided Pyomo model instance,
    organizes them into dictionaries and pandas DataFrames, and writes them to CSV files in the specified output directory.
    Parameters
    ----------
    model : pyomo.environ.ConcreteModel
        The Pyomo model instance containing the optimization results.
    case : str or int
        Identifier for the current simulation case or scenario. Used in output filenames.
    output_dir : str, optional
        Directory path where the output CSV files will be saved. Defaults to './results_pyomo/'.
    Outputs
    -------
    OutputGeneration_{case}.csv : CSV file
        Contains hourly generation and curtailment results for each technology and scenario.
    OutputStorage_{case}.csv : CSV file
        Contains hourly storage operation results (charging, discharging, state of charge) for each storage technology.
    OutputSummary_{case}.csv : CSV file
        Contains summary metrics including total cost, capacities, generation, demand, CAPEX, OPEX, and other key results.
    Notes
    -----
    - The function assumes the model contains specific variables and sets (e.g., GenPV, CurtPV, GenWind, PC, PD, SOC, etc.).
    - The function creates the output directory if it does not exist.
    - Results are only written if relevant data is available (e.g., non-empty results).
    """

    logging.info("Exporting SDOM results...")
    os.makedirs(output_dir, exist_ok=True)

    # Initialize results dictionaries column: [values]
    logging.debug("--Initializing results dictionaries...")
    gen_results = {'Scenario':[],'Hour': [], 'Solar PV Generation (MW)': [], 'Solar PV Curtailment (MW)': [],
                   'Wind Generation (MW)': [], 'Wind Curtailment (MW)': [],
                   'Gas CC Generation (MW)': [], 'Storage Charge/Discharge (MW)': []}

    storage_results = {'Hour': [], 'Technology': [], 'Charging power (MW)': [],
                       'Discharging power (MW)': [], 'State of charge (MWh)': []}

    summary_results_columns = ['Metric', 'Technology', 'Run', 'Optimal Value', 'Unit']
    summary_results = pd.DataFrame(columns=summary_results_columns)

    # Extract generation results
#    for run in range(num_runs):
    logging.debug("--Extracting generation results...")
    for h in model.h:
        solar_gen = safe_pyomo_value(model.GenPV[h])
        solar_curt = safe_pyomo_value(model.CurtPV[h])
        wind_gen = safe_pyomo_value(model.GenWind[h])
        wind_curt = safe_pyomo_value(model.CurtWind[h])
        gas_cc_gen = safe_pyomo_value(model.GenCC[h])

        if None not in [solar_gen, solar_curt, wind_gen, wind_curt, gas_cc_gen]:
#            gen_results['Scenario'].append(run)
            gen_results['Hour'].append(h)
            gen_results['Solar PV Generation (MW)'].append(solar_gen)
            gen_results['Solar PV Curtailment (MW)'].append(solar_curt)
            gen_results['Wind Generation (MW)'].append(wind_gen)
            gen_results['Wind Curtailment (MW)'].append(wind_curt)
            gen_results['Gas CC Generation (MW)'].append(gas_cc_gen)

            power_to_storage = sum(safe_pyomo_value(model.PC[h, j]) or 0 for j in model.j) - sum(safe_pyomo_value(model.PD[h, j]) or 0 for j in model.j)
            gen_results['Storage Charge/Discharge (MW)'].append(power_to_storage)
        gen_results['Scenario'].append(case)

    # Extract storage results
    logging.debug("--Extracting storage results...")
    for h in model.h:
        for j in model.j:
            charge_power = safe_pyomo_value(model.PC[h, j])
            discharge_power = safe_pyomo_value(model.PD[h, j])
            soc = safe_pyomo_value(model.SOC[h, j])
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
    summary_results = pd.concat([summary_results, total_cost], ignore_index=True)
    ## Total capacity
    cap = {}
    cap['GasCC'] = safe_pyomo_value(model.CapCC)
    cap['Solar PV'] = sum(safe_pyomo_value(model.Ypv[k]) * model.CapSolar_CAPEX_M[k] for k in model.k)
    cap['Wind'] = sum(safe_pyomo_value(model.Ywind[w]) * model.CapWind_CAPEX_M[w] for w in model.w)
    cap['All'] = cap['GasCC'] + cap['Solar PV'] + cap['Wind']
    capacities = pd.DataFrame.from_dict(cap, orient='index', columns=['Optimal Value'])
    capacities = capacities.reset_index(names=['Technology'])
    capacities['Run'] = 1
    capacities['Unit'] = 'MW'
    capacities['Metric'] = 'Capacity'
    summary_results = pd.concat([summary_results, capacities], ignore_index=True)
    ## Generation
    gen = {}
    gen['GasCC'] = safe_pyomo_value(sum(model.GenCC[h] for h in model.h))
    gen['Solar PV'] = sum(safe_pyomo_value(model.GenPV[h]) for h in model.h)
    gen['Wind'] = sum(safe_pyomo_value(model.GenWind[h]) for h in model.h)
    gen['Other renewables'] = safe_pyomo_value(sum(model.OtherRenewables[h]for h in model.h)) 
    gen['Hydro'] = safe_pyomo_value(sum(model.LargeHydro[h] for h in model.h))
    gen['Nuclear'] = safe_pyomo_value(sum(model.Nuclear[h] for h in model.h))
    gen['LiIon'] = safe_pyomo_value(sum(model.PD[h, 'Li-Ion'] for h in model.h))
    gen['CAES'] = safe_pyomo_value(sum(model.PD[h, 'CAES'] for h in model.h) )
    gen['PHS'] = safe_pyomo_value(sum(model.PD[h, 'PHS'] for h in model.h) )
    gen['H2'] = safe_pyomo_value(sum(model.PD[h, 'H2'] for h in model.h) )
    gen['All'] = gen['GasCC'] + gen['Solar PV'] + gen['Wind'] + gen['Other renewables'] + gen['Hydro'] + \
    gen['Nuclear'] + gen['LiIon'] + gen['CAES'] + gen['PHS'] + gen['H2']
    generation = pd.DataFrame.from_dict(gen, orient='index', columns=['Optimal Value'])
    generation = generation.reset_index(names=['Technology'])
    generation['Run'] = 1
    generation['Unit'] = 'MWh'
    generation['Metric'] = 'Total generation'
    summary_results = pd.concat([summary_results, generation], ignore_index=True)
    ## Storage energy charging
    stoch = {}
    stoch['LiIon'] = safe_pyomo_value(sum(model.PC[h, 'Li-Ion'] for h in model.h))
    stoch['CAES'] = safe_pyomo_value(sum(model.PC[h, 'CAES'] for h in model.h) )
    stoch['PHS'] = safe_pyomo_value(sum(model.PC[h, 'PHS'] for h in model.h) )
    stoch['H2'] = safe_pyomo_value(sum(model.PC[h, 'H2'] for h in model.h) )
    stoch['All'] = stoch['LiIon'] + stoch['CAES'] + stoch['PHS'] + stoch['H2']
    storage_charging = pd.DataFrame.from_dict(stoch, orient='index', columns=['Optimal Value'])
    storage_charging = storage_charging.reset_index(names=['Technology'])
    storage_charging['Run'] = 1
    storage_charging['Unit'] = 'MWh'
    storage_charging['Metric'] = 'Storage energy charging'
    summary_results = pd.concat([summary_results, storage_charging], ignore_index=True)
    ## Demand
    dem = {}
    dem['demand'] = sum(model.Load[h] for h in model.h)
    demand = pd.DataFrame.from_dict(dem, orient='index', columns=['Optimal Value'])
    demand = demand.reset_index(names=['Technology'])
    demand['Run'] = 1
    demand['Unit'] = 'MWh'
    demand['Metric'] = 'Total demand'
    summary_results = pd.concat([summary_results, demand], ignore_index=True)
    ## CAPEX
    capex = {}
    capex['Solar PV'] = sum(safe_pyomo_value((model.FCR_VRE * (MW_TO_KW * model.CapSolar_CAPEX_M[k] + model.CapSolar_trans_cap_cost[k]))\
                                         * model.CapSolar_capacity[k] * model.Ypv[k]) for k in model.k)
    capex['Wind'] = sum(safe_pyomo_value((model.FCR_VRE * (MW_TO_KW * model.CapWind_CAPEX_M[w] + model.CapWind_trans_cap_cost[w])) \
                                       * model.CapWind_capacity[w] * model.Ywind[w]) for w in model.w) 
    capex['GasCC'] = safe_pyomo_value(model.FCR_GasCC*MW_TO_KW*model.CapexGasCC*model.CapCC)
    capex['All'] = capex['Solar PV'] + capex['Wind'] + capex['GasCC']
    capital_costs = pd.DataFrame.from_dict(capex, orient='index', columns=['Optimal Value'])
    capital_costs = capital_costs.reset_index(names=['Technology'])
    capital_costs['Run'] = 1
    capital_costs['Unit'] = '$US'
    capital_costs['Metric'] = 'CAPEX'
    summary_results = pd.concat([summary_results, capital_costs], ignore_index=True)
    ## Power CAPEX
    pcapex = {}
    pcapex['LiIon'] = safe_pyomo_value(model.CRF['Li-Ion']*(MW_TO_KW*model.StorageData['CostRatio', 'Li-Ion'] * \
                                        model.StorageData['P_Capex', 'Li-Ion']*model.Pcha['Li-Ion']
                                        + MW_TO_KW*(1 - model.StorageData['CostRatio', 'Li-Ion']) * \
                                        model.StorageData['P_Capex', 'Li-Ion']*model.Pdis['Li-Ion']))
    pcapex['CAES'] = safe_pyomo_value(model.CRF['CAES']*(MW_TO_KW*model.StorageData['CostRatio', 'CAES'] * \
                                        model.StorageData['P_Capex', 'CAES']*model.Pcha['CAES']
                                        + MW_TO_KW*(1 - model.StorageData['CostRatio', 'CAES']) * \
                                        model.StorageData['P_Capex', 'CAES']*model.Pdis['CAES']))
    pcapex['PHS'] = safe_pyomo_value(model.CRF['PHS']*(MW_TO_KW*model.StorageData['CostRatio', 'PHS'] * \
                                    model.StorageData['P_Capex', 'PHS']*model.Pcha['PHS']
                                    + MW_TO_KW*(1 - model.StorageData['CostRatio', 'PHS']) * \
                                    model.StorageData['P_Capex', 'PHS']*model.Pdis['PHS']))
    pcapex['H2'] = safe_pyomo_value(model.CRF['H2']*(MW_TO_KW*model.StorageData['CostRatio', 'H2'] * \
                        model.StorageData['P_Capex', 'H2']*model.Pcha['H2']
                        + MW_TO_KW*(1 - model.StorageData['CostRatio', 'H2']) * \
                        model.StorageData['P_Capex', 'H2']*model.Pdis['H2']))
    pcapex['All'] = pcapex['LiIon'] + pcapex['CAES'] + pcapex['PHS'] + pcapex['H2']
    power_capex = pd.DataFrame.from_dict(pcapex, orient='index',columns=['Optimal Value'])
    power_capex = power_capex.reset_index(names=['Technology'])
    power_capex['Run'] = 1
    power_capex['Unit'] = '$US'
    power_capex['Metric'] = 'Power-CAPEX'
    summary_results = pd.concat([summary_results, power_capex], ignore_index=True)
    ## Energy CAPEX
    ecapex = {}    
    ecapex['LiIon'] = safe_pyomo_value(model.CRF['Li-Ion']*MW_TO_KW*model.StorageData['E_Capex', 'Li-Ion']*model.Ecap['Li-Ion'])
    ecapex['CAES'] = safe_pyomo_value(model.CRF['CAES']*MW_TO_KW*model.StorageData['E_Capex', 'CAES']*model.Ecap['CAES'])    
    ecapex['PHS'] = safe_pyomo_value(model.CRF['PHS']*MW_TO_KW*model.StorageData['E_Capex', 'PHS']*model.Ecap['PHS'])   
    ecapex['H2'] = safe_pyomo_value(model.CRF['H2']*MW_TO_KW*model.StorageData['E_Capex', 'H2']*model.Ecap['H2'])
    ecapex['All'] = ecapex['LiIon'] + ecapex['CAES'] + ecapex['PHS'] + ecapex['H2']
    energy_capex = pd.DataFrame.from_dict(ecapex, orient='index',columns=['Optimal Value'])
    energy_capex = energy_capex.reset_index(names=['Technology'])
    energy_capex['Run'] = 1
    energy_capex['Unit'] = '$US'
    energy_capex['Metric'] = 'Energy-CAPEX'
    summary_results = pd.concat([summary_results, energy_capex], ignore_index=True)
    ## Total CAPEX
    tcapex = {}    
    tcapex['LiIon'] = pcapex['LiIon'] + ecapex['LiIon']
    tcapex['CAES'] = pcapex['CAES'] + ecapex['CAES']  
    tcapex['PHS'] = pcapex['PHS'] + ecapex['PHS']  
    tcapex['H2'] = pcapex['H2'] + ecapex['H2']
    tcapex['All'] = tcapex['LiIon'] + tcapex['CAES'] + tcapex['PHS'] + tcapex['H2']
    total_capex = pd.DataFrame.from_dict(tcapex, orient='index',columns=['Optimal Value'])
    total_capex = total_capex.reset_index(names=['Technology'])
    total_capex['Run'] = 1
    total_capex['Unit'] = '$US'
    total_capex['Metric'] = 'Total-CAPEX'
    summary_results = pd.concat([summary_results, total_capex], ignore_index=True)
    ## FOM
    fom = {}
    fom['GasCC'] = safe_pyomo_value(MW_TO_KW*model.FOM_GasCC*model.CapCC)
    fom['Solar PV'] = sum(safe_pyomo_value((model.FCR_VRE * MW_TO_KW*model.CapSolar_FOM_M[k]) * model.CapSolar_capacity[k] * model.Ypv[k]) for k in model.k)
    fom['Wind'] = sum(safe_pyomo_value((model.FCR_VRE * MW_TO_KW*model.CapWind_FOM_M[w]) * model.CapWind_capacity[w] * model.Ywind[w]) for w in model.w)
    fom['LiIon'] = safe_pyomo_value(MW_TO_KW*model.StorageData['CostRatio', 'Li-Ion'] * model.StorageData['FOM', 'Li-Ion']*model.Pcha['Li-Ion']
                                + MW_TO_KW*(1 - model.StorageData['CostRatio', 'Li-Ion']) * model.StorageData['FOM', 'Li-Ion']*model.Pdis['Li-Ion'])
    fom['CAES'] = safe_pyomo_value(MW_TO_KW*model.StorageData['CostRatio', 'CAES'] * model.StorageData['FOM', 'CAES']*model.Pcha['CAES']
                            + MW_TO_KW*(1 - model.StorageData['CostRatio', 'CAES']) * model.StorageData['FOM', 'CAES']*model.Pdis['CAES'])
    fom['PHS'] = safe_pyomo_value(MW_TO_KW*model.StorageData['CostRatio', 'PHS'] * model.StorageData['FOM', 'PHS']*model.Pcha['PHS']
                                + MW_TO_KW*(1 - model.StorageData['CostRatio', 'PHS']) * model.StorageData['FOM', 'PHS']*model.Pdis['PHS'])
    fom['H2'] = safe_pyomo_value(MW_TO_KW*model.StorageData['CostRatio', 'H2'] * model.StorageData['FOM', 'H2']*model.Pcha['H2']
                            + MW_TO_KW*(1 - model.StorageData['CostRatio', 'H2']) * model.StorageData['FOM', 'H2']*model.Pdis['H2'])
    fom['All'] = fom['GasCC'] + fom['Solar PV'] + fom['Wind'] + fom['LiIon'] + fom['CAES'] + fom['PHS'] + fom['H2'] 
    fixedom = pd.DataFrame.from_dict(fom, orient='index', columns=['Optimal Value'])
    fixedom = fixedom.reset_index(names=['Technology'])
    fixedom['Run'] = 1
    fixedom['Unit'] = '$US'
    fixedom['Metric'] = 'FOM'
    summary_results = pd.concat([summary_results, fixedom], ignore_index=True)
    ## VOM
    vom = {}
    vom['GasCC'] = safe_pyomo_value((model.GasPrice * model.HR + model.VOM_GasCC) *sum(model.GenCC[h] for h in model.h))
    vom['LiIon'] = safe_pyomo_value(model.StorageData['VOM', 'Li-Ion'] * sum(model.PD[h, 'Li-Ion'] for h in model.h))
    vom['CAES'] = safe_pyomo_value(model.StorageData['VOM', 'CAES'] * sum(model.PD[h, 'CAES'] for h in model.h) )
    vom['PHS'] = safe_pyomo_value(model.StorageData['VOM', 'PHS'] * sum(model.PD[h, 'PHS'] for h in model.h) )
    vom['H2'] = safe_pyomo_value(model.StorageData['VOM', 'H2'] * sum(model.PD[h, 'H2'] for h in model.h) )
    vom['All'] = vom['GasCC'] + vom['LiIon'] + vom['CAES'] + vom['PHS'] + vom['H2'] 
    variableom = pd.DataFrame.from_dict(vom, orient='index', columns=['Optimal Value'])
    variableom = variableom.reset_index(names=['Technology'])
    variableom['Run'] = 1
    variableom['Unit'] = '$US'
    variableom['Metric'] = 'VOM'
    summary_results = pd.concat([summary_results, variableom], ignore_index=True)
    ## OPEX
    opex = {}
    opex['GasCC'] = fom['GasCC'] + vom['GasCC']
    opex['Solar PV'] = fom['Solar PV'] 
    opex['Wind'] = fom['Wind'] 
    opex['LiIon'] = fom['LiIon'] + vom['LiIon']
    opex['CAES'] = fom['CAES'] + vom['CAES']
    opex['PHS'] = fom['PHS'] + vom['PHS']
    opex['H2'] = fom['H2'] + vom['H2']
    opex['All'] = opex['GasCC'] + opex['Solar PV'] + opex['Wind'] + opex['LiIon'] + opex['CAES'] + opex['PHS'] + opex['H2'] 
    operating_cost = pd.DataFrame.from_dict(opex, orient='index', columns=['Optimal Value'])
    operating_cost = operating_cost.reset_index(names=['Technology'])
    operating_cost['Run'] = 1
    operating_cost['Unit'] = '$US'
    operating_cost['Metric'] = 'OPEX'
    summary_results = pd.concat([summary_results, operating_cost], ignore_index=True)
    ## Charge power capacity
    charge = {}
    charge['LiIon'] = safe_pyomo_value(model.Pcha['Li-Ion'])
    charge['CAES'] = safe_pyomo_value(model.Pcha['CAES'])
    charge['PHS'] = safe_pyomo_value(model.Pcha['PHS'])
    charge['H2'] = safe_pyomo_value(model.Pcha['H2'])
    charge['All'] = charge['LiIon'] + charge['CAES'] + charge['PHS'] + charge['H2']
    charge_power = pd.DataFrame.from_dict(charge, orient='index', columns=['Optimal Value'])
    charge_power = charge_power.reset_index(names=['Technology'])
    charge_power['Run'] = 1
    charge_power['Unit'] = 'MW'
    charge_power['Metric'] = 'Charge power capacity'
    summary_results = pd.concat([summary_results, charge_power], ignore_index=True)
    ## Discharge power capacity
    dcharge = {}
    dcharge['LiIon'] = safe_pyomo_value(model.Pdis['Li-Ion'] )
    dcharge['CAES'] = safe_pyomo_value(model.Pdis['CAES'])
    dcharge['PHS'] = safe_pyomo_value(model.Pdis['PHS'])
    dcharge['H2'] = safe_pyomo_value(model.Pdis['H2'])
    dcharge['All'] = dcharge['LiIon'] + dcharge['CAES'] + dcharge['PHS'] + dcharge['H2']
    dcharge_power = pd.DataFrame.from_dict(dcharge, orient='index', columns=['Optimal Value'])
    dcharge_power = dcharge_power.reset_index(names=['Technology'])
    dcharge_power['Run'] = 1
    dcharge_power['Unit'] = 'MW'
    dcharge_power['Metric'] = 'Discharge power capacity'
    summary_results = pd.concat([summary_results, dcharge_power], ignore_index=True)
    ## Average power capacity
    avgpocap = {}
    avgpocap['LiIon'] = (charge['LiIon'] + dcharge['LiIon'])/2
    avgpocap['CAES'] = (charge['CAES'] + dcharge['CAES'])/2
    avgpocap['PHS'] = (charge['PHS'] + dcharge['PHS'])/2
    avgpocap['H2'] = (charge['H2'] + dcharge['H2'])/2
    avgpocap['All'] = avgpocap['LiIon'] + avgpocap['CAES'] + avgpocap['PHS'] + avgpocap['H2']
    average_power = pd.DataFrame.from_dict(avgpocap, orient='index', columns=['Optimal Value'])
    average_power = average_power.reset_index(names=['Technology'])
    average_power['Run'] = 1
    average_power['Unit'] = 'MW'
    average_power['Metric'] = 'Average power capacity'
    summary_results = pd.concat([summary_results, average_power], ignore_index=True)
    ## Energy capacity
    encap = {}
    encap['LiIon'] = safe_pyomo_value(model.Ecap['Li-Ion'] )
    encap['CAES'] = safe_pyomo_value(model.Ecap['CAES'])
    encap['PHS'] = safe_pyomo_value(model.Ecap['PHS'])
    encap['H2'] = safe_pyomo_value(model.Ecap['H2'])
    encap['All'] = encap['LiIon'] + encap['CAES'] + encap['PHS'] + encap['H2']
    energy_cap = pd.DataFrame.from_dict(encap, orient='index', columns=['Optimal Value'])
    energy_cap = energy_cap.reset_index(names=['Technology'])
    energy_cap['Run'] = 1
    energy_cap['Unit'] = 'MWh'
    energy_cap['Metric'] = 'Energy capacity'
    summary_results = pd.concat([summary_results, energy_cap], ignore_index=True)
    ## Discharge duration
    dur = {}
    dur['LiIon'] = safe_pyomo_value(sqrt(model.StorageData['Eff','Li-Ion']*model.Ecap['Li-Ion']/(model.Pdis['Li-Ion'] + 1e-15)))
    dur['CAES'] = safe_pyomo_value(sqrt(model.StorageData['Eff','CAES']*model.Ecap['CAES']/(model.Pdis['CAES'] + 1e-15)))
    dur['PHS'] = safe_pyomo_value(sqrt(model.StorageData['Eff','PHS']*model.Ecap['PHS']/(model.Pdis['PHS'] + 1e-15)))
    dur['H2'] = safe_pyomo_value(sqrt(model.StorageData['Eff','H2']*model.Ecap['H2']/(model.Pdis['H2'] + 1e-15)))
    duration = pd.DataFrame.from_dict(dur, orient='index', columns=['Optimal Value'])
    duration = duration.reset_index(names=['Technology'])
    duration['Run'] = 1
    duration['Unit'] = 'h'
    duration['Metric'] = 'Duration'
    summary_results = pd.concat([summary_results, duration], ignore_index=True)
    ## Equivalent number of cycles
    cyc = {}
    cyc['LiIon'] = safe_pyomo_value(gen['LiIon']/(model.Ecap['Li-Ion'] + 1e-15))
    cyc['CAES'] = safe_pyomo_value(gen['CAES']/(model.Ecap['CAES'] + 1e-15))
    cyc['PHS'] = safe_pyomo_value(gen['PHS']/(model.Ecap['PHS'] + 1e-15))
    cyc['H2'] = safe_pyomo_value(gen['H2']/(model.Ecap['H2']+ 1e-15))
    cycles = pd.DataFrame.from_dict(cyc, orient='index', columns=['Optimal Value'])
    cycles = cycles.reset_index(names=['Technology'])
    cycles['Run'] = 1
    cycles['Unit'] = '-'
    cycles['Metric'] = 'Equivalent number of cycles'
    summary_results = pd.concat([summary_results, cycles], ignore_index=True)

    logging.info("Exporting csv files containing SDOM results...")
    # Save generation results to CSV
    logging.debug("--Saving generation results to CSV...")
    if gen_results['Hour']:
        with open(output_dir + f'OutputGeneration_{case}.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=gen_results.keys())
            writer.writeheader()
            writer.writerows([dict(zip(gen_results, t))
                             for t in zip(*gen_results.values())])

    # Save storage results to CSV
    logging.debug("--Saving storage results to CSV...")
    if storage_results['Hour']:
        with open(output_dir + f'OutputStorage_{case}.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=storage_results.keys())
            writer.writeheader()
            writer.writerows([dict(zip(storage_results, t))
                             for t in zip(*storage_results.values())])

    # Save summary results to CSV
    logging.debug("--Saving summary results to CSV...")
    if len(summary_results)>0:
        summary_results.to_csv(output_dir + f'OutputSummary_{case}.csv', index=False)
