# -*- coding: utf-8 -*-
"""
Created on Tue Sep  24 13:46:19 2024

@author: ttran2
"""

from pyomo.environ import *
import pandas as pd
import csv
import os
from pyomo.opt import SolverFactory
from pyomo.opt import SolverResults

# ---------------------------------------------------------------------------------
# Data loading
def load_data():
    solar_plants = pd.read_csv('Set_k_SolarPV.csv', header=None)[0].tolist()
    wind_plants = pd.read_csv('Set_w_Wind.csv', header=None)[0].tolist()

    load_data = pd.read_csv('Load_hourly_2050.csv')
    nuclear_data = pd.read_csv('Nucl_hourly_2019.csv')
    large_hydro_data = pd.read_csv('lahy_hourly_2019.csv')
    other_renewables_data = pd.read_csv('otre_hourly_2019.csv')
    cf_solar = pd.read_csv('CFSolar_2050.csv')
    cf_wind = pd.read_csv('CFWind_2050.csv')
    cap_solar = pd.read_csv('CapSolar_2050.csv')
    cap_wind = pd.read_csv('CapWind_2050.csv')
    storage_data = pd.read_csv('StorageData_2050.csv', index_col=0)

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
    }

# ---------------------------------------------------------------------------------
# Model initialization
def initialize_model(data):
    model = ConcreteModel()

    # Solar plant ID alignment
    solar_plants_cf = data['cf_solar'].columns[1:].astype(str).tolist()
    solar_plants_cap = data['cap_solar']['sc_gid'].astype(str).tolist()
    common_solar_plants = list(set(solar_plants_cf) & set(solar_plants_cap))

    # Filter solar data and initialize model set
    complete_solar_data = data["cap_solar"][data["cap_solar"]['sc_gid'].astype(str).isin(common_solar_plants)]
    complete_solar_data = complete_solar_data.dropna(subset=['CAPEX_M', 'trans_cap_cost', 'FOM_M'])
    common_solar_plants_filtered = complete_solar_data['sc_gid'].astype(str).tolist()
    model.k = Set(initialize=common_solar_plants_filtered)

    # Wind plant ID alignment
    wind_plants_cf = data['cf_wind'].columns[1:].astype(str).tolist()
    wind_plants_cap = data['cap_wind']['sc_gid'].astype(str).tolist()
    common_wind_plants = list(set(wind_plants_cf) & set(wind_plants_cap))

    # Filter wind data and initialize model set
    complete_wind_data = data["cap_wind"][data["cap_wind"]['sc_gid'].astype(str).isin(common_wind_plants)]
    complete_wind_data = complete_wind_data.dropna(subset=['CAPEX_M', 'trans_cap_cost', 'FOM_M'])
    common_wind_plants_filtered = complete_wind_data['sc_gid'].astype(str).tolist()
    model.w = Set(initialize=common_wind_plants_filtered)

    # Initialize solar parameters, with default values for missing data
    for property_name in ['trans_cap_cost', 'CAPEX_M', 'FOM_M']:
        property_dict = complete_solar_data.set_index('sc_gid')[property_name].to_dict()
        
        default_value = 0.0
        filtered_property_dict = {k: property_dict.get(k, default_value) for k in model.k}
        model.add_component(f"CapSolar_{property_name}", Param(model.k, initialize=filtered_property_dict))

    # Initialize wind parameters, with default values for missing data
    for property_name in ['trans_cap_cost', 'CAPEX_M', 'FOM_M']:
        property_dict = complete_wind_data.set_index('sc_gid')[property_name].to_dict()

        default_value = 0.0
        filtered_property_dict = {k: property_dict.get(k, default_value) for k in model.w}
        model.add_component(f"CapWind_{property_name}", Param(model.w, initialize=filtered_property_dict))

    # Define sets
    model.h = RangeSet(1, 8760)
    model.j = Set(initialize=['Li-Ion', 'CAES', 'PHS', 'H2'])
    model.b = Set(initialize=['Li-Ion', 'PHS'])

    # Initialize storage properties
    storage_properties = ['P_Capex', 'E_Capex', 'Eff', 'Min_Duration', 'Max_Duration', 'Max_P', 'FOM', 'VOM', 'Lifetime', 'CostRatio']
    model.sp = Set(initialize=storage_properties)

    # Scalar parameters
    model.r = Param(initialize=0.06)
    model.GasPrice = Param(initialize=4.113894393)
    model.HR = Param(initialize=6.4005)
    model.GenMix_Target = Param(initialize=1.00, mutable=True)
    model.AlphaNuclear = Param(initialize=1)
    model.AlphaLargHy = Param(initialize=1)
    model.AlphaOtheRe = Param(initialize=1)

    model.CapexGasCC = Param(initialize=940.6078576)
    model.FOM_GasCC = Param(initialize=13.2516707)
    model.VOM_GasCC = Param(initialize=2.226321156)

    # Capital recovery factor
    def fcr_rule(model, lifetime=30):
        return (model.r * (1 + model.r) ** lifetime) / ((1 + model.r) ** lifetime - 1)
    model.FCR_VRE = Param(initialize=fcr_rule(model))
    model.FCR_GasCC = Param(initialize=fcr_rule(model))

    # Load data initialization
    model.Load = Param(model.h, initialize=data["load_data"].set_index('*Hour')['Load'].to_dict())

    # Solar capacity factor initialization
    cf_solar_melted = data["cf_solar"].melt(id_vars='Hour', var_name='plant', value_name='CF')
    cf_solar_filtered = cf_solar_melted[cf_solar_melted['plant'].isin(model.k)]
    cf_solar_dict = cf_solar_filtered.set_index(['Hour', 'plant'])['CF'].to_dict()
    model.CFSolar = Param(model.h, model.k, initialize=cf_solar_dict)

    # Wind capacity factor initialization
    cf_wind_melted = data["cf_wind"].melt(id_vars='Hour', var_name='plant', value_name='CF')
    cf_wind_filtered = cf_wind_melted[cf_wind_melted['plant'].isin(model.w)]
    cf_wind_dict = cf_wind_filtered.set_index(['Hour', 'plant'])['CF'].to_dict()
    model.CFWind = Param(model.h, model.w, initialize=cf_wind_dict)

    # Storage data initialization
    storage_dict = data["storage_data"].stack().to_dict()
    storage_tuple_dict = {(prop, tech): storage_dict[(prop, tech)] for prop in storage_properties for tech in model.j}
    model.StorageData = Param(model.sp, model.j, initialize=storage_tuple_dict)

    # Capital recovery factor for storage
    def crf_rule(model, j):
        lifetime = model.StorageData['Lifetime', j]
        return (model.r * (1 + model.r) ** lifetime) / ((1 + model.r) ** lifetime - 1)
    model.CRF = Param(model.j, initialize=crf_rule)

    # Define variables
    model.GenPV = Var(model.h, domain=NonNegativeReals)
    model.CurtPV = Var(model.h, domain=NonNegativeReals, initialize=0)
    model.GenWind = Var(model.h, domain=NonNegativeReals)
    model.CurtWind = Var(model.h, domain=NonNegativeReals, initialize=0)
    model.CapCC = Var(domain=NonNegativeReals)
    model.GenCC = Var(model.h, domain=NonNegativeReals)

    model.PC = Var(model.h, model.j, domain=NonNegativeReals)
    model.PD = Var(model.h, model.j, domain=NonNegativeReals)
    model.SOC = Var(model.h, model.j, domain=NonNegativeReals)
    model.Pcha = Var(model.j, domain=NonNegativeReals)
    model.Pdis = Var(model.j, domain=NonNegativeReals)
    model.Ecap = Var(model.j, domain=NonNegativeReals)

    model.Ypv = Var(model.k, domain=Binary, initialize=0)
    model.Ywind = Var(model.w, domain=Binary, initialize=0)
    model.Ystorage = Var(model.j, model.h, domain=Binary, initialize=0)

    # Define the objective function
    def objective_rule(model):
        total_cost = sum(
            model.FCR_VRE * (1000 * model.CapSolar_CAPEX_M[k] + model.CapSolar_trans_cap_cost[k] + 1000 * model.CapSolar_FOM_M[k]) * model.Ypv[k]
            for k in model.k
        ) + sum(
            model.FCR_VRE * (1000 * model.CapWind_CAPEX_M[w] + model.CapWind_trans_cap_cost[w] + 1000 * model.CapWind_FOM_M[w]) * model.Ywind[w]
            for w in model.w
        ) + sum(
            model.CRF[j] * (1000 * model.StorageData['CostRatio', j] * model.StorageData['P_Capex', j] * model.Pcha[j] +
                            1000 * (1 - model.StorageData['CostRatio', j]) * model.StorageData['P_Capex', j] * model.Pdis[j] +
                            1000 * model.StorageData['E_Capex', j] * model.Ecap[j])
            for j in model.j
        ) + sum(
            1000 * model.StorageData['CostRatio', j] * model.StorageData['FOM', j] * model.Pcha[j] +
            1000 * (1 - model.StorageData['CostRatio', j]) * model.StorageData['FOM', j] * model.Pdis[j] +
            model.StorageData['VOM', j] * sum(model.PD[h, j] for h in model.h)
            for j in model.j
        ) + model.FCR_GasCC * 1000 * model.CapexGasCC * model.CapCC + sum(
            model.GasPrice * model.HR * model.GenCC[h] + model.FOM_GasCC * 1000 * model.CapCC + model.VOM_GasCC * model.GenCC[h]
            for h in model.h
        )

        return total_cost

    model.Obj = Objective(rule=objective_rule, sense=minimize)
   
    # Define constraints
    def supply_balance_rule(model, h):
        return model.Load[h] + sum(model.PC[h, j] for j in model.j) - model.GenPV[h] - model.GenWind[h] - sum(model.PD[h, j] for j in model.j) - model.GenCC[h] == 0

    model.SupplyBalance = Constraint(model.h, rule=supply_balance_rule)

    # Additional constraints (charging, discharging, capacity...)
    model.MaxChargePower = Constraint(model.h, model.j, rule=lambda m, h, j: m.PC[h, j] <= m.StorageData['Max_P', j] * m.Ystorage[j, h])
    model.MaxDischargePower = Constraint(model.h, model.j, rule=lambda m, h, j: m.PD[h, j] <= m.StorageData['Max_P', j] * (1 - m.Ystorage[j, h]))
    model.MaxPcha = Constraint(model.j, rule=lambda m, j: m.Pcha[j] <= m.StorageData['Max_P', j])
    model.MaxPdis = Constraint(model.j, rule=lambda m, j: m.Pdis[j] <= m.StorageData['Max_P', j])
    model.MinEcap = Constraint(model.j, rule=lambda m, j: m.Ecap[j] >= m.StorageData['Min_Duration', j] * m.Pdis[j] / sqrt(m.StorageData['Eff', j]))
    model.MaxEcap = Constraint(model.j, rule=lambda m, j: m.Ecap[j] <= m.StorageData['Max_Duration', j] * m.Pdis[j] / sqrt(m.StorageData['Eff', j]))

    # State of charge constraints
    model.SOCBalance = Constraint(model.h, model.j, rule=lambda m, h, j: m.SOC[h, j] == m.SOC[h-1, j] + sqrt(m.StorageData['Eff', j]) * m.PC[h, j] - m.PD[h, j] / sqrt(m.StorageData['Eff', j]) if h > 1 else Constraint.Skip)
    model.SOCInitialBalance = Constraint(model.j, rule=lambda m, j: m.SOC[1, j] == 0)

    return model


