
from pyomo.environ import *

import logging
import math
#import matplotlib.pyplot as plt
from pyomo.opt import SolverFactory, SolverStatus, TerminationCondition
from pyomo.environ import value
from pyomo.environ import Binary
from pyomo.util.infeasible import log_infeasible_constraints
from pyomo.core import Var, Constraint
from pyomo.core.expr.visitor import identify_variables
from pyomo.util.model_size import build_model_size_report
#from pympler import muppy, summary
import sys
from pyomo.contrib import appsi
from pyomo.contrib.appsi.solvers import Highs
#from gethighs import HiGHS
#import highspy
#solver = highspy.Highs()

# ---------------------------------------------------------------------------------
# Data loading


def load_data():
    os.chdir('./Data')
    solar_plants = pd.read_csv('Set_k_SolarPV.csv', header=None)[0].tolist()
    wind_plants = pd.read_csv('Set_w_Wind.csv', header=None)[0].tolist()

    load_data = pd.read_csv('Load_hourly_2050.csv').round(5)
    nuclear_data = pd.read_csv('Nucl_hourly_2019.csv').round(5)
    large_hydro_data = pd.read_csv('lahy_hourly_2019.csv').round(5)
    other_renewables_data = pd.read_csv('otre_hourly_2019.csv').round(5)
    cf_solar = pd.read_csv('CFSolar_2050.csv').round(5)
    cf_solar.columns = cf_solar.columns.astype(str)
    cf_wind = pd.read_csv('CFWind_2050.csv').round(5)
    cf_wind.columns = cf_wind.columns.astype(str)
    cap_solar = pd.read_csv('CapSolar_2050.csv').round(5)
    cap_solar['sc_gid'] = cap_solar['sc_gid'].astype(str)
    cap_wind = pd.read_csv('CapWind_2050.csv').round(5)
    cap_wind['sc_gid'] = cap_wind['sc_gid'].astype(str)
    storage_data = pd.read_csv('StorageData_2050.csv', index_col=0).round(5)
    os.chdir('..')
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





