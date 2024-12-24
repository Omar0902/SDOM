
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
from pyomo.environ import Binary
from pyomo.util.infeasible import log_infeasible_constraints
from pyomo.environ import TransformationFactory
from pyomo.core import Var, Constraint
from pyomo.core.expr.visitor import identify_variables
from pyomo.util.model_size import build_model_size_report
from pyomo.environ import UnitInterval

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
    # model.h = RangeSet(1, 8760)
    model.h = RangeSet(1, 24)
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
    model.EUE_max = Param(initialize=100, mutable=True) # Maximum EUE (in MWh)
    
    # GenMix_Target, mutable to change across multiple runs
    model.GenMix_Target = Param(initialize=1.00, mutable=True)  

    # Fixed Charge Rates (FCR) for VRE and Gas CC
    def fcr_rule(model, lifetime=30):
        return (model.r * (1 + model.r) ** lifetime) / ((1 + model.r) ** lifetime - 1)
    
    model.FCR_VRE = Param(initialize=fcr_rule(model))  
    model.FCR_GasCC = Param(initialize=fcr_rule(model))

    # Activation factors for nuclear, hydro, and other renewables
    model.AlphaNuclear = Param(initialize=1, mutable=True) 
    model.AlphaLargHy = Param(initialize=1)  # Control for large hydro generation
    model.AlphaOtheRe = Param(initialize=1)  # Control for other renewable generation
    
    # Battery life and cycling
    model.MaxCycles = Param(initialize=3250)

    # Load data initialization
    load_data = data["load_data"].set_index('*Hour')['Load'].to_dict()
    filtered_load_data = {h: load_data[h] for h in model.h if h in load_data}
    model.Load = Param(model.h, initialize=filtered_load_data)

    # Nuclear data initialization
    nuclear_data = data["nuclear_data"].set_index('*Hour')['Nuclear'].to_dict()
    filtered_nuclear_data = {h: nuclear_data[h] for h in model.h if h in nuclear_data}
    model.Nuclear = Param(model.h, initialize=filtered_nuclear_data)

    # Large hydro data initialization
    large_hydro_data = data["large_hydro_data"].set_index('*Hour')['LargeHydro'].to_dict()
    filtered_large_hydro_data = {h: large_hydro_data[h] for h in model.h if h in large_hydro_data}
    model.LargeHydro = Param(model.h, initialize=filtered_large_hydro_data)

    # Other renewables data initialization
    other_renewables_data = data["other_renewables_data"].set_index('*Hour')['OtherRenewables'].to_dict()
    filtered_other_renewables_data = {h: other_renewables_data[h] for h in model.h if h in other_renewables_data}
    model.OtherRenewables = Param(model.h, initialize=filtered_other_renewables_data)

    # Solar capacity factor initialization
    cf_solar_melted = data["cf_solar"].melt(id_vars='Hour', var_name='plant', value_name='CF')
    cf_solar_filtered = cf_solar_melted[
        (cf_solar_melted['plant'].isin(model.k)) & (cf_solar_melted['Hour'].isin(model.h))
    ]
    cf_solar_dict = cf_solar_filtered.set_index(['Hour', 'plant'])['CF'].to_dict()
    model.CFSolar = Param(model.h, model.k, initialize=cf_solar_dict)

    # Wind capacity factor initialization
    cf_wind_melted = data["cf_wind"].melt(id_vars='Hour', var_name='plant', value_name='CF')
    cf_wind_filtered = cf_wind_melted[
        (cf_wind_melted['plant'].isin(model.w)) & (cf_wind_melted['Hour'].isin(model.h))
    ]
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
    model.GenPV = Var(model.h, domain=NonNegativeReals, initialize=0)  # Generated solar PV power
    model.CurtPV = Var(model.h, domain=NonNegativeReals, initialize=0)  # Curtailment for solar PV power
    model.GenWind = Var(model.h, domain=NonNegativeReals, initialize=0)  # Generated wind power
    model.CurtWind = Var(model.h, domain=NonNegativeReals, initialize=0)  # Curtailment for wind power
    model.CapCC = Var(domain=NonNegativeReals, initialize=0)  # Capacity of backup GCC units
    model.GenCC = Var(model.h, domain=NonNegativeReals, initialize=0)  # Generation from GCC units
    model.LoadShed = Var(model.h, domain=NonNegativeReals, initialize=0) # Load shedding
    model.EUE = Var(domain=NonNegativeReals) # Expected Unserved Energy
    
    # Storage-related variables
    model.PC = Var(model.h, model.j, domain=NonNegativeReals, initialize=0)  # Charging power for storage technology j in hour h
    model.PD = Var(model.h, model.j, domain=NonNegativeReals, initialize=0)  # Discharging power for storage technology j in hour h
    model.SOC = Var(model.h, model.j, domain=NonNegativeReals, initialize=0)  # State-of-charge for storage technology j in hour h
    model.Pcha = Var(model.j, domain=NonNegativeReals, initialize=0) # Charging capacity for storage technology j
    model.Pdis = Var(model.j, domain=NonNegativeReals, initialize=0) # Discharging capacity for storage technology j
    model.Ecap = Var(model.j, domain=NonNegativeReals, initialize=0)  # Energy capacity for storage technology j

    # Capacity selection variables with continuous bounds between 0 and 1
    model.Ypv = Var(model.k, domain=NonNegativeReals, bounds=(0, 1), initialize=0)
    model.Ywind = Var(model.w, domain=NonNegativeReals, bounds=(0, 1), initialize=0)
    model.Ystorage = Var(model.j, model.h, domain=Binary, initialize=0)  # Storage selection (binary)
    # model.Ystorage = Var(model.j, model.h, domain=UnitInterval, initialize=0) # Partial charging

    for pv in model.Ypv:
        if model.Ypv[pv].value is None:
            model.Ypv[pv].set_value(0)  # Initialize to 0 if not already set
            
    for wind in model.Ywind:
        if model.Ywind[wind].value is None:
            model.Ywind[wind].set_value(0)  # Initialize to 0 if not already set
            
    for s in model.Ystorage:
        if model.Ystorage[s].value is None:
            model.Ystorage[s].set_value(0)  # Initialize to 0 if not already set

    

    # Define the objective function ---------------------------------------------
    def objective_rule(model):
        # Annual Fixed Costs
        fixed_costs = (
            # Solar PV Capex and Fixed O&M
            sum(
                (model.FCR_VRE * (1000*model.CapSolar_CAPEX_M[k] + model.CapSolar_trans_cap_cost[k]) + 1000*model.CapSolar_FOM_M[k])
                * model.CapSolar_capacity[k] * model.Ypv[k]
                for k in model.k
            )
            +
            # Wind Capex and Fixed O&M
            sum(
                (model.FCR_VRE * (1000*model.CapWind_CAPEX_M[w] + model.CapWind_trans_cap_cost[w]) + 1000*model.CapWind_FOM_M[w])
                * model.CapWind_capacity[w] * model.Ywind[w]
                for w in model.w
            )
            +
            # Storage Capex and Fixed O&M
            sum(
                model.CRF[j]*(
                    1000*model.StorageData['CostRatio', j]*model.StorageData['P_Capex', j]*model.Pcha[j]
                    + 1000*(1 - model.StorageData['CostRatio', j])*model.StorageData['P_Capex', j]*model.Pdis[j]
                    + 1000*model.StorageData['E_Capex', j]*model.Ecap[j]
                )
                + 1000*model.StorageData['CostRatio', j]*model.StorageData['FOM', j]*model.Pcha[j]
                + 1000*(1 - model.StorageData['CostRatio', j])*model.StorageData['FOM', j]*model.Pdis[j]
                for j in model.j
            )
            +
            # Gas CC Capex and Fixed O&M
            model.FCR_GasCC*1000*model.CapexGasCC*model.CapCC
            + 1000*model.FOM_GasCC*model.CapCC
        )
    
        # Variable Costs (Gas CC Fuel & VOM, Storage VOM)
        variable_costs = sum(
            model.GasPrice * model.HR * model.GenCC[h]
            + model.VOM_GasCC * model.GenCC[h]
            + sum(model.StorageData['VOM', j]*model.PD[h, j] for j in model.j)
            for h in model.h
        )
    
        return fixed_costs + variable_costs
    
    model.Obj = Objective(rule=objective_rule, sense=minimize)
   
    # Define constraints ---------------------------------------------------------
    # Ensure that the total supply (load, charging) matches the generation (solar, wind, gas, discharging).
    def supply_balance_rule(model, h):
        return (
            model.Load[h] 
            + sum(model.PC[h, j] for j in model.j)
            - model.AlphaNuclear * model.Nuclear[h]
            - model.AlphaLargHy * model.LargeHydro[h]
            - model.AlphaOtheRe * model.OtherRenewables[h]
            - model.GenPV[h]
            - model.GenWind[h]
            - sum(model.PD[h, j] for j in model.j)
            - model.GenCC[h]
        ) == 0

    model.SupplyBalance = Constraint(model.h, rule=supply_balance_rule)

    # Enforce the upper bound for CapCC
    model.maxRemainingLoad = Var(domain = NonNegativeReals)

    def max_remainingLoad(model, h):
        return model.maxRemainingLoad >= model.Load[h] + model.AlphaNuclear*model.Nuclear[h] + model.AlphaLargHy*model.LargeHydro[h]+ model.AlphaOtheRe*model.OtherRenewables[h]
    model.max_remainingLoad = Constraint(model.h, rule=max_remainingLoad)

    def max_capcc(model):
        return model.CapCC - model.maxRemainingLoad <= 0 
    model.max_capcc = Constraint(rule=max_capcc)

    # Define critical load as part of the load for essential services 
    critical_load_percentage = 0.3 # 30% of the total load
    total_critical_load = sum(value(model.Load[h]) for h in model.h) * critical_load_percentage
    
    # PCLS Constraint:
    PCLS_target = 0.9 # 90% of the total load
    # LoadShed[h] = how much load is unmet during hour h
    
    def pcls_constraint_rule(model):
        return sum(model.Load[h] - model.LoadShed[h] for h in model.h) \
               >= PCLS_target * total_critical_load
    
    model.PCLS_Constraint = Constraint(rule=pcls_constraint_rule)
    
    # EUE Constraint:
    def eue_constraint_rule(model):
        return model.EUE == sum(model.LoadShed[h] for h in model.h)
    model.EUE_Constraint = Constraint(rule=eue_constraint_rule)
    
    model.MaxEUE_Constraint = Constraint(expr=model.EUE <= model.EUE_max)
    
    # Ensure that the total generation from gas does not exceed the GenMix_Target percentage
    def genmix_share_rule(model):
        return sum(model.GenCC[h] for h in model.h) <= (1 - model.GenMix_Target) * sum(model.Load[h] +sum(model.PC[h,j] - model.PD[h,j] for j in model.j) for h in model.h)
    
    model.GenMix_Share = Constraint(rule=genmix_share_rule)
    
    # Ensure the solar generation and curtailment match the available solar capacity for each hour
    def solar_balance_rule(model, h):
        return model.GenPV[h] + model.CurtPV[h] == sum(model.CFSolar[h, k] * model.CapSolar_capacity[k] * model.Ypv[k] for k in model.k)    
    
    model.SolarBal = Constraint(model.h, rule=solar_balance_rule)    
    
    # Ensure the wind generation and curtailment match the available wind capacity for each hour.
    def wind_balance_rule(model, h):
        return model.GenWind[h] + model.CurtWind[h] == sum(model.CFWind[h, w] * model.CapWind_capacity[w] * model.Ywind[w] for w in model.w)
    
    model.WindBal = Constraint(model.h, rule=wind_balance_rule)
   
    # Backup gas generation cannot produce more than its capacity
    def backup_gen_rule(model, h):
        if model.GenCC[h].value is None or model.CapCC.value is None:
            return Constraint.Skip
        else:
            return model.CapCC >= model.GenCC[h]
        
    model.BackupGen = Constraint(model.h, rule=backup_gen_rule)
    
    # Keep track of the state of charge for storage across time - charging and discharging
    # Max SOC
    def max_soc_rule(model, h, j):
        return model.SOC[h,j] <= model.Ecap[j]
    
    model.MaxSOC = Constraint(model.h, model.j, rule=max_soc_rule)
    
    # SOC Balance
    def soc_balance_rule(model, h, j):
        if h > 1:
            return model.SOC[h, j] == model.SOC[h-1, j] \
                   + sqrt(model.StorageData['Eff', j]) * model.PC[h, j] \
                   - model.PD[h, j] / sqrt(model.StorageData['Eff', j])
        else:
            # cyclical or initial condition
            return model.SOC[h, j] == model.SOC[max(model.h), j] \
                   + sqrt(model.StorageData['Eff', j]) * model.PC[h, j] \
                   - model.PD[h, j] / sqrt(model.StorageData['Eff', j])
    
    model.SOCBalance = Constraint(model.h, model.j, rule=soc_balance_rule)
    
    # Ensure that the charging and discharging power do not exceed storage limits
    model.MaxChargePower = Constraint(model.h, model.j, rule=lambda m, h, j: m.PC[h, j] <= m.StorageData['Max_P', j] * m.Ystorage[j, h])
    model.MaxDischargePower = Constraint(model.h, model.j, rule=lambda m, h, j: m.PD[h, j] <= m.StorageData['Max_P', j] * (1 - m.Ystorage[j, h]))
    
    # Constraints on the maximum charging (Pcha) and discharging (Pdis) power for each technology
    model.MaxPcha = Constraint(model.j, rule=lambda m, j: m.Pcha[j] <= m.StorageData['Max_P', j])
    model.MaxPdis = Constraint(model.j, rule=lambda m, j: m.Pdis[j] <= m.StorageData['Max_P', j])

    model.PchaPdis = Constraint(model.b, rule=lambda m, j: m.Pcha[j] == m.Pdis[j])

    # Hourly capacity bounds
    def max_hourly_charging_rule(m, h, j):
        return m.PC[h, j] <= m.Pcha[j]
    model.MaxHourlyCharging = Constraint(model.h, model.j, rule=max_hourly_charging_rule)
    
    def max_hourly_discharging_rule(m, h, j):
        return m.PD[h, j] <= m.Pdis[j]
    model.MaxHourlyDischarging = Constraint(model.h, model.j, rule=max_hourly_discharging_rule)
 
    # Max and min energy capacity constraints (handle uninitialized variables)
    def min_ecap_rule(model, j):
        if model.StorageData['Eff', j] <= 0:
            return Constraint.Skip 
        else:
            return model.Ecap[j] >= model.StorageData['Min_Duration', j] \
                * model.Pdis[j] / sqrt(model.StorageData['Eff', j])
    model.MinEcap = Constraint(model.j, rule=min_ecap_rule)

    def max_ecap_rule(model, j):
        if model.StorageData['Eff', j] <= 0:
            return Constraint.Skip
        else:
            return model.Ecap[j] <= model.StorageData['Max_Duration', j] \
                * model.Pdis[j] / sqrt(model.StorageData['Eff', j])
    model.MaxEcap = Constraint(model.j, rule=max_ecap_rule)
    
    # Max cycle year
    def max_cycle_year_rule(model):
        return sum(model.PD[h, 'Li-Ion'] for h in model.h) <= (model.MaxCycles / model.StorageData['Lifetime', 'Li-Ion']) * model.Ecap['Li-Ion']
    model.MaxCycleYear = Constraint(rule=max_cycle_year_rule)

    
    # Sanity checks of loaded and initialized data ---------------------------------    
    # Open a file to save all sanity checks output
    with open("sanity_checks_output.txt", "w") as f:
    
        # Inspect the first few hours of data
        f.write("Sanity Checks for First Few Hours of Data:\n")
        for h in range(1, 10):
            f.write(f"Hour {h}: Load={model.Load[h]}, Nuclear={model.Nuclear[h]}, LargeHydro={model.LargeHydro[h]}, OtherRenewables={model.OtherRenewables[h]}\n")
        
        # Check for NaN or None values across all hours
        f.write("\nChecking for NaN or None Values Across All Hours:\n")
        def check_missing_data(model, f):
            for h in model.h:
                load_value = model.Load[h]
                nuclear_value = model.Nuclear[h]
                hydro_value = model.LargeHydro[h]
                other_re_value = model.OtherRenewables[h]
        
                if pd.isna(load_value) or pd.isna(nuclear_value) or pd.isna(hydro_value) or pd.isna(other_re_value):
                    f.write(f"Hour {h} has NaN values.\n")
                elif load_value is None or nuclear_value is None or hydro_value is None or other_re_value is None:
                    f.write(f"Hour {h} has None values.\n")
        
        check_missing_data(model, f)
        
        # Extract values for analysis and bounds checking
        load_values = [model.Load[h] for h in model.h]
        nuclear_values = [model.Nuclear[h] for h in model.h]
        hydro_values = [model.LargeHydro[h] for h in model.h]
        other_re_values = [model.OtherRenewables[h] for h in model.h]
        
        f.write("\nSummary of Parameter Ranges:\n")
        f.write(f"Load range: {min(load_values)} to {max(load_values)}\n")
        f.write(f"Nuclear range: {min(nuclear_values)} to {max(nuclear_values)}\n")
        f.write(f"LargeHydro range: {min(hydro_values)} to {max(hydro_values)}\n")
        f.write(f"OtherRenewables range: {min(other_re_values)} to {max(other_re_values)}\n")
        
        # Check if all hours have values for each parameter
        f.write("\nChecking for Missing Hours:\n")
        def check_missing_hours(model, f):
            missing_hours = [h for h in model.h if pd.isna(model.Load[h]) or pd.isna(model.Nuclear[h]) or pd.isna(model.LargeHydro[h]) or pd.isna(model.OtherRenewables[h])]
            
            if missing_hours:
                f.write(f"Missing data for hours: {missing_hours}\n")
            else:
                f.write("All hours have data.\n")
    
        check_missing_hours(model, f)
        
        # Check bounds of some variables
        f.write("\nBounds Check for Variables:\n")
        for pv in model.Ypv:
            lb, ub = model.Ypv[pv].bounds
            f.write(f"Ypv[{pv}]: Bounds = ({lb}, {ub}), Initial Value = {model.Ypv[pv].value}\n")
        
        for wind in model.Ywind:
            lb, ub = model.Ywind[wind].bounds
            f.write(f"Ywind[{wind}]: Bounds = ({lb}, {ub}), Initial Value = {model.Ywind[wind].value}\n")
        
        for j in model.j:
            lb, ub = model.Pcha[j].bounds
            f.write(f"Pcha[{j}]: Bounds = ({lb}, {ub}), Initial Value = {model.Pcha[j].value}\n")
            lb, ub = model.Pdis[j].bounds
            f.write(f"Pdis[{j}]: Bounds = ({lb}, {ub}), Initial Value = {model.Pdis[j].value}\n")
            
        # Check model dimensions
        f.write("\nModel Dimensions:\n")
        f.write(f"Number of hours (h): {len(model.h)}\n")
        f.write(f"Number of solar plants (k): {len(model.k)}\n")
        f.write(f"Number of wind plants (w): {len(model.w)}\n")
        f.write(f"Number of storage technologies (j): {len(model.j)}\n")
        f.write(f"Number of storage properties (sp): {len(model.sp)}\n")
    
        # Count variables by type
        binary_vars = [v for v in model.component_data_objects(Var) if v.is_binary()]
        integer_vars = [v for v in model.component_data_objects(Var) if v.is_integer()]
        continuous_vars = [v for v in model.component_data_objects(Var) if v.is_continuous()]
        
        f.write(f"\nNumber of binary variables: {len(binary_vars)}\n")
        f.write(f"Number of integer variables: {len(integer_vars)}\n")
        f.write(f"Number of continuous variables: {len(continuous_vars)}\n")
        
        # Count constraints
        constraints = list(model.component_data_objects(Constraint, active=True))
        f.write(f"\nTotal number of constraints: {len(constraints)}\n")
    
        # Check variables used in each constraint
        f.write("\nVariables Involved in Each Constraint:\n")
        for c in model.component_objects(Constraint, active=True):
            c_data = getattr(model, c.name)
            for index in c_data:
                expr = c_data[index].body
                vars_in_expr = list(identify_variables(expr))
                f.write(f"Constraint {c.name}[{index}] involves {len(vars_in_expr)} variables.\n")
    
        # Recheck variables count
        binary_vars = [v for v in model.component_data_objects(Var) if v.is_binary()]
        f.write(f"\nUpdated number of binary variables: {len(binary_vars)}\n")
    
        # Summary of loaded data
        f.write("\nSummary of Loaded Data:\n")
        def summarize_data(data, name, f):
            if isinstance(data, pd.DataFrame):
                f.write(f"\nSummary of {name}:\n")
                f.write(data.head().to_string() + "\n")
                f.write(data.describe().to_string() + "\n")
            elif isinstance(data, list):
                f.write(f"\nSummary of {name} (List):\n")
                f.write(f"First 5 elements: {data[:5]}\n")
                f.write(f"Total number of elements: {len(data)}\n")
        
        summarize_data(data['solar_plants'], 'Solar Data', f)
        summarize_data(data['wind_plants'], 'Wind Data', f)
        summarize_data(data['load_data'], 'Load Data', f)
        summarize_data(data['nuclear_data'], 'Nuclear Data', f)
        summarize_data(data['large_hydro_data'], 'Large Hydro Data', f)
        summarize_data(data['other_renewables_data'], 'Other Renewables Data', f)
        summarize_data(data['cf_solar'], 'Solar Capacity Factors', f)
        summarize_data(data['cf_wind'], 'Wind Capacity Factors', f)
        summarize_data(data['cap_solar'], 'Solar Capacity', f)
        summarize_data(data['cap_wind'], 'Wind Capacity', f)
        summarize_data(data['storage_data'], 'Storage Capacity', f)
    
        # Check initialized parameters
        f.write("\nSummary of Initialized Parameters:\n")
        for param in [model.Load, model.Nuclear, model.LargeHydro, model.OtherRenewables]:
            values = [param[h] for h in model.h]
            f.write(f"Parameter {param.name}: Min={min(values)}, Max={max(values)}\n")
        
        # Model statistics
        f.write("\nPyomo Model Size Report:\n")
        report = build_model_size_report(model)
        f.write(str(report) + "\n")

    #------------------------------------------------------------------------------    
    
    return model