# ---------------------------------------------------------------------------------
# Run solver and collect results

def safe_value(var):
    """Return the value of a variable or expression if it is initialized, else return None."""
    try:
        return value(var) if var is not None else None
    except ValueError:
        # To handle cases where var is not initialized
        return None

def collect_results(model):
    results = {}

    # Collect total cost from the objective
    results['Total_Cost'] = safe_value(model.Obj.expr)

    # Collect capacity results
    results['Total_CapCC'] = safe_value(model.CapCC)
    results['Total_CapPV'] = sum(safe_value(model.Ypv[k]) * model.CapSolar_CAPEX_M[k]
                                 for k in model.k if safe_value(model.Ypv[k]) is not None)
    results['Total_CapWind'] = sum(safe_value(model.Ywind[w]) * model.CapWind_CAPEX_M[w]
                                   for w in model.w if safe_value(model.Ywind[w]) is not None)
    results['Total_CapScha'] = {j: safe_value(model.Pcha[j]) for j in model.j}
    results['Total_CapSdis'] = {j: safe_value(model.Pdis[j]) for j in model.j}
    results['Total_EcapS'] = {j: safe_value(model.Ecap[j]) for j in model.j}

    # Collect generation results
    results['Total_GenPV'] = sum(safe_value(model.GenPV[h]) for h in model.h if safe_value(model.GenPV[h]) is not None)
    results['Total_GenWind'] = sum(safe_value(model.GenWind[h]) for h in model.h if safe_value(model.GenWind[h]) is not None)
    results['Total_GenS'] = {j: sum(safe_value(model.PD[h, j]) for h in model.h if safe_value(model.PD[h, j]) is not None) for j in model.j}

    # Collect power flows for storage technologies
    results['SummaryPC'] = {(h, j): safe_value(model.PC[h, j]) for h in model.h for j in model.j if safe_value(model.PC[h, j]) is not None}
    results['SummaryPD'] = {(h, j): safe_value(model.PD[h, j]) for h in model.h for j in model.j if safe_value(model.PD[h, j]) is not None}
    results['SummarySOC'] = {(h, j): safe_value(model.SOC[h, j]) for h in model.h for j in model.j if safe_value(model.SOC[h, j]) is not None}

    # Collect dispatch results
    results['SolarPVGen'] = {h: safe_value(model.GenPV[h]) for h in model.h if safe_value(model.GenPV[h]) is not None}
    results['WindGen'] = {h: safe_value(model.GenWind[h]) for h in model.h if safe_value(model.GenWind[h]) is not None}
    results['SolarPVCurt'] = {h: safe_value(model.CurtPV[h]) for h in model.h if safe_value(model.CurtPV[h]) is not None}
    results['WindCurt'] = {h: safe_value(model.CurtWind[h]) for h in model.h if safe_value(model.CurtWind[h]) is not None}
    results['GenGasCC'] = {h: safe_value(model.GenCC[h]) for h in model.h if safe_value(model.GenCC[h]) is not None}

    # Collect selected plants
    results['SelectedSolarPV'] = {k: safe_value(model.Ypv[k]) for k in model.k if safe_value(model.Ypv[k]) is not None}
    results['SelectedWind'] = {w: safe_value(model.Ywind[w]) for w in model.w if safe_value(model.Ywind[w]) is not None}

    return results

