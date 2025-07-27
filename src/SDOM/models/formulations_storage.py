from pyomo.core import Var, Constraint
from pyomo.environ import *

####################################################################################|
# ------------------------------------ Variables -----------------------------------|
####################################################################################|
def add_storage_variables(model):
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

    model.Ystorage = Var(model.j, model.h, domain=Binary, initialize=0)


####################################################################################|
# -----------------------------------= Add_costs -----------------------------------|
####################################################################################|
def add_storage_fixed_costs(model):
    """
    Add cost-related variables for storage technologies to the model.
    
    Parameters:
    model: The optimization model to which storage cost variables will be added.
    
    Returns:
    Costs sum for storage technologies, including capital and fixed O&M costs.
    """
    return ( # Storage Capex and Fixed O&M
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
            ) )

def add_storage_variable_costs(model):
    """
    Add variable costs for storage technologies to the model.
    
    Parameters:
    model: The optimization model to which storage variable costs will be added.
    
    Returns:
    Variable costs sum for storage technologies, including variable O&M costs.
    """
    return (
        sum( model.StorageData['VOM', j] * sum(model.PD[h, j]
                  for h in model.h) for j in model.j )
    )

####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|