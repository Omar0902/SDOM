from pyomo.core import Var, Constraint
from pyomo.environ import *
from ..constants import VRE_PROPERTIES_NAMES, MW_TO_KW
from .models_utils import fcr_rule

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_vre_parameters(model, data):
    filtered_cap_solar_dict = data['filtered_cap_solar_dict']
    filtered_cap_wind_dict = data['filtered_cap_wind_dict']
    complete_solar_data = data['complete_solar_data']
    complete_wind_data = data['complete_wind_data']

    # Initialize solar and wind parameters, with default values for missing data
    for property_name in VRE_PROPERTIES_NAMES:#['trans_cap_cost', 'CAPEX_M', 'FOM_M']:
        property_dict_solar = complete_solar_data.set_index('sc_gid')[property_name].to_dict()
        property_dict_wind = complete_wind_data.set_index('sc_gid')[property_name].to_dict()
        default_value = 0.0
        filtered_property_dict_solar = {k: property_dict_solar.get(k, default_value) for k in model.k}
        filtered_property_dict_wind = {w: property_dict_wind.get(w, default_value) for w in model.w}
        model.add_component(f"CapSolar_{property_name}", Param(model.k, initialize=filtered_property_dict_solar))
        model.add_component(f"CapWind_{property_name}", Param(model.w, initialize=filtered_property_dict_wind))

    model.CapSolar_capacity = Param( model.k, initialize = filtered_cap_solar_dict )  
    model.CapWind_capacity = Param( model.w, initialize = filtered_cap_wind_dict )

    model.FCR_VRE = Param( initialize = fcr_rule( model, float(data["scalars"].loc["LifeTimeVRE"].Value) ) )

    # Solar capacity factor initialization
    cf_solar_melted = data["cf_solar"].melt(id_vars='Hour', var_name='plant', value_name='CF')
    cf_solar_filtered = cf_solar_melted[(cf_solar_melted['plant'].isin(model.k)) & (cf_solar_melted['Hour'].isin(model.h))]
    cf_solar_dict = cf_solar_filtered.set_index(['Hour', 'plant'])['CF'].to_dict()
    model.CFSolar = Param( model.h, model.k, initialize = cf_solar_dict )

    # Wind capacity factor initialization
    cf_wind_melted = data["cf_wind"].melt(id_vars='Hour', var_name='plant', value_name='CF')
    cf_wind_filtered = cf_wind_melted[(cf_wind_melted['plant'].isin(model.w)) & (cf_wind_melted['Hour'].isin(model.h))]
    cf_wind_dict = cf_wind_filtered.set_index(['Hour', 'plant'])['CF'].to_dict()
    model.CFWind = Param( model.h, model.w, initialize = cf_wind_dict )


def add_vre_variables(model):
    """
    Add variables related to variable renewable energy (VRE) to the model.
    
    Parameters:
    model: The optimization model to which VRE variables will be added.
    
    Returns:
    None
    """
    model.GenPV = Var(model.h, domain=NonNegativeReals,initialize=0)  # Generated solar PV power
    model.CurtPV = Var(model.h, domain=NonNegativeReals, initialize=0) # Curtailment for solar PV power
    model.GenWind = Var(model.h, domain=NonNegativeReals,initialize=0)  # Generated wind power
    model.CurtWind = Var(model.h, domain=NonNegativeReals,initialize=0)  # Curtailment for wind power


####################################################################################|
# -----------------------------------= Add_costs -----------------------------------|
####################################################################################|

def add_vre_fixed_costs(model):
    """
    Add cost-related variables for variable renewable energy (VRE) to the model.
    
    Parameters:
    model: The optimization model to which VRE cost variables will be added.
    
    Returns:
    Costs sum for solar PV and wind energy, including capital and fixed O&M costs.
    """
    # Solar PV Capex and Fixed O&M
    return ( 
        sum(
        (model.FCR_VRE * (MW_TO_KW * \
            model.CapSolar_CAPEX_M[k] + model.CapSolar_trans_cap_cost[k]) + MW_TO_KW*model.CapSolar_FOM_M[k])
        * model.CapSolar_capacity[k] * model.Ypv[k]
        for k in model.k
        )
        +
        # Wind Capex and Fixed O&M
        sum(
            (model.FCR_VRE * (MW_TO_KW * \
                model.CapWind_CAPEX_M[w] + model.CapWind_trans_cap_cost[w]) + MW_TO_KW*model.CapWind_FOM_M[w])
            * model.CapWind_capacity[w] * model.Ywind[w]
            for w in model.w
        ) )

####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|
# - Solar balance : generation + curtailed generation = capacity factor * capacity
def solar_balance_rule(model, h):
    return model.GenPV[h] + model.CurtPV[h] == sum(model.CFSolar[h, k] * model.CapSolar_capacity[k] * model.Ypv[k] for k in model.k)

# - Wind balance : generation + curtailed generation = capacity factor * capacity 
def wind_balance_rule(model, h):
    return model.GenWind[h] + model.CurtWind[h] == sum(model.CFWind[h, w] * model.CapWind_capacity[w] * model.Ywind[w] for w in model.w)

def add_vre_balance_constraints(model):
    """
    Add constraints related to variable renewable energy (VRE) to the model.
    
    Parameters:
    model: The optimization model to which VRE constraints will be added.
    
    Returns:
    None
    """
    # Solar balance constraint
    model.SolarBal = Constraint(model.h, rule=solar_balance_rule)
    # Wind balance constraint
    model.WindBal = Constraint(model.h, rule=wind_balance_rule)