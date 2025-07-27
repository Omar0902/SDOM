from pyomo.core import Var, Constraint
from pyomo.environ import *

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
        ) )

####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|