def run_solver(model, log_file_path='solver_log.txt', mipgap=0, num_runs=10):
    solver = SolverFactory('glpk')  
    options = {'mipgap': mipgap}  

    results_over_runs = []  
    best_result = None       
    best_objective_value = float('inf')  # Initialize with a high value

    # Solve the model for each run
    for run in range(num_runs):
        # Set the target for GenMix_Target (0.70 + 0.05 * run) similar to GAMS
        target_value = 0.70 + 0.05 * run
        model.GenMix_Target.set_value(target_value)  

        print(f"Running optimization for GenMix_Target = {target_value:.2f}")

        # Solve the model
        result = solver.solve(model, tee=True, keepfiles=True, logfile=log_file_path, options=options)

        # Check if the solver found an optimal solution
        if (result.solver.status == SolverStatus.ok) and (result.solver.termination_condition == TerminationCondition.optimal):
            # Collect the results for this run
            run_results = collect_results(model)
            run_results['GenMix_Target'] = target_value  
            results_over_runs.append(run_results)  

            # Check if this is the best result so far
            if 'Total_Cost' in run_results and run_results['Total_Cost'] < best_objective_value:
                best_objective_value = run_results['Total_Cost']
                best_result = run_results
        else:
            print(f"Solver did not find an optimal solution for GenMix_Target = {target_value:.2f}. Skipping this run.")
    
    return results_over_runs, best_result  


