from pyomo.core import Var
from pyomo.environ import Param, value, NonNegativeReals
from .models_utils import fcr_rule
from ..constants import MW_TO_KW

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|
def add_gascc_parameters(model, data):

    model.GasPrice = Param( initialize = float(data["scalars"].loc["GasPrice"].Value))  # Gas prices (US$/MMBtu)
    # Heat rate for gas combined cycle (MMBtu/MWh)
    model.HR = Param( initialize = float(data["scalars"].loc["HR"].Value) )
    # Capex for gas combined cycle units (US$/kW)
    model.CapexGasCC = Param( initialize =float(data["scalars"].loc["CapexGasCC"].Value) )
    # Fixed O&M for gas combined cycle (US$/kW-year)
    model.FOM_GasCC = Param( initialize = float(data["scalars"].loc["FOM_GasCC"].Value) )
    # Variable O&M for gas combined cycle (US$/MWh)
    model.VOM_GasCC = Param( initialize = float(data["scalars"].loc["VOM_GasCC"].Value) )

    model.FCR_GasCC = Param( initialize = fcr_rule( model, float(data["scalars"].loc["LifeTimeGasCC"].Value) ) )


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
        model.FCR_GasCC*MW_TO_KW*model.CapexGasCC*model.CapCC
        + MW_TO_KW*model.FOM_GasCC*model.CapCC
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