# ---------------------------------------------------------------------------------
# Results collection function
def collect_results(model):
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

    return results

# Run solver function
def run_solver(model, log_file_path='solver_log.txt', mipgap=0, num_runs=1):
    #solver = SolverFactory('cbc', executable='C:/NREL_Projects/LDES/SDOM/Open-source/CBC/cbc.exe')
    solver = SolverFactory('cbc')
    solver.options['loglevel'] = 3
    solver.options['ratioGap'] = mipgap
    logging.basicConfig(level=logging.INFO)

    # Export the model to an LP file for comparing with the gdx file
    # model.write('model.lp', io_options={'symbolic_solver_labels': True})
    
    results_over_runs = []  
    best_result = None       
    best_objective_value = float('inf')  

    for run in range(num_runs):
        target_value = 0.5 + 0.05 * run
        model.GenMix_Target.set_value(target_value)  

        print(f"Running optimization for GenMix_Target = {target_value:.2f}")
        result = solver.solve(model, tee=True, keepfiles=True, logfile=log_file_path, options_string="threads=4")

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

    #iso = ['CAISO', 'ERCOT', 'ISONE', 'MISO', 'NYISO', 'PJM', 'SPP']
    iso = ['CAISO']
    nuclear = ['1']
    target = ['1.00']
    
    #nuclear = ['0', '1']
    #target = ['0.00', '0.75', '0.80', '0.85', '0.90', '0.95', '1.00'] 

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

