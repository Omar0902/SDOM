from pyomo.core import Var, Constraint, Expression
from pyomo.environ import Param, NonNegativeReals
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

    # Capacity selection variables with continuous bounds between 0 and 1
    model.Ypv = Var(model.k, domain=NonNegativeReals, bounds=(0, 1), initialize=1)
    model.Ywind = Var(model.w, domain=NonNegativeReals, bounds=(0, 1), initialize=1)

####################################################################################|
# ----------------------------------- Expressions ----------------------------------|
####################################################################################|

def solar_fixed_om_cost_expr_rule(model):
    """
    Expression to calculate the fixed O&M costs for solar PV technologies.
    """
    return sum( ( MW_TO_KW * model.CapSolar_FOM_M[k]) * model.CapSolar_capacity[k] * model.Ypv[k] for k in model.k )

def wind_fixed_om_cost_expr_rule(model):
    """
    Expression to calculate the fixed O&M costs for wind technologies.
    """
    return sum( ( MW_TO_KW * model.CapWind_FOM_M[w]) * model.CapWind_capacity[w] * model.Ywind[w] for w in model.w )

def solar_capex_cost_expr_rule(model):
    """
    Expression to calculate the capital expenditures (Capex) for solar PV technologies.
    """
    return sum( (model.FCR_VRE * (MW_TO_KW * model.CapSolar_CAPEX_M[k] + model.CapSolar_trans_cap_cost[k]))\
                                         * model.CapSolar_capacity[k] * model.Ypv[k] for k in model.k )

def wind_capex_cost_expr_rule(model):
    """
    Expression to calculate the capital expenditures (Capex) for wind technologies.
    """
    return sum( (model.FCR_VRE * (MW_TO_KW * model.CapWind_CAPEX_M[w] + model.CapWind_trans_cap_cost[w])) \
                                       * model.CapWind_capacity[w] * model.Ywind[w] for w in model.w )


def add_vre_expressions(model):
    model.pv_fixed_om_cost_expr = Expression(rule=solar_fixed_om_cost_expr_rule)
    model.wind_fixed_om_cost_expr = Expression(rule=wind_fixed_om_cost_expr_rule)
    model.pv_capex_cost_expr = Expression(rule=solar_capex_cost_expr_rule)
    model.wind_capex_cost_expr = Expression(rule=wind_capex_cost_expr_rule)
    
    model.total_hourly_pv_availability = Expression(model.h, rule=lambda model, h: model.GenPV[h] + model.CurtPV[h])
    model.total_hourly_wind_availability = Expression(model.h, rule=lambda model, h: model.GenWind[h] + model.CurtWind[h])

    model.total_hourly_pv_plant_availability = Expression(model.h, model.k, rule=lambda model, h, k: model.CFSolar[h, k] * model.CapSolar_capacity[k] * model.Ypv[k])
    model.total_hourly_wind_plant_availability = Expression(model.h, model.w, rule=lambda model, h, w: model.CFWind[h, w] * model.CapWind_capacity[w] * model.Ywind[w])

####################################################################################|
# ------------------------------------ Add_costs -----------------------------------|
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
        model.pv_fixed_om_cost_expr + model.pv_capex_cost_expr +
        # Wind Capex and Fixed O&M
        model.wind_fixed_om_cost_expr + model.wind_capex_cost_expr
         )

####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|
# - Solar balance : generation + curtailed generation = capacity factor * capacity
def solar_balance_rule(model, h):
    return model.total_hourly_pv_availability[h] == sum(model.total_hourly_pv_plant_availability[h, k] for k in model.k)

# - Wind balance : generation + curtailed generation = capacity factor * capacity 
def wind_balance_rule(model, h):
    return model.total_hourly_wind_availability[h] == sum(model.total_hourly_wind_plant_availability[h, w] for w in model.w)

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