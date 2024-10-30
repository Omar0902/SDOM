# -*- coding: utf-8 -*-
"""
Created on Tue Sep  24 13:46:19 2024

@author: ttran2
"""

from pyomo.environ import *
import pandas as pd
import csv
import os
import logging
import math
import matplotlib.pyplot as plt
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
from pyomo.opt import SolverResults
from pyomo.environ import value
from pyomo.util.infeasible import log_infeasible_constraints
from pyomo.environ import TransformationFactory

# ---------------------------------------------------------------------------------
# Data loading
def load_data():
    solar_plants = pd.read_csv('Set_k_SolarPV.csv', header=None)[0].tolist()
    wind_plants = pd.read_csv('Set_w_Wind.csv', header=None)[0].tolist()

    load_data = pd.read_csv('Load_hourly_2050.csv').round(5) # rounding to 5 decimal 
    nuclear_data = pd.read_csv('Nucl_hourly_2019.csv').round(5)
    large_hydro_data = pd.read_csv('lahy_hourly_2019.csv').round(5)
    other_renewables_data = pd.read_csv('otre_hourly_2019.csv').round(5)
    cf_solar = pd.read_csv('CFSolar_2050.csv').round(5)
    cf_wind = pd.read_csv('CFWind_2050.csv').round(5)
    cap_solar = pd.read_csv('CapSolar_2050.csv').round(5)
    cap_wind = pd.read_csv('CapWind_2050.csv').round(5)
    storage_data = pd.read_csv('StorageData_2050.csv', index_col=0).round(5)

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
# Safe value function for uninitialized variables/parameters
def safe_pyomo_value(var):
    """Return the value of a variable or expression if it is initialized, else return None."""
    try:
        return value(var) if var is not None else None
    except ValueError:
        return None

