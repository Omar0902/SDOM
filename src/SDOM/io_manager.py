import logging
import pandas as pd
import os
import csv

from pyomo.environ import sqrt

from .common.utilities import safe_pyomo_value, check_file_exists, compare_lists, concatenate_dataframes
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
    
    logging.debug("- Trying to load VRE data...")
    # THE SET CSV FILES WERE REMOVED
    # input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["solar_plants"])
    # if check_file_exists(input_file_path, "solar plants ids"):
    #     solar_plants = pd.read_csv( input_file_path, header=None )[0].tolist()
    
    # input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["wind_plants"])
    # if check_file_exists(input_file_path, "wind plants ids"):
    #     wind_plants = pd.read_csv( input_file_path, header=None )[0].tolist()
    
    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["cf_solar"])
    if check_file_exists(input_file_path, "Capacity factors for pv solar"):
        cf_solar = pd.read_csv( input_file_path ).round(5)
        cf_solar.columns = cf_solar.columns.astype(str)
        solar_plants = cf_solar.columns[1:].tolist()
        logging.debug( f"-- It were loaded a total of {len( solar_plants )} solar plants profiles." )
    

    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["cf_wind"])
    if check_file_exists(input_file_path, "Capacity factors for wind"):
        cf_wind = pd.read_csv( input_file_path ).round(5)
        cf_wind.columns = cf_wind.columns.astype(str)
        wind_plants = cf_wind.columns[1:].tolist()
        logging.debug( f"-- It were loaded a total of {len( wind_plants )} wind plants profiles." )

    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["cap_solar"])
    if check_file_exists(input_file_path, "Capex information for solar"):
        cap_solar = pd.read_csv( input_file_path ).round(5)
        cap_solar['sc_gid'] = cap_solar['sc_gid'].astype(str)
        solar_plants_capex = cap_solar['sc_gid'].tolist()
        compare_lists(solar_plants, solar_plants_capex, text_comp="solar plants", list_names=["CF", "Capex"])

    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["cap_wind"])
    if check_file_exists(input_file_path, "Capex information for wind"):
        cap_wind = pd.read_csv( input_file_path ).round(5)
        cap_wind['sc_gid'] = cap_wind['sc_gid'].astype(str)
        wind_plants_capex = cap_wind['sc_gid'].tolist()
        compare_lists(wind_plants, wind_plants_capex, text_comp="wind plants", list_names=["CF", "Capex"])

    logging.debug("- Trying to load demand data...")
    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["load_data"])
    if check_file_exists(input_file_path, "load data"):
        load_data = pd.read_csv( input_file_path ).round(5)

    logging.debug("- Trying to load nuclear data...")
    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["nuclear_data"])
    if check_file_exists(input_file_path, "nuclear data"):
        nuclear_data = pd.read_csv( input_file_path ).round(5)

    logging.debug("- Trying to load large hydro data...")
    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["large_hydro_data"])
    if check_file_exists(input_file_path, "large hydro data"):
        large_hydro_data = pd.read_csv( input_file_path ).round(5)

    logging.debug("- Trying to load other renewables data...")
    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["other_renewables_data"])
    if check_file_exists(input_file_path, "other renewables data"):
        other_renewables_data = pd.read_csv( input_file_path ).round(5)

    logging.debug("- Trying to load storage data...")
    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["storage_data"])
    if check_file_exists(input_file_path, "Storage data"):
        storage_data = pd.read_csv( input_file_path, index_col=0 ).round(5)
        storage_set_j_techs = storage_data.columns[0:].astype(str).tolist()
        storage_set_b_techs = storage_data.columns[ storage_data.loc["Coupled"] == 1 ].astype( str ).tolist()

    logging.debug("- Trying to load thermal generation data...")
    input_file_path = os.path.join(input_data_dir, INPUT_CSV_NAMES["thermal_data"])
    if check_file_exists(input_file_path, "thermal data"):
        thermal_data = pd.read_csv( input_file_path ).round(5)

    logging.debug("- Trying to load scalars data...")
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
        "STORAGE_SET_B_TECHS": storage_set_b_techs,
        "thermal_data": thermal_data,
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
                   'Thermal Generation (MW)': [], 'Storage Charge/Discharge (MW)': []}

    storage_results = {'Hour': [], 'Technology': [], 'Charging power (MW)': [],
                       'Discharging power (MW)': [], 'State of charge (MWh)': []}

    # Extract generation results