def initialize_model(data, with_resilience_constraints=False):
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

    # Initialize solar and wind parameters, with default values for missing data
    for property_name in ['trans_cap_cost', 'CAPEX_M', 'FOM_M']:
        property_dict_solar = complete_solar_data.set_index('sc_gid')[property_name].to_dict()
        property_dict_wind = complete_wind_data.set_index('sc_gid')[property_name].to_dict()
        default_value = 0.0
        filtered_property_dict_solar = {k: property_dict_solar.get(k, default_value) for k in model.k}
        filtered_property_dict_wind = {w: property_dict_wind.get(w, default_value) for w in model.w}
        model.add_component(f"CapSolar_{property_name}", Param(model.k, initialize=filtered_property_dict_solar))
        model.add_component(f"CapWind_{property_name}", Param(model.w, initialize=filtered_property_dict_wind))

    # Define sets
    model.h = RangeSet(1, 24)
    model.j = Set(initialize=['Li-Ion', 'CAES', 'PHS', 'H2'])
    model.b = Set(initialize=['Li-Ion', 'PHS'])

    # Initialize storage properties
    storage_properties = ['P_Capex', 'E_Capex', 'Eff', 'Min_Duration',
                          'Max_Duration', 'Max_P', 'FOM', 'VOM', 'Lifetime', 'CostRatio']
    model.sp = Set(initialize=storage_properties)

    # Scalar parameters
    model.r = Param( initialize = float(data["scalars"].loc["r"].Value) )  # Discount rate
    model.GasPrice = Param( initialize = float(data["scalars"].loc["GasPrice"].Value))  # Gas prices (US$/MMBtu)
    # Heat rate for gas combined cycle (MMBtu/MWh)
    model.HR = Param( initialize = float(data["scalars"].loc["HR"].Value) )
    # Capex for gas combined cycle units (US$/kW)
    model.CapexGasCC = Param( initialize =float(data["scalars"].loc["CapexGasCC"].Value) )
    # Fixed O&M for gas combined cycle (US$/kW-year)
    model.FOM_GasCC = Param( initialize = float(data["scalars"].loc["FOM_GasCC"].Value) )
    # Variable O&M for gas combined cycle (US$/MWh)
    model.VOM_GasCC = Param( initialize = float(data["scalars"].loc["VOM_GasCC"].Value) )
    model.EUE_max = Param( initialize = float(data["scalars"].loc["EUE_max"].Value), mutable=True )  # Maximum EUE (in MWh) - Maximum unserved Energy

    # GenMix_Target, mutable to change across multiple runs
    model.GenMix_Target = Param( initialize = float(data["scalars"].loc["GenMix_Target"].Value), mutable=True)

    # Fixed Charge Rates (FCR) for VRE and Gas CC
    def fcr_rule(model, lifetime=30):
        return (model.r * (1 + model.r) ** lifetime) / ((1 + model.r) ** lifetime - 1)

    model.FCR_VRE = Param( initialize = fcr_rule( model, float(data["scalars"].loc["LifeTimeVRE"].Value) ) )
    model.FCR_GasCC = Param( initialize = fcr_rule( model, float(data["scalars"].loc["LifeTimeGasCC"].Value) ) )

    # Activation factors for nuclear, hydro, and other renewables
    model.AlphaNuclear = Param( initialize = float(data["scalars"].loc["AlphaNuclear"].Value), mutable=True )
    # Control for large hydro generation
    model.AlphaLargHy = Param( initialize = float(data["scalars"].loc["AlphaLargHy"].Value) )
    # Control for other renewable generation
    model.AlphaOtheRe = Param( initialize = float(data["scalars"].loc["AlphaOtheRe"].Value) )

    # Battery life and cycling
    model.MaxCycles = Param( initialize = float(data["scalars"].loc["MaxCycles"].Value) )

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
    cf_solar_filtered = cf_solar_melted[(cf_solar_melted['plant'].isin(model.k)) & (cf_solar_melted['Hour'].isin(model.h))]
    cf_solar_dict = cf_solar_filtered.set_index(['Hour', 'plant'])['CF'].to_dict()
    model.CFSolar = Param(model.h, model.k, initialize=cf_solar_dict)

    # Wind capacity factor initialization
    cf_wind_melted = data["cf_wind"].melt(id_vars='Hour', var_name='plant', value_name='CF')
    cf_wind_filtered = cf_wind_melted[(cf_wind_melted['plant'].isin(model.w)) & (cf_wind_melted['Hour'].isin(model.h))]
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
    #model.CRF.display()

    # Define variables
    model.GenPV = Var(model.h, domain=NonNegativeReals,initialize=0)  # Generated solar PV power
    # Curtailment for solar PV power
    model.CurtPV = Var(model.h, domain=NonNegativeReals, initialize=0)
    model.GenWind = Var(model.h, domain=NonNegativeReals,initialize=0)  # Generated wind power
    model.CurtWind = Var(model.h, domain=NonNegativeReals,initialize=0)  # Curtailment for wind power
    # Capacity of backup GCC units
    model.CapCC = Var(domain=NonNegativeReals, initialize=0)
    model.GenCC = Var(model.h, domain=NonNegativeReals,initialize=0)  # Generation from GCC units

    # Resilience variables
    # How much load is unmet during hour h
    model.LoadShed = Var(model.h, domain=NonNegativeReals, initialize=0)

    # Storage-related variables
    # Charging power for storage technology j in hour h
    model.PC = Var(model.h, model.j, domain=NonNegativeReals, initialize=0)
    # Discharging power for storage technology j in hour h
    model.PD = Var(model.h, model.j, domain=NonNegativeReals, initialize=0)
    # State-of-charge for storage technology j in hour h
    model.SOC = Var(model.h, model.j, domain=NonNegativeReals, initialize=0)
    # Charging capacity for storage technology j
    model.Pcha = Var(model.j, domain=NonNegativeReals, initialize=0)
    # Discharging capacity for storage technology j
    model.Pdis = Var(model.j, domain=NonNegativeReals, initialize=0)
    # Energy capacity for storage technology j
    model.Ecap = Var(model.j, domain=NonNegativeReals, initialize=0)

    # Capacity selection variables with continuous bounds between 0 and 1
    model.Ypv = Var(model.k, domain=NonNegativeReals, bounds=(0, 1), initialize=1)
    model.Ywind = Var(model.w, domain=NonNegativeReals, bounds=(0, 1), initialize=1)

    model.Ystorage = Var(model.j, model.h, domain=Binary, initialize=0)  # Storage selection (binary)

    # Compute and set the upper bound for CapCC
    CapCC_upper_bound_value = max(
        value(model.Load[h]) - value(model.AlphaNuclear) *
        value(model.Nuclear[h])
        - value(model.AlphaLargHy) * value(model.LargeHydro[h])
        - value(model.AlphaOtheRe) * value(model.OtherRenewables[h])
        for h in model.h
    )

    model.CapCC.setub(CapCC_upper_bound_value)
   # model.CapCC.setub(0)
    #print(CapCC_upper_bound_value)

    # ----------------------------------- Objective function -----------------------------------
    def objective_rule(model):
        # Annual Fixed Costs
        fixed_costs = (
            # Solar PV Capex and Fixed O&M
            sum(
                (model.FCR_VRE * (1000 * \
                 model.CapSolar_CAPEX_M[k] + model.CapSolar_trans_cap_cost[k]) + 1000*model.CapSolar_FOM_M[k])
                * model.CapSolar_capacity[k] * model.Ypv[k]
                for k in model.k
            )
            +
            # Wind Capex and Fixed O&M
            sum(
                (model.FCR_VRE * (1000 * \
                 model.CapWind_CAPEX_M[w] + model.CapWind_trans_cap_cost[w]) + 1000*model.CapWind_FOM_M[w])
                * model.CapWind_capacity[w] * model.Ywind[w]
                for w in model.w
            )
            +
            # Storage Capex and Fixed O&M
            sum(
                model.CRF[j]*(
                    1000*model.StorageData['CostRatio', j] * \
                    model.StorageData['P_Capex', j]*model.Pcha[j]
                    + 1000*(1 - model.StorageData['CostRatio', j]) * \
                    model.StorageData['P_Capex', j]*model.Pdis[j]
                    + 1000*model.StorageData['E_Capex', j]*model.Ecap[j]
                )
                + 1000*model.StorageData['CostRatio', j] * \
                model.StorageData['FOM', j]*model.Pcha[j]
                + 1000*(1 - model.StorageData['CostRatio', j]) * \
                model.StorageData['FOM', j]*model.Pdis[j]
                for j in model.j
            )
            +
            # Gas CC Capex and Fixed O&M
            model.FCR_GasCC*1000*model.CapexGasCC*model.CapCC
            + 1000*model.FOM_GasCC*model.CapCC
        )

        # Variable Costs (Gas CC Fuel & VOM, Storage VOM)
        variable_costs = (
            (model.GasPrice * model.HR + model.VOM_GasCC) *
            sum(model.GenCC[h] for h in model.h)
            + sum(model.StorageData['VOM', j] * sum(model.PD[h, j]
                  for h in model.h) for j in model.j)
        )

        return fixed_costs + variable_costs

    model.Obj = Objective(rule=objective_rule, sense=minimize)

    # ----------------------------------- Constraints -----------------------------------
    # Energy supply demand
    def supply_balance_rule(model, h):
        return (
            model.Load[h] + sum(model.PC[h, j] for j in model.j) - sum(model.PD[h, j] for j in model.j)
            - model.AlphaNuclear * model.Nuclear[h] - model.AlphaLargHy * model.LargeHydro[h] - model.AlphaOtheRe * model.OtherRenewables[h]
            - model.GenPV[h] - model.GenWind[h]
            - model.GenCC[h] == 0
        ) 
    model.SupplyBalance = Constraint(model.h, rule=supply_balance_rule)


    # PCLS - Percentage of Critical Load Served - Constraint : Resilience
    critical_load_percentage = 1  # 10% of the total load
    PCLS_target = 0.9  # 90% of the total load

    def pcls_constraint_rule(model):
        return sum(model.Load[h] - model.LoadShed[h] for h in model.h) \
            >= PCLS_target * sum(model.Load[h] for h in model.h) * critical_load_percentage
    if with_resilience_constraints:
        model.PCLS_Constraint = Constraint(rule=pcls_constraint_rule)

    # EUE - Expected Unserved Energy - Constraint : Resilience
    def max_eue_constraint_rule(model):
        return sum(model.LoadShed[h] for h in model.h) <= model.EUE_max
    if with_resilience_constraints:
        model.MaxEUE_Constraint = Constraint(rule=max_eue_constraint_rule)

    # Generation mix target
    # Limit on generation from NG
    def genmix_share_rule(model):
        return sum(model.GenCC[h] for h in model.h) <= (1 - model.GenMix_Target)*sum(model.Load[h] + sum(model.PC[h, j] for j in model.j)
                           - sum(model.PD[h, j] for j in model.j) for h in model.h)
    model.GenMix_Share = Constraint(rule=genmix_share_rule)

    # - Solar balance : generation + curtailed generation = capacity factor * capacity
    def solar_balance_rule(model, h):
        return model.GenPV[h] + model.CurtPV[h] == sum(model.CFSolar[h, k] * model.CapSolar_capacity[k] * model.Ypv[k] for k in model.k)
    model.SolarBal = Constraint(model.h, rule=solar_balance_rule)

    # - Wind balance : generation + curtailed generation = capacity factor * capacity 
    def wind_balance_rule(model, h):
        return model.GenWind[h] + model.CurtWind[h] == sum(model.CFWind[h, w] * model.CapWind_capacity[w] * model.Ywind[w] for w in model.w)
    model.WindBal = Constraint(model.h, rule=wind_balance_rule)

    # Ensure that the charging and discharging power do not exceed storage limits
    model.ChargSt= Constraint(model.h, model.j, rule=lambda m, h, j: m.PC[h, j] <= m.StorageData['Max_P', j] * m.Ystorage[j, h])
    model.DischargeSt = Constraint(model.h, model.j, rule=lambda m, h, j: m.PD[h, j] <= m.StorageData['Max_P', j] * (1 - m.Ystorage[j, h]))

    # Hourly capacity bounds
    model.MaxHourlyCharging = Constraint(model.h, model.j, rule= lambda m,h,j: m.PC[h, j] <= m.Pcha[j])
    model.MaxHourlyDischarging = Constraint(model.h, model.j, rule= lambda m,h,j: m.PD[h, j] <= m.Pdis[j])

    # Limit state of charge of storage by its capacity
    model.MaxSOC = Constraint(model.h, model.j, rule=lambda m, h, j: m.SOC[h,j]<= m.Ecap[j])

    # State-Of-Charge Balance -
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


    # - Constraints on the maximum charging (Pcha) and discharging (Pdis) power for each technology
    model.MaxPcha = Constraint( model.j, rule=lambda m, j: m.Pcha[j] <= m.StorageData['Max_P', j])
    model.MaxPdis = Constraint(model.j, rule=lambda m, j: m.Pdis[j] <= m.StorageData['Max_P', j])

    # Charge and discharge rates are equal -
    model.PchaPdis = Constraint(model.b, rule=lambda m, j: m.Pcha[j] == m.Pdis[j])

    # Max and min energy capacity constraints (handle uninitialized variables)
    model.MinEcap = Constraint(model.j, rule= lambda m,j: m.Ecap[j] >= m.StorageData['Min_Duration', j] * m.Pdis[j] / sqrt(m.StorageData['Eff', j]))
    model.MaxEcap = Constraint(model.j, rule= lambda m,j: m.Ecap[j] <= m.StorageData['Max_Duration', j] * m.Pdis[j] / sqrt(m.StorageData['Eff', j]))

    # Capacity of the backup generation
    model.BackupGen = Constraint(model.h, rule= lambda m,h: m.CapCC >= m.GenCC[h])

    # Max cycle year
    def max_cycle_year_rule(model):
        return sum(model.PD[h, 'Li-Ion'] for h in model.h) <= (model.MaxCycles / model.StorageData['Lifetime', 'Li-Ion']) * model.Ecap['Li-Ion']
    model.MaxCycleYear = Constraint(rule=max_cycle_year_rule)

    # Build a model size report
    #all_objects = muppy.get_objects()
    #print(summary.summarize(all_objects))

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

    results['CAESFOM'] = 1000*model.StorageData['CostRatio', 'PHS'] * model.StorageData['FOM', 'PHS']*model.Pcha['PHS']\
                        + 1000*(1 - model.StorageData['CostRatio', 'PHS']) * model.StorageData['FOM', 'PHS']*model.Pdis['PHS']
    results['CAESVOM'] = model.StorageData['VOM', 'PHS'] * sum(model.PD[h, 'PHS'] for h in model.h) 
    
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


