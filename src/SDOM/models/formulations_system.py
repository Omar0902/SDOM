from pyomo.core import Var, Constraint
from pyomo.environ import *

from .formulations_vre import add_vre_fixed_costs
from .formulations_thermal import add_gasscc_fixed_costs, add_gasscc_variable_costs
from .formulations_resiliency import *
from .formulations_storage import add_storage_fixed_costs, add_storage_variable_costs

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
        add_gasscc_fixed_costs(model)
    )

    # Variable Costs (Gas CC Fuel & VOM, Storage VOM)
    variable_costs = (
        add_gasscc_variable_costs(model)
        + 
        add_storage_variable_costs(model)
    )

    return fixed_costs + variable_costs

