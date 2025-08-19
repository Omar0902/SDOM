from pyomo.core import Constraint


from .formulations_vre import add_vre_fixed_costs
from .formulations_thermal import add_thermal_fixed_costs, add_thermal_variable_costs
from .formulations_storage import add_storage_fixed_costs, add_storage_variable_costs

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|



####################################################################################|
# ------------------------------- Objective Function -------------------------------|
####################################################################################|

def objective_rule(model):
    """
    Calculates the total objective value for the optimization model.
    This function computes the sum of annual fixed costs and variable costs for the system.
    Fixed costs include VRE (Variable Renewable Energy), storage, and gas combined cycle (Gas CC) fixed costs.
    Variable costs include Gas CC fuel and variable operation & maintenance (VOM) costs, as well as storage VOM costs.
    Args:
        model: The optimization model instance containing relevant parameters and variables.
    Returns:
        The total objective value as the sum of fixed and variable costs.
    """

    # Annual Fixed Costs
    fixed_costs = (
        add_vre_fixed_costs(model)
        +
        add_storage_fixed_costs(model)
        +
        add_thermal_fixed_costs(model)
    )

    # Variable Costs (Gas CC Fuel & VOM, Storage VOM)
    variable_costs = (
        add_thermal_variable_costs(model)
        + 
        add_storage_variable_costs(model)
    )

    return fixed_costs + variable_costs


####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|
# Energy supply demand
def supply_balance_rule(model, h):
    return (
        model.Load[h] + sum(model.PC[h, j] for j in model.j) - sum(model.PD[h, j] for j in model.j)
        - model.AlphaNuclear * model.Nuclear[h] - model.AlphaLargHy * model.LargeHydro[h] - model.AlphaOtheRe * model.OtherRenewables[h]
        - model.GenPV[h] - model.GenWind[h]
        - sum(model.GenCC[h, bu] for bu in model.bu) == 0
    )

# Generation mix target
# Limit on generation from NG
def genmix_share_rule(model):
    return sum(model.GenCC[h, bu] for h in model.h for bu in model.bu) <= (1 - model.GenMix_Target)*sum(model.Load[h] + sum(model.PC[h, j] for j in model.j)
                        - sum(model.PD[h, j] for j in model.j) for h in model.h)

def add_system_constraints(model):
    """
    Adds system constraints to the optimization model.
    
    Parameters:
    model: The optimization model to which system constraints will be added.
    
    Returns:
    None
    """
    # Supply balance constraint
    model.SupplyBalance = Constraint(model.h, rule=supply_balance_rule)

    # Generation mix share constraint
    model.GenMix_Share = Constraint(rule=genmix_share_rule)