def initialize_model(data):
    model = ConcreteModel(name="SDOM_Model")

    # Solar plant ID alignment
    solar_plants_cf = data['cf_solar'].columns[1:].astype(str).tolist()
    solar_plants_cap = data['cap_solar']['sc_gid'].astype(str).tolist()
    common_solar_plants = list(set(solar_plants_cf) & set(solar_plants_cap))

    # Filter solar data and initialize model set
    complete_solar_data = data["cap_solar"][data["cap_solar"]['sc_gid'].astype(str).isin(common_solar_plants)]
    complete_solar_data = complete_solar_data.dropna(subset=['CAPEX_M', 'trans_cap_cost', 'FOM_M', 'capacity'])
    common_solar_plants_filtered = complete_solar_data['sc_gid'].astype(str).tolist()
    model.k = Set(initialize=common_solar_plants_filtered)

    # Load the solar capacities
    cap_solar_dict = complete_solar_data.set_index('sc_gid')['capacity'].to_dict()

    # Filter the dictionary to ensure only valid keys are included
    default_capacity_value = 0.0
    filtered_cap_solar_dict = {k: cap_solar_dict.get(k, default_capacity_value) for k in model.k}
    model.CapSolar_capacity = Param(model.k, initialize=filtered_cap_solar_dict)

    # Wind plant ID alignment
    wind_plants_cf = data['cf_wind'].columns[1:].astype(str).tolist()
    wind_plants_cap = data['cap_wind']['sc_gid'].astype(str).tolist()
    common_wind_plants = list(set(wind_plants_cf) & set(wind_plants_cap))

    # Filter wind data and initialize model set
    complete_wind_data = data["cap_wind"][data["cap_wind"]['sc_gid'].astype(str).isin(common_wind_plants)]
    complete_wind_data = complete_wind_data.dropna(subset=['CAPEX_M', 'trans_cap_cost', 'FOM_M', 'capacity'])
    common_wind_plants_filtered = complete_wind_data['sc_gid'].astype(str).tolist()
    model.w = Set(initialize=common_wind_plants_filtered)

    # Load the wind capacities
    cap_wind_dict = complete_wind_data.set_index('sc_gid')['capacity'].to_dict()

    # Filter the dictionary to ensure only valid keys are included
    filtered_cap_wind_dict = {w: cap_wind_dict.get(w, default_capacity_value) for w in model.w}
    model.CapWind_capacity = Param(model.w, initialize=filtered_cap_wind_dict)
    
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
    model.r = Param(initialize=0.06)  # Discount rate
    model.GasPrice = Param(initialize=4.113894393)  # Gas prices (US$/MMBtu)
    model.HR = Param(initialize=6.4005)  # Heat rate for gas combined cycle (MMBtu/MWh)
    model.CapexGasCC = Param(initialize=940.6078576)  # Capex for gas combined cycle units (US$/kW)
    model.FOM_GasCC = Param(initialize=13.2516707)  # Fixed O&M for gas combined cycle (US$/kW-year)
    model.VOM_GasCC = Param(initialize=2.226321156)  # Variable O&M for gas combined cycle (US$/MWh)
    
    # GenMix_Target, mutable to change across multiple runs
    model.GenMix_Target = Param(initialize=1.00, mutable=True)  

    # Fixed Charge Rates (FCR) for VRE and Gas CC
    def fcr_rule(model, lifetime=30):
        return (model.r * (1 + model.r) ** lifetime) / ((1 + model.r) ** lifetime - 1)
    model.FCR_VRE = Param(initialize=fcr_rule(model))  # For VRE (solar and wind)
    model.FCR_GasCC = Param(initialize=fcr_rule(model))

    # Activation factors for nuclear, hydro, and other renewables
    model.AlphaNuclear = Param(initialize=1, mutable=True) 
    model.AlphaLargHy = Param(initialize=1)  # Control for large hydro generation
    model.AlphaOtheRe = Param(initialize=1)  # Control for other renewable generation
    
    # Battery life and cycling
    model.MaxCycles = Param(initialize=3250)

    # Load data initialization
    model.Load = Param(model.h, initialize=data["load_data"].set_index('*Hour')['Load'].to_dict())

    # Nuclear data initialization
    model.Nuclear = Param(model.h, initialize=data["nuclear_data"].set_index('*Hour')['Nuclear'].to_dict())

    # Large hydro data initialization
    model.LargeHydro = Param(model.h, initialize=data["large_hydro_data"].set_index('*Hour')['LargeHydro'].to_dict())

    # Other renewables data initialization
    model.OtherRenewables = Param(model.h, initialize=data["other_renewables_data"].set_index('*Hour')['OtherRenewables'].to_dict())

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
    model.GenPV = Var(model.h, domain=NonNegativeReals)  # Generated solar PV power
    model.CurtPV = Var(model.h, domain=NonNegativeReals)  # Curtailment for solar PV power
    model.GenWind = Var(model.h, domain=NonNegativeReals)  # Generated wind power
    model.CurtWind = Var(model.h, domain=NonNegativeReals)  # Curtailment for wind power
    model.CapCC = Var(domain=NonNegativeReals)  # Capacity of backup gas combined cycle units
    model.GenCC = Var(model.h, domain=NonNegativeReals)  # Generation from gas combined cycle units
    
    model.SupplySlack = Var(model.h, domain=NonNegativeReals)  # Slack variable -- to be removed!
    model.GenMixSlack = Var(domain=NonNegativeReals)  # Slack variable
    
    # Storage-related variables
    model.PC = Var(model.h, model.j, domain=NonNegativeReals)  # Charging power for storage technology j in hour h
    model.PD = Var(model.h, model.j, domain=NonNegativeReals)  # Discharging power for storage technology j in hour h
    model.SOC = Var(model.h, model.j, domain=NonNegativeReals)  # State-of-charge for storage technology j in hour h
    model.Pcha = Var(model.j, domain=NonNegativeReals, bounds=(0, None), initialize=0.5) # Charging capacity for storage technology j
    model.Pdis = Var(model.j, domain=NonNegativeReals, bounds=(0, None), initialize=0.5) # Discharging capacity for storage technology j
    model.Ecap = Var(model.j, domain=NonNegativeReals)  # Energy capacity for storage technology j

    # Capacity selection variables with continuous bounds between 0 and 1
    model.Ypv = Var(model.k, domain=NonNegativeReals, bounds=(0, 1))  # Solar PV plant selection (fractional)
    model.Ywind = Var(model.w, domain=NonNegativeReals, bounds=(0, 1))  # Wind plant selection (fractional)
    model.Ystorage = Var(model.j, model.h, domain=NonNegativeReals, bounds=(0, 1))  # Storage selection (fractional)

    for pv in model.Ypv:
        if model.Ypv[pv].value is None:
            model.Ypv[pv].set_value(0)  # Initialize to 0 if not already set
            
    for wind in model.Ywind:
        if model.Ywind[wind].value is None:
            model.Ywind[wind].set_value(0)  # Initialize to 0 if not already set
            
    for s in model.Ystorage:
        if model.Ystorage[s].value is None:
            model.Ystorage[s].set_value(0)  # Initialize to 0 if not already set

    # Upper bound for CapCC: based on load and renewable generation
    def capcc_upper_bound_rule(model):
        return model.CapCC <= max(
            model.Load[h] - value(model.AlphaNuclear) * model.Nuclear[h] 
            - model.AlphaLargHy * model.LargeHydro[h] 
            - model.AlphaOtheRe * model.OtherRenewables[h] 
            for h in model.h
        )

    model.CapCCUpperBound = Constraint(rule=capcc_upper_bound_rule)

    # Sanity checks of loaded and initialized data ---------------------------------
    # Inspect the first few hours of data
    for h in range(1, 10):
        print(f"Hour {h}: Load={model.Load[h]}, Nuclear={model.Nuclear[h]}, LargeHydro={model.LargeHydro[h]}, OtherRenewables={model.OtherRenewables[h]}")
    
    # Check for NaN or None values across all hours
    def check_missing_data(model):
        for h in model.h:
            load_value = model.Load[h]
            nuclear_value = model.Nuclear[h]
            hydro_value = model.LargeHydro[h]
            other_re_value = model.OtherRenewables[h]
    
            # Check for NaN or None values directly
            if pd.isna(load_value) or pd.isna(nuclear_value) or pd.isna(hydro_value) or pd.isna(other_re_value):
                print(f"Hour {h} has NaN values.")
            elif load_value is None or nuclear_value is None or hydro_value is None or other_re_value is None:
                print(f"Hour {h} has None values.")
    
    check_missing_data(model)
    
    # Extract values for analysis and bounds checking
    load_values = [model.Load[h] for h in model.h]
    nuclear_values = [model.Nuclear[h] for h in model.h]
    hydro_values = [model.LargeHydro[h] for h in model.h]
    other_re_values = [model.OtherRenewables[h] for h in model.h]
    
    print(f"Load range: {min(load_values)} to {max(load_values)}")
    print(f"Nuclear range: {min(nuclear_values)} to {max(nuclear_values)}")
    print(f"LargeHydro range: {min(hydro_values)} to {max(hydro_values)}")
    print(f"OtherRenewables range: {min(other_re_values)} to {max(other_re_values)}")
    
    # Check if all hours have values for each parameter
    def check_missing_hours(model):
        missing_hours = [h for h in model.h if pd.isna(model.Load[h]) or pd.isna(model.Nuclear[h]) or pd.isna(model.LargeHydro[h]) or pd.isna(model.OtherRenewables[h])]
        
        if missing_hours:
            print(f"Missing data for hours: {missing_hours}")
        else:
            print("All hours have data.")

    check_missing_hours(model)
    
    plt.figure(figsize=(10, 6))
    plt.plot(load_values, label="Load", linewidth=1.5)
    plt.plot(nuclear_values, label="Nuclear", linewidth=1.5)
    plt.plot(hydro_values, label="LargeHydro", linewidth=1.5)
    plt.plot(other_re_values, label="OtherRenewables", linewidth=1.5)
    plt.xlabel("Hour")
    plt.ylabel("Generation (MW)")
    plt.title("Generation profiles over time")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.show()

    # Check bounds of variables
    print("\nBounds check for variables:")
    for pv in model.Ypv:
        lb, ub = model.Ypv[pv].bounds
        print(f"Ypv[{pv}]: Bounds = ({lb}, {ub}), Initial Value = {model.Ypv[pv].value}")
    
    for wind in model.Ywind:
        lb, ub = model.Ywind[wind].bounds
        print(f"Ywind[{wind}]: Bounds = ({lb}, {ub}), Initial Value = {model.Ywind[wind].value}")
    
    for j in model.j:
        lb, ub = model.Pcha[j].bounds
        print(f"Pcha[{j}]: Bounds = ({lb}, {ub}), Initial Value = {model.Pcha[j].value}")
        lb, ub = model.Pdis[j].bounds
        print(f"Pdis[{j}]: Bounds = ({lb}, {ub}), Initial Value = {model.Pdis[j].value}")
    #------------------------------------------------------------------------------    

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
    # This constraint ensures that the total supply (load, charging) matches the generation (solar, wind, gas, discharging).
    #def supply_balance_rule(model, h):
        # Including nuclear, hydro, and other renewables into the supply balance
    #    return (model.Load[h] + sum(model.PC[h, j] for j in model.j)
    #            - model.AlphaNuclear * model.Nuclear[h]
    #            - model.AlphaLargHy * model.LargeHydro[h]
    #            - model.AlphaOtheRe * model.OtherRenewables[h]
    #            - model.GenPV[h] - model.GenWind[h]
    #            - sum(model.PD[h, j] for j in model.j)
    #            - model.GenCC[h]) == 0
    
    #model.SupplyBalance = Constraint(model.h, rule=supply_balance_rule)

    def supply_balance_rule(model, h):
        return (model.Load[h] + sum(model.PC[h, j] for j in model.j)
                - model.AlphaNuclear * model.Nuclear[h]
                - model.AlphaLargHy * model.LargeHydro[h]
                - model.AlphaOtheRe * model.OtherRenewables[h]
                - model.GenPV[h] - model.GenWind[h]
                - sum(model.PD[h, j] for j in model.j)
                - model.GenCC[h] + model.SupplySlack[h]) == 0  # Add slack

    model.SupplyBalance = Constraint(model.h, rule=supply_balance_rule)
    
    # This constraint ensures that the total generation from gas does not exceed the GenMix_Target percentage.
    #def genmix_share_rule(model):
    #    total_gen = sum(model.Load[h] + sum(model.PC[h, j] for j in model.j) - sum(model.PD[h, j] for j in model.j) for h in model.h)
    #    total_gas_gen = sum(model.GenCC[h] for h in model.h)
    #    return total_gas_gen <= (1 - model.GenMix_Target) * total_gen
    
    #model.GenMix_Share = Constraint(rule=genmix_share_rule)
    
    def genmix_share_rule(model):
        total_gen = sum(model.Load[h] + sum(model.PC[h, j] for j in model.j) - sum(model.PD[h, j] for j in model.j) for h in model.h)
        total_gas_gen = sum(model.GenCC[h] for h in model.h)
        return total_gas_gen <= (1 - model.GenMix_Target) * total_gen + model.GenMixSlack  # Add slack
    
    model.GenMix_Share = Constraint(rule=genmix_share_rule)
    
    # Ensure the solar generation and curtailment match the available solar capacity for each hour.
    def solar_balance_rule(model, h):
        return model.GenPV[h] + model.CurtPV[h] == sum(model.CFSolar[h, k] * model.CapSolar_capacity[k] * model.Ypv[k] for k in model.k)
    
    model.SolarBal = Constraint(model.h, rule=solar_balance_rule)    
    
    # Ensure the wind generation and curtailment match the available wind capacity for each hour.
    def wind_balance_rule(model, h):
        return model.GenWind[h] + model.CurtWind[h] == sum(model.CFWind[h, w] * model.CapWind_capacity[w] * model.Ywind[w] for w in model.w)
    
    model.WindBal = Constraint(model.h, rule=wind_balance_rule)
   
    # Ensure the gas combined cycle (CapCC) can generate enough electricity when needed
    def backup_gen_rule(model, h):
        return model.CapCC >= model.GenCC[h]
    
    model.BackupGen = Constraint(model.h, rule=backup_gen_rule)
    
    # Keep track of the state of charge for storage across time - charging and discharging
    def soc_balance_rule(model, h, j):
        if h > 1:
            return model.SOC[h, j] == model.SOC[h - 1, j] + sqrt(model.StorageData['Eff', j]) * model.PC[h, j] - model.PD[h, j] / sqrt(model.StorageData['Eff', j])
        else:
            return Constraint.Skip  # Skip for the first hour (initial state handled separately)
    
    model.SOCBalance = Constraint(model.h, model.j, rule=soc_balance_rule)
    
    # Set the initial state of charge to 0 at the start of the simulation
    def soc_initial_balance_rule(model, j):
        return model.SOC[1, j] == 0
    
    model.SOCInitialBalance = Constraint(model.j, rule=soc_initial_balance_rule)
    
    # Ensure that the charging and discharging power do not exceed storage limits
    model.MaxChargePower = Constraint(model.h, model.j, rule=lambda m, h, j: m.PC[h, j] <= m.StorageData['Max_P', j] * m.Ystorage[j, h])
    model.MaxDischargePower = Constraint(model.h, model.j, rule=lambda m, h, j: m.PD[h, j] <= m.StorageData['Max_P', j] * (1 - m.Ystorage[j, h]))
    
    # Constraints on the maximum charging (Pcha) and discharging (Pdis) power for each technology
    model.MaxPcha = Constraint(model.j, rule=lambda m, j: m.Pcha[j] <= m.StorageData['Max_P', j])
    model.MaxPdis = Constraint(model.j, rule=lambda m, j: m.Pdis[j] <= m.StorageData['Max_P', j])
    
    # Ensure energy capacity remains within the minimum and maximum allowable values.
    model.MinEcap = Constraint(model.j, rule=lambda m, j: m.Ecap[j] >= m.StorageData['Min_Duration', j] * m.Pdis[j] / sqrt(m.StorageData['Eff', j]))
    model.MaxEcap = Constraint(model.j, rule=lambda m, j: m.Ecap[j] <= m.StorageData['Max_Duration', j] * m.Pdis[j] / sqrt(m.StorageData['Eff', j]))
    
    return model

