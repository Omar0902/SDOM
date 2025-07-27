from pyomo.core import Var, Constraint
from pyomo.environ import *

####################################################################################|
# ------------------------------------ Variables -----------------------------------|
####################################################################################|

def add_gascc_variables(model):
    model.CapCC = Var(domain=NonNegativeReals, initialize=0)
    model.GenCC = Var(model.h, domain=NonNegativeReals,initialize=0)  # Generation from GCC units

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

####################################################################################|
# -----------------------------------= Add_costs -----------------------------------|
####################################################################################|
def add_gasscc_fixed_costs(model):
    """
    Add cost-related variables for gas combined cycle (GCC) to the model.
    
    Parameters:
    model: The optimization model to which GCC cost variables will be added.
    
    Returns:
    Costs sum for gas combined cycle, including capital and fixed O&M costs.
    """
    return (
        # Gas CC Capex and Fixed O&M
        model.FCR_GasCC*1000*model.CapexGasCC*model.CapCC
        + 1000*model.FOM_GasCC*model.CapCC
    )

def add_gasscc_variable_costs(model):
    """
    Add variable costs for gas combined cycle (GCC) to the model.

    Parameters:
    model: The optimization model to which GCC variable costs will be added.

    Returns:
    Variable costs sum for gas combined cycle, including fuel costs.
    """
    return (
        (model.GasPrice * model.HR + model.VOM_GasCC) *
            sum(model.GenCC[h] for h in model.h)
    )

####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|