#    for run in range(num_runs):
    logging.debug("--Extracting generation results...")
    for h in model.h:
        solar_gen = safe_pyomo_value(model.GenPV[h])
        solar_curt = safe_pyomo_value(model.CurtPV[h])
        wind_gen = safe_pyomo_value(model.GenWind[h])
        wind_curt = safe_pyomo_value(model.CurtWind[h])
        gas_cc_gen = sum( safe_pyomo_value(model.GenCC[h, bu]) for bu in model.bu )

        if None not in [solar_gen, solar_curt, wind_gen, wind_curt, gas_cc_gen]:
#            gen_results['Scenario'].append(run)
            gen_results['Hour'].append(h)
            gen_results['Solar PV Generation (MW)'].append(solar_gen)
            gen_results['Solar PV Curtailment (MW)'].append(solar_curt)
            gen_results['Wind Generation (MW)'].append(wind_gen)
            gen_results['Wind Curtailment (MW)'].append(wind_curt)
            gen_results['Thermal Generation (MW)'].append(gas_cc_gen)

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
    summary_results = total_cost

    ## Total capacity
    cap = {}
    cap['Thermal'] = sum( safe_pyomo_value( model.CapCC[bu] ) for bu in model.bu )
    cap['Solar PV'] = sum(safe_pyomo_value(model.Ypv[k]) * model.CapSolar_CAPEX_M[k] for k in model.k) #TODO REVIEW THIS
    cap['Wind'] = sum(safe_pyomo_value(model.Ywind[w]) * model.CapWind_CAPEX_M[w] for w in model.w)
    cap['All'] = cap['Thermal'] + cap['Solar PV'] + cap['Wind']

    summary_results = concatenate_dataframes( summary_results, cap, run=1, unit='MW', metric='Capacity' )
    
    ## Generation
    gen = {}
    gen['Thermal'] =  safe_pyomo_value( model.annual_thermal_gen_expr )
    gen['Solar PV'] = sum(safe_pyomo_value(model.GenPV[h]) for h in model.h)
    gen['Wind'] = sum(safe_pyomo_value(model.GenWind[h]) for h in model.h)
    gen['Other renewables'] = safe_pyomo_value(sum(model.OtherRenewables[h]for h in model.h)) 
    gen['Hydro'] = safe_pyomo_value(sum(model.hydro.ts_parameter[h] for h in model.h))
    gen['Nuclear'] = safe_pyomo_value(sum(model.Nuclear[h] for h in model.h))
    
    sum_all = 0.0
    storage_tech_list = list(model.j)
    for tech in storage_tech_list:
        gen[tech] = safe_pyomo_value( sum( model.PD[h, tech] for h in model.h ) )
        sum_all += gen[tech]

    gen['All'] = gen['Thermal'] + gen['Solar PV'] + gen['Wind'] + gen['Other renewables'] + gen['Hydro'] + \
                gen['Nuclear'] + sum_all

    summary_results = concatenate_dataframes( summary_results, gen, run=1, unit='MWh', metric='Total generation' )
    
    ## Storage energy charging
    sum_all = 0.0
    stoch = {}
    for tech in storage_tech_list:
        stoch[tech] = safe_pyomo_value( sum( model.PC[h, tech] for h in model.h ) )
        sum_all += stoch[tech]
    stoch['All'] = sum_all

    summary_results = concatenate_dataframes( summary_results, stoch, run=1, unit='MWh', metric='Storage energy charging' )
    
    ## Demand
    dem = {}
    dem['demand'] = sum(model.Load[h] for h in model.h)

    summary_results = concatenate_dataframes( summary_results, dem, run=1, unit='MWh', metric='Total demand' )
    
    ## CAPEX
    capex = {}
    capex['Solar PV'] = safe_pyomo_value( model.pv_capex_cost_expr )
    capex['Wind'] = safe_pyomo_value( model.wind_capex_cost_expr )
    capex['Thermal'] = sum( safe_pyomo_value( model.FCR_GasCC[bu] * MW_TO_KW * model.CapexGasCC[bu] * model.CapCC[bu] ) for bu in model.bu )
    capex['All'] = capex['Solar PV'] + capex['Wind'] + capex['Thermal']

    summary_results = concatenate_dataframes( summary_results, capex, run=1, unit='$US', metric='CAPEX' )
    
    ## Power CAPEX
    pcapex = {}
    sum_all = 0.0
    for tech in storage_tech_list:
        pcapex[tech] = safe_pyomo_value(model.CRF[tech]*(MW_TO_KW*model.StorageData['CostRatio', tech] * \
                                        model.StorageData['P_Capex', tech]*model.Pcha[tech]
                                        + MW_TO_KW*(1 - model.StorageData['CostRatio', tech]) * \
                                        model.StorageData['P_Capex', tech]*model.Pdis[tech]))
        sum_all += pcapex[tech]
    
    pcapex['All'] = sum_all

    summary_results = concatenate_dataframes( summary_results, pcapex, run=1, unit='$US', metric='Power-CAPEX' )

    ## Energy CAPEX and Total CAPEX
    ecapex = {}
    tcapex = {}
    sum_all = 0.0
    sum_all_t = 0.0
    for tech in storage_tech_list:
        ecapex[tech] = safe_pyomo_value(model.CRF[tech]*MW_TO_KW*model.StorageData['E_Capex', tech]*model.Ecap[tech])
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
    fom['Thermal'] = sum( safe_pyomo_value( MW_TO_KW*model.FOM_GasCC[bu]*model.CapCC[bu] ) for bu in model.bu )
    fom['Solar PV'] = safe_pyomo_value( model.pv_fixed_om_cost_expr )
    fom['Wind'] = safe_pyomo_value( model.wind_fixed_om_cost_expr )
     
    for tech in storage_tech_list:
        fom[tech] = safe_pyomo_value(MW_TO_KW*model.StorageData['CostRatio', tech] * model.StorageData['FOM', tech]*model.Pcha[tech]
                            + MW_TO_KW*(1 - model.StorageData['CostRatio', tech]) * model.StorageData['FOM', tech]*model.Pdis[tech])
        sum_all += fom[tech]

    fom['All'] = fom['Thermal'] + fom['Solar PV'] + fom['Wind'] + sum_all 

    summary_results = concatenate_dataframes( summary_results, fom, run=1, unit='$US', metric='FOM' )
    
    ## VOM
    vom = {}
    sum_all = 0.0
    #TODO review this calculation
    vom['Thermal'] = sum( safe_pyomo_value( (model.VOM_GasCC[bu]) *sum(model.GenCC[h, bu] for h in model.h ) ) for bu in model.bu )

    for tech in storage_tech_list:
        vom[tech] = safe_pyomo_value(model.StorageData['VOM', tech] * sum(model.PD[h, tech] for h in model.h))
        sum_all += vom[tech]
    vom['All'] = vom['Thermal'] + sum_all

    summary_results = concatenate_dataframes( summary_results, vom, run=1, unit='$US', metric='VOM' )

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

    ## Charge power capacity
    charge = {}
    sum_all = 0.0
    for tech in storage_tech_list:
        charge[tech] = safe_pyomo_value(model.Pcha[tech])
        sum_all += charge[tech]
    charge['All'] = sum_all

    summary_results = concatenate_dataframes( summary_results, charge, run=1, unit='MW', metric='Charge power capacity' )

    ## Discharge power capacity
    dcharge = {}
    sum_all = 0.0

    for tech in storage_tech_list:
        dcharge[tech] = safe_pyomo_value(model.Pdis[tech])
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
        encap[tech] = safe_pyomo_value(model.Ecap[tech])
        sum_all += encap[tech]
    encap['All'] = sum_all

    summary_results = concatenate_dataframes( summary_results, encap, run=1, unit='MWh', metric='Energy capacity' )

    ## Discharge duration
    dur = {}
    for tech in storage_tech_list:
        dur[tech] = safe_pyomo_value(sqrt(model.StorageData['Eff', tech] * model.Ecap[tech] / (model.Pdis[tech] + 1e-15)))

    summary_results = concatenate_dataframes( summary_results, dur, run=1, unit='h', metric='Duration' )

    ## Equivalent number of cycles
    cyc = {}
    for tech in storage_tech_list:
        cyc[tech] = safe_pyomo_value(gen[tech] / (model.Ecap[tech] + 1e-15))

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
    if len(summary_results)>0:
        summary_results.to_csv(output_dir + f'OutputSummary_{case}.csv', index=False)