# ---------------------------------------------------------------------------------
# Export results to CSV files
def export_results(model, iso_name, case):
    output_dir = f'C:/NREL_Projects/LDES/SDOM/Open-source/GLPK/{iso_name}/'
    os.makedirs(output_dir, exist_ok=True)

    # Create dictionaries to store results
    summary_results = {}
    gen_results = {'Hour': [], 'Solar PV Generation (MW)': [], 'Solar PV Curtailment (MW)': [],
                   'Wind Generation (MW)': [], 'Wind Curtailment (MW)': [], 'Gas CC Generation (MW)': [],
                   'Power from Storage and Gas CC to Storage (MW)': []}

    storage_results = {'Hour': [], 'Technology': [], 'Charging power (MW)': [], 'Discharging power (MW)': [],
                       'State of charge (MWh)': []}

    # Function to get the value of a variable, or return None if uninitialized
    def safe_value(var):
        if isinstance(var, (int, float)):  
            return var
        return value(var) if var is not None and var.value is not None else None

    # Extract results for generation
    for h in model.h:
        solar_gen = safe_value(model.GenPV[h])
        solar_curt = safe_value(model.CurtPV[h])
        wind_gen = safe_value(model.GenWind[h])
        wind_curt = safe_value(model.CurtWind[h])
        gas_cc_gen = safe_value(model.GenCC[h])

        # If any generation data is uninitialized, skip this hour
        if solar_gen is None or solar_curt is None or wind_gen is None or wind_curt is None or gas_cc_gen is None:
            continue

        gen_results['Hour'].append(h)
        gen_results['Solar PV Generation (MW)'].append(solar_gen)
        gen_results['Solar PV Curtailment (MW)'].append(solar_curt)
        gen_results['Wind Generation (MW)'].append(wind_gen)
        gen_results['Wind Curtailment (MW)'].append(wind_curt)
        gen_results['Gas CC Generation (MW)'].append(gas_cc_gen)

        # Include power sent to storage
        power_to_storage = sum(safe_value(model.PC[h, j]) or 0 for j in model.j) - sum(safe_value(model.PD[h, j]) or 0 for j in model.j)
        gen_results['Power from Storage and Gas CC to Storage (MW)'].append(power_to_storage)

    # Extract storage results
    for h in model.h:
        for j in model.j:
            charge_power = safe_value(model.PC[h, j])
            discharge_power = safe_value(model.PD[h, j])
            soc = safe_value(model.SOC[h, j])

            # If any storage data is uninitialized, skip this hour and technology
            if charge_power is None or discharge_power is None or soc is None:
                continue

            storage_results['Hour'].append(h)
            storage_results['Technology'].append(j)
            storage_results['Charging power (MW)'].append(charge_power)
            storage_results['Discharging power (MW)'].append(discharge_power)
            storage_results['State of charge (MWh)'].append(soc)

    # Save results to CSV files
    if gen_results['Hour']:
        with open(output_dir + f'OutputUpdatedGeneration_SDOM_{case}_.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=gen_results.keys())
            writer.writeheader()
            writer.writerows([dict(zip(gen_results, t)) for t in zip(*gen_results.values())])

    if storage_results['Hour']:
        with open(output_dir + f'OutputUpdatedStorage_SDOM_{case}_.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=storage_results.keys())
            writer.writeheader()
            writer.writerows([dict(zip(storage_results, t)) for t in zip(*storage_results.values())])

    # Extract summary data
    total_cost = safe_value(model.Obj())
    total_gas_cc_capacity = safe_value(model.CapCC)
    total_solar_capacity = sum(safe_value(model.GenPV[h]) or 0 for h in model.h)
    total_wind_capacity = sum(safe_value(model.GenWind[h]) or 0 for h in model.h)

    if total_cost is not None and total_gas_cc_capacity is not None:
        summary_results['Total cost US$'] = total_cost
        summary_results['Total capacity of gas combined cycle units (MW)'] = total_gas_cc_capacity
        summary_results['Total capacity of solar PV units (MW)'] = total_solar_capacity
        summary_results['Total capacity of wind units (MW)'] = total_wind_capacity

        # Save summary to CSV
        with open(output_dir + f'OutputUpdatedSummary_SDOM_{case}_.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=summary_results.keys())
            writer.writeheader()
            writer.writerow(summary_results)


# ---------------------------------------------------------------------------------
# Main loop for handling scenarios and results exporting
def main():
    data = load_data()
    model = initialize_model(data)

    # Run initial optimization
    results_over_runs, best_result = run_solver(model)

    # Check if any valid result was found in the initial optimization
    #if best_result:
    #    print("Best initial run results:", best_result)
    #else:
    #    print("No optimal solution was found in the initial runs.")

    # Define scenarios for different iso, nuclear configurations, and target values
    iso = ['CAISO', 'ERCOT', 'ISONE', 'MISO', 'NYISO', 'PJM', 'SPP']
    nuclear = ['0', '1']
    target = ['0.00', '0.75', '0.80', '0.85', '0.90', '0.95', '1.00']

    # Loop over scenarios and solve the model for each
    for j in iso:
        for i in nuclear:
            for k in target:
                case = f"{j} Nuclear {i} Target {k}"
                print(f"Solving for {case}...")

                results_over_runs, best_result = run_solver(model)

                # Check if the best result was found for the current scenario
                if best_result:
                    print(f"Best result for {case}: {best_result}")
                    export_results(model, j, case)  
                else:
                    print(f"Solver did not find an optimal solution for {case}, skipping result export.")


# ---------------------------------------------------------------------------------
# Execute the main function
if __name__ == "__main__":
    main()