# ---------------------------------------------------------------------------------
# Results collection function
def collect_results(model):
    results = {}
    results['Total_Cost'] = safe_pyomo_value(model.Obj.expr)

    # Collect capacity and generation results
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
    
    # Collect slack variables -- to be removed!
    results['SupplySlack'] = {h: safe_pyomo_value(model.SupplySlack[h]) for h in model.h}
    results['GenMixSlack'] = safe_pyomo_value(model.GenMixSlack)

    return results

# Run solver function
def run_solver(model, log_file_path='solver_log.txt', num_runs=3):
    solver = SolverFactory('cbc', executable='C:/NREL_Projects/LDES/SDOM/Open-source/CBC/cbc.exe')  
    solver.options['loglevel'] = 3
    #solver.options['presolve'] = 'on'
    
    # Apply transformations to model
    # TransformationFactory('core.relax_integer_vars').apply_to(model)
    # TransformationFactory('contrib.deactivate_trivial_constraints').apply_to(model)

    # Export the model to an LP file
    model.write('model.lp', io_options={'symbolic_solver_labels': True})
    
    results_over_runs = []  
    best_result = None       
    best_objective_value = float('inf')  

    for run in range(num_runs):
        target_value = 0.70 + 0.05 * run
        model.GenMix_Target.set_value(target_value)  

        print(f"Running optimization for GenMix_Target = {target_value:.2f}")
        result = solver.solve(model, tee=True, keepfiles=True, logfile=log_file_path)

        if (result.solver.status == SolverStatus.ok) and (result.solver.termination_condition == TerminationCondition.optimal):
            # If the solution is optimal, collect the results
            run_results = collect_results(model)
            run_results['GenMix_Target'] = target_value  
            results_over_runs.append(run_results)
            
            # Calculate the final SupplySlack as the sum across all hours
            total_supply_slack = sum(run_results['SupplySlack'].values())
            print(f"Total SupplySlack value: {total_supply_slack}")
            
            print(f"GenMixSlack value: {run_results['GenMixSlack']}")

            # Update the best result if it found a better one
            if 'Total_Cost' in run_results and run_results['Total_Cost'] < best_objective_value:
                best_objective_value = run_results['Total_Cost']
                best_result = run_results
        else:
            print(f"Solver did not find an optimal solution for GenMix_Target = {target_value:.2f}.")
            
            # Log infeasible constraints for debugging
            print("Logging infeasible constraints...")
            logging.basicConfig(level=logging.INFO)
            log_infeasible_constraints(model)
    
    return results_over_runs, best_result