def run_solver(model, log_file_path='./solver_log.txt', optcr=0.0, num_runs=1):
    #solver = SolverFactory('HiGHS')
    #solver = HiGHS(mip_heuristic_effort=0.2, mip_detect_symmetry="on")
    solver = SolverFactory('cbc')#, executable = 'C:/Users/mkoleva/Documents/Masha/Projects/LDES_Demonstration/CBP/TEA/SDOM_pyomo_cbc_122324/Cbc-releases.2.10.12-w64/bin/cbc.exe')
    #solver = SolverFactory('appsi_highs')
    #solver = SolverFactory('scip')
    solver.options['loglevel'] = 3
    solver.options['mip_rel_gap'] = optcr
    solver.options['tee'] = True
    solver.options['keepfiles'] = True
    solver.options['logfile'] = log_file_path
    logging.basicConfig(level=logging.INFO)

    results_over_runs = []
    best_result = None
    best_objective_value = float('inf')

    for run in range(num_runs):
        target_value = 0.95 + 0.05 * (run + 1)
        model.GenMix_Target.set_value(target_value)

        print(f"Running optimization for GenMix_Target = {target_value:.2f}")
        result = solver.solve(model, 
                              #, tee=True, keepfiles = True, #working_dir='C:/Users/mkoleva/Documents/Masha/Projects/LDES_Demonstration/CBP/TEA/Results/solver_log.txt'
                             )
        
        if (result.solver.status == SolverStatus.ok) and (result.solver.termination_condition == TerminationCondition.optimal):
            # If the solution is optimal, collect the results
            print("Optimal solution found")
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

    return results_over_runs, best_result, result

