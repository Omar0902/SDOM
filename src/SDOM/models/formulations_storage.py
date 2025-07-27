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

# Max cycle year
def max_cycle_year_rule(model):
    return sum(model.PD[h, 'Li-Ion'] for h in model.h) <= (model.MaxCycles / model.StorageData['Lifetime', 'Li-Ion']) * model.Ecap['Li-Ion']

def add_storage_constraints( model ):
    """
    Add storage-related constraints to the model.
    
    Parameters:
    model: The optimization model to which storage constraints will be added.
    
    Returns:
    None
    """
    # Ensure that the charging and discharging power do not exceed storage limits
    model.ChargSt= Constraint(model.h, model.j, rule=lambda m, h, j: m.PC[h, j] <= m.StorageData['Max_P', j] * m.Ystorage[j, h])
    model.DischargeSt = Constraint(model.h, model.j, rule=lambda m, h, j: m.PD[h, j] <= m.StorageData['Max_P', j] * (1 - m.Ystorage[j, h]))

    # Hourly capacity bounds
    model.MaxHourlyCharging = Constraint(model.h, model.j, rule= lambda m,h,j: m.PC[h, j] <= m.Pcha[j])
    model.MaxHourlyDischarging = Constraint(model.h, model.j, rule= lambda m,h,j: m.PD[h, j] <= m.Pdis[j])

    # Limit state of charge of storage by its capacity
    model.MaxSOC = Constraint(model.h, model.j, rule=lambda m, h, j: m.SOC[h,j]<= m.Ecap[j])
    # SOC Balance Constraint
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

    model.MaxCycleYear = Constraint(rule=max_cycle_year_rule)