# ---------------------------------------------------------------------------------
# Export results to CSV files
def export_results(model, iso_name, case):
    output_dir = f'C:/NREL_Projects/LDES/SDOM/Open-source/CBC/{iso_name}/'
    os.makedirs(output_dir, exist_ok=True)

    # Initialize results dictionaries
    gen_results = {'Hour': [], 'Solar PV Generation (MW)': [], 'Solar PV Curtailment (MW)': [], 
                   'Wind Generation (MW)': [], 'Wind Curtailment (MW)': [], 
                   'Gas CC Generation (MW)': [], 'Power from Storage and Gas CC to Storage (MW)': []}

    storage_results = {'Hour': [], 'Technology': [], 'Charging power (MW)': [], 
                       'Discharging power (MW)': [], 'State of charge (MWh)': []}

    summary_results = {}

    # Extract generation results
    for h in model.h:
        solar_gen = safe_pyomo_value(model.GenPV[h])
        solar_curt = safe_pyomo_value(model.CurtPV[h])
        wind_gen = safe_pyomo_value(model.GenWind[h])
        wind_curt = safe_pyomo_value(model.CurtWind[h])
        gas_cc_gen = safe_pyomo_value(model.GenCC[h])

        if None not in [solar_gen, solar_curt, wind_gen, wind_curt, gas_cc_gen]:
            gen_results['Hour'].append(h)
            gen_results['Solar PV Generation (MW)'].append(solar_gen)
            gen_results['Solar PV Curtailment (MW)'].append(solar_curt)
            gen_results['Wind Generation (MW)'].append(wind_gen)
            gen_results['Wind Curtailment (MW)'].append(wind_curt)
            gen_results['Gas CC Generation (MW)'].append(gas_cc_gen)

            power_to_storage = sum(safe_pyomo_value(model.PC[h, j]) or 0 for j in model.j) - sum(safe_pyomo_value(model.PD[h, j]) or 0 for j in model.j)
            gen_results['Power from Storage and Gas CC to Storage (MW)'].append(power_to_storage)

    # Extract storage results
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
    total_cost = safe_pyomo_value(model.Obj())
    total_gas_cc_capacity = safe_pyomo_value(model.CapCC)
    total_solar_capacity = sum(safe_pyomo_value(model.GenPV[h]) or 0 for h in model.h)
    total_wind_capacity = sum(safe_pyomo_value(model.GenWind[h]) or 0 for h in model.h)

    if total_cost is not None and total_gas_cc_capacity is not None:
        summary_results['Total cost US$'] = total_cost
        summary_results['Total capacity of gas combined cycle units (MW)'] = total_gas_cc_capacity
        summary_results['Total capacity of solar PV units (MW)'] = total_solar_capacity
        summary_results['Total capacity of wind units (MW)'] = total_wind_capacity

    # Save generation results to CSV
    if gen_results['Hour']:
        with open(output_dir + f'OutputGeneration_{case}.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=gen_results.keys())
            writer.writeheader()
            writer.writerows([dict(zip(gen_results, t)) for t in zip(*gen_results.values())])

    # Save storage results to CSV
    if storage_results['Hour']:
        with open(output_dir + f'OutputStorage_{case}.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=storage_results.keys())
            writer.writeheader()
            writer.writerows([dict(zip(storage_results, t)) for t in zip(*storage_results.values())])

    # Save summary results to CSV
    if summary_results:
        with open(output_dir + f'OutputSummary_{case}.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=summary_results.keys())
            writer.writeheader()
            writer.writerow(summary_results)

# ---------------------------------------------------------------------------------
# Main loop for handling scenarios and results exporting
def main():
    data = load_data()  
    model = initialize_model(data)  

    iso = ['CAISO']  
    nuclear = ['0', '1']
    target = ['0.75', '0.95']  

    # Loop over each scenario combination and solve the model
    for j in iso:
        for i in nuclear:
            for k in target:
                case = f"{j}_Nuclear_{i}_Target_{k}"
                print(f"Solving for {case}...")

                results_over_runs, best_result = run_solver(model)

                if best_result:
                    print(f"Best result for {case}: {best_result}")
                    export_results(model, j, case)  
                else:
                    print(f"Solver did not find an optimal solution for {case}, skipping result export.")

# ---------------------------------------------------------------------------------
# Execute the main function
if __name__ == "__main__":
    main()

