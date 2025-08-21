from pyomo.environ import Param
from ..constants import MW_TO_KW

# Fixed Charge Rates (FCR) for VRE and Gas CC
def fcr_rule( model, lifetime = 30 ):
    return ( model.r * (1 + model.r) ** lifetime ) / ( (1 + model.r) ** lifetime - 1 )

def fcr_rule_thermal( model, bu ):
    lifetime = model.data['LifeTime', bu]
    return ( model.r * (1 + model.r) ** lifetime ) / ( (1 + model.r) ** lifetime - 1 )

# Capital recovery factor for storage
def crf_rule( model, j ):
    lifetime = model.data['Lifetime', j]
    return ( model.r * (1 + model.r) ** lifetime ) / ( (1 + model.r) ** lifetime - 1 )


####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_alpha_and_ts_parameters( block, 
                                hourly_set, 
                                data, 
                                key_scalars: str, 
                                key_ts: str,
                                key_col: str):
    # Control parameter to activate certain device.
    if key_scalars != "":
        # Initialize alpha parameter from scalars
        block.alpha = Param( initialize = float(data["scalars"].loc[key_scalars].Value) )

    # Time-series parameter data initialization
    selected_data          = data[key_ts].set_index('*Hour')[key_col].to_dict()
    filtered_selected_data = {h: selected_data[h] for h in hourly_set if h in selected_data}

    block.ts_parameter = Param( hourly_set, initialize = filtered_selected_data)


####################################################################################|
# ----------------------------------- Expressions ----------------------------------|
####################################################################################|

def sum_installed_capacity_by_plants_set_expr_rule( block ):
    """
    Expression to calculate the total installed capacity for plants contained in a plants_set of a pyomo block.
    """
    return sum( block.plant_installed_capacity[plant] for plant in block.plants_set )
 

def generic_fixed_om_cost_expr_rule( block ):
    """
    Expression to calculate the fixed O&M costs for generic technologies.
    """
    return sum( ( MW_TO_KW * block.FOM_M[k]) * block.plant_installed_capacity[k] for k in block.plants_set )


def generic_capex_cost_expr_rule( block ):
    """
    Expression to calculate the capital expenditures (Capex) for generic technologies when lifetime and fcr are the same for all the "block.plants_set".
    """
    return sum( ( (MW_TO_KW * block.CAPEX_M[k] + block.trans_cap_cost[k]))\
                                         * block.plant_installed_capacity[k] for k in block.plants_set )


def different_fcr_capex_cost_expr_rule( block ):
    """
    Expression to calculate the capital expenditures (Capex) for generic technologies when lifetime and fcr are specific for each element in "block.plants_set".
    """
    return sum( ( block.FCR[k] * (MW_TO_KW * block.CAPEX_M[k] + block.trans_cap_cost[k]))\
                                         * block.plant_installed_capacity[k] for k in block.plants_set )


####################################################################################|
# -----------------------------------= Add_costs -----------------------------------|
####################################################################################|

def add_generic_fixed_costs(block):
    """
    Add fixed costs (FOM+CAPEX) for generic technologies to the block.
    
    Parameters:
    block: The optimization block to which cost variables will be added.
    The block should have the expressions `capex_cost_expr` and `fixed_om_cost_expr`.

    Returns:
    Costs sum for generic technologies, including capital and fixed O&M costs.
    """
    return block.capex_cost_expr + block.fixed_om_cost_expr