# ---------------------------------------------------------------------------------
# Export results to CSV files


def export_results(model, iso_name, case):
    output_dir = f'./results'
    os.makedirs(output_dir, exist_ok=True)

    # Initialize results dictionaries
    gen_results = {'Scenario':[],'Hour': [], 'Solar PV Generation (MW)': [], 'Solar PV Curtailment (MW)': [],
                   'Wind Generation (MW)': [], 'Wind Curtailment (MW)': [],
                   'Gas CC Generation (MW)': [], 'Power from Storage and Gas CC to Storage (MW)': []}

    storage_results = {'Hour': [], 'Technology': [], 'Charging power (MW)': [],
                       'Discharging power (MW)': [], 'State of charge (MWh)': []}

    summary_results = {}

    # Extract generation results
#    for run in range(num_runs):
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

            power_to_storage = sum(safe_pyomo_value(model.PC[h, j]) or 0 for j in model.j) - sum(
                safe_pyomo_value(model.PD[h, j]) or 0 for j in model.j)
            gen_results['Power from Storage and Gas CC to Storage (MW)'].append(
                power_to_storage)

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
                storage_results['Discharging power (MW)'].append(
                    discharge_power)
                storage_results['State of charge (MWh)'].append(soc)

    # Summary results (total capacities and costs)
    total_cost = safe_pyomo_value(model.Obj())
    total_gas_cc_capacity = safe_pyomo_value(model.CapCC)
    total_solar_capacity = sum(safe_pyomo_value(
        model.Ypv[k]) * model.CapSolar_CAPEX_M[k] for k in model.k)
    total_wind_capacity = sum(safe_pyomo_value(
        model.Ywind[w]) * model.CapWind_CAPEX_M[w] for w in model.w)
    total_solar_generation = sum(safe_pyomo_value(
        model.GenPV[h]) or 0 for h in model.h)
    total_wind_generation = sum(safe_pyomo_value(
        model.GenWind[h]) or 0 for h in model.h)
    solar_capex =  sum(safe_pyomo_value(
         (model.FCR_VRE * (1000 * \
          model.CapSolar_CAPEX_M[k] + model.CapSolar_trans_cap_cost[k])) * model.CapSolar_capacity[k] * model.Ypv[k])
         for k in model.k
         )
    wind_capex =  sum(safe_pyomo_value(
         (model.FCR_VRE * (1000 * \
         model.CapWind_CAPEX_M[w] + model.CapWind_trans_cap_cost[w])) * model.CapWind_capacity[w] * model.Ywind[w])
         for w in model.w
         )        
    solar_FOM = sum(safe_pyomo_value(
         (model.FCR_VRE * 1000*model.CapSolar_FOM_M[k]) * model.CapSolar_capacity[k] * model.Ypv[k])
         for k in model.k
         )
    wind_FOM =  sum(safe_pyomo_value(
         (model.FCR_VRE * 1000*model.CapWind_FOM_M[w]) * model.CapWind_capacity[w] * model.Ywind[w])
         for w in model.w
         )
    LiIon_power_capex = safe_pyomo_value(model.CRF['Li-Ion']*(
                        1000*model.StorageData['CostRatio', 'Li-Ion'] * \
                        model.StorageData['P_Capex', 'Li-Ion']*model.Pcha['Li-Ion']
                        + 1000*(1 - model.StorageData['CostRatio', 'Li-Ion']) * \
                        model.StorageData['P_Capex', 'Li-Ion']*model.Pdis['Li-Ion'])
                        )

    LiIon_energy_capex = safe_pyomo_value(model.CRF['Li-Ion']*1000*model.StorageData['E_Capex', 'Li-Ion']*model.Ecap['Li-Ion']
                                          )
    LiIon_FOM =safe_pyomo_value(1000*model.StorageData['CostRatio', 'Li-Ion'] * model.StorageData['FOM', 'Li-Ion']*model.Pcha['Li-Ion']
    + 1000*(1 - model.StorageData['CostRatio', 'Li-Ion']) * model.StorageData['FOM', 'Li-Ion']*model.Pdis['Li-Ion']
    )
    LiIon_VOM = safe_pyomo_value(model.StorageData['VOM', 'Li-Ion'] * sum(model.PD[h, 'Li-Ion'] for h in model.h) 
                                 )
    caes_power_capex = safe_pyomo_value(model.CRF['CAES']*(
                        1000*model.StorageData['CostRatio', 'CAES'] * \
                        model.StorageData['P_Capex', 'CAES']*model.Pcha['CAES']
                        + 1000*(1 - model.StorageData['CostRatio', 'CAES']) * \
                        model.StorageData['P_Capex', 'CAES']*model.Pdis['CAES'])
                        )
    caes_energy_capex = safe_pyomo_value(model.CRF['CAES']*1000*model.StorageData['E_Capex', 'CAES']*model.Ecap['CAES']
                                         )
    caes_FOM = safe_pyomo_value(1000*model.StorageData['CostRatio', 'CAES'] * model.StorageData['FOM', 'CAES']*model.Pcha['CAES']
    + 1000*(1 - model.StorageData['CostRatio', 'CAES']) * model.StorageData['FOM', 'CAES']*model.Pdis['CAES']
    )
    caes_VOM = safe_pyomo_value(model.StorageData['VOM', 'CAES'] * sum(model.PD[h, 'CAES'] for h in model.h) 
                                )
    phs_power_capex = safe_pyomo_value(model.CRF['PHS']*(
                        1000*model.StorageData['CostRatio', 'PHS'] * \
                        model.StorageData['P_Capex', 'PHS']*model.Pcha['PHS']
                        + 1000*(1 - model.StorageData['CostRatio', 'PHS']) * \
                        model.StorageData['P_Capex', 'PHS']*model.Pdis['PHS'])
                        )
    phs_energy_capex = safe_pyomo_value(model.CRF['PHS']*1000*model.StorageData['E_Capex', 'PHS']*model.Ecap['PHS']
                                        )
    phs_FOM = safe_pyomo_value(1000*model.StorageData['CostRatio', 'PHS'] * model.StorageData['FOM', 'PHS']*model.Pcha['PHS']
    + 1000*(1 - model.StorageData['CostRatio', 'PHS']) * model.StorageData['FOM', 'PHS']*model.Pdis['PHS']
    )
    phs_VOM = safe_pyomo_value(model.StorageData['VOM', 'PHS'] * sum(model.PD[h, 'PHS'] for h in model.h) 
                               )
    H2_power_capex = safe_pyomo_value(model.CRF['H2']*(
                        1000*model.StorageData['CostRatio', 'H2'] * \
                        model.StorageData['P_Capex', 'H2']*model.Pcha['H2']
                        + 1000*(1 - model.StorageData['CostRatio', 'H2']) * \
                        model.StorageData['P_Capex', 'H2']*model.Pdis['H2'])
                        )
    H2_energy_capex = safe_pyomo_value(model.CRF['H2']*1000*model.StorageData['E_Capex', 'H2']*model.Ecap['H2']
                                       )
    H2_FOM = safe_pyomo_value(1000*model.StorageData['CostRatio', 'H2'] * model.StorageData['FOM', 'H2']*model.Pcha['H2']
    + 1000*(1 - model.StorageData['CostRatio', 'H2']) * model.StorageData['FOM', 'H2']*model.Pdis['H2']
    )
    H2_VOM = safe_pyomo_value(model.StorageData['VOM', 'H2'] * sum(model.PD[h, 'H2'] for h in model.h) 
                              )
    gasCC_capex = safe_pyomo_value(model.FCR_GasCC*1000*model.CapexGasCC*model.CapCC
                                   )
    gasCC_fuel = safe_pyomo_value((model.GasPrice * model.HR) * sum(model.GenCC[h] for h in model.h)
                                  )
    gasCC_FOM = safe_pyomo_value(1000*model.FOM_GasCC*model.CapCC
                                 )
    gasCC_VOM = safe_pyomo_value((model.GasPrice * model.HR) * sum(model.GenCC[h] for h in model.h)
                                 )
    if total_cost is not None and total_gas_cc_capacity is not None:
        summary_results['Total cost US$'] = total_cost
        summary_results['Total capacity of gas combined cycle units (MW)'] = total_gas_cc_capacity
        summary_results['Total capacity of solar PV units (MW)'] = total_solar_capacity
        summary_results['Total capacity of wind units (MW)'] = total_wind_capacity
        summary_results['Total generation of solar PV units (MWh)'] = total_solar_generation
        summary_results['Total generation of wind units (MWh)'] = total_wind_generation
        summary_results['Solar Capex US$'] = solar_capex
        summary_results['Solar FOM US$'] = solar_FOM
        summary_results['Wind Capex US$'] = wind_capex
        summary_results['Wind FOM US$'] = wind_FOM
        summary_results['Li-Ion Power Capex US$'] = LiIon_power_capex
        summary_results['Li-Ion Energy Capex US$'] = LiIon_energy_capex
        summary_results['Li-Ion FOM US$'] = LiIon_FOM
        summary_results['Li-Ion VOM US$'] = LiIon_VOM
        summary_results['CAES Power Capex US$'] = caes_power_capex
        summary_results['CAES Energy Capex US$'] = caes_energy_capex
        summary_results['CAES FOM US$'] = caes_FOM
        summary_results['CAES VOM US$'] = caes_VOM
        summary_results['PHS Power Capex US$'] = phs_power_capex
        summary_results['PHS Energy Capex US$'] = phs_energy_capex
        summary_results['PHS FOM US$'] = phs_FOM
        summary_results['PHS VOM US$'] = phs_VOM
        summary_results['H2 Power Capex US$'] = H2_power_capex
        summary_results['H2 Energy Capex US$'] = H2_energy_capex
        summary_results['H2 FOM US$'] = H2_FOM
        summary_results['H2 VOM US$'] = H2_VOM
        summary_results['GasCC Capex US$'] = gasCC_capex
        summary_results['GasCC FUEL US$'] = gasCC_fuel
        summary_results['GasCC FOM US$'] = gasCC_FOM
        summary_results['GasCC VOM US$'] = gasCC_VOM

    # Save generation results to CSV
    if gen_results['Hour']:
        with open(output_dir + f'OutputGeneration_{case}.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=gen_results.keys())
            writer.writeheader()
            writer.writerows([dict(zip(gen_results, t))
                             for t in zip(*gen_results.values())])

    # Save storage results to CSV
    if storage_results['Hour']:
        with open(output_dir + f'OutputStorage_{case}.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=storage_results.keys())
            writer.writeheader()
            writer.writerows([dict(zip(storage_results, t))
                             for t in zip(*storage_results.values())])

    # Save summary results to CSV
    if summary_results:
        with open(output_dir + f'OutputSummary_{case}.csv', mode='w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=summary_results.keys())
            writer.writeheader()
            writer.writerow(summary_results)

# ---------------------------------------------------------------------------------
# Main loop for handling scenarios and results exporting


def main(with_resilience_constraints = False, case='test_data'):
    data = load_data()
    model = initialize_model(data, with_resilience_constraints=with_resilience_constraints)


    # Loop over each scenario combination and solve the model
    if with_resilience_constraints:
        best_result = run_solver(model, with_resilience_constraints=True)
        case += '_resilience'
    else:
        best_result = run_solver(model)
    if best_result:
        export_results(model, case)
    else:
        print(f"Solver did not find an optimal solution for given data and with resilience constraints = {with_resilience_constraints}, skipping result export.")


# ---------------------------------------------------------------------------------
# Execute the main function
if __name__ == "__main__":
    main()
