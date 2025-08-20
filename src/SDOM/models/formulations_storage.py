from pyomo.core import Var, Constraint
from pyomo.environ import NonNegativeReals, Param, Binary, sqrt
from ..constants import STORAGE_PROPERTIES_NAMES, MW_TO_KW
from .models_utils import crf_rule

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_storage_parameters(model, data):
    # Battery life and cycling
    model.MaxCycles = Param( initialize = float(data["scalars"].loc["MaxCycles"].Value) )
    # Storage data initialization
    storage_dict = data["storage_data"].stack().to_dict()
    storage_tuple_dict = {(prop, tech): storage_dict[(prop, tech)] for prop in STORAGE_PROPERTIES_NAMES for tech in model.storage.j}
    model.StorageData = Param( model.sp, model.storage.j, initialize = storage_tuple_dict )

    model.CRF = Param( model.storage.j, initialize = crf_rule ) #Capital Recovery Factor -STORAGE

####################################################################################|
# ------------------------------------ Variables -----------------------------------|
####################################################################################|
def add_storage_variables(model):
    # Charging power for storage technology j in hour h
    model.PC = Var(model.h, model.storage.j, domain=NonNegativeReals, initialize=0)
    # Discharging power for storage technology j in hour h
    model.PD = Var(model.h, model.storage.j, domain=NonNegativeReals, initialize=0)
    # State-of-charge for storage technology j in hour h
    model.SOC = Var(model.h, model.storage.j, domain=NonNegativeReals, initialize=0)
    # Charging capacity for storage technology j
    model.Pcha = Var(model.storage.j, domain=NonNegativeReals, initialize=0)
    # Discharging capacity for storage technology j
    model.Pdis = Var(model.storage.j, domain=NonNegativeReals, initialize=0)
    # Energy capacity for storage technology j
    model.Ecap = Var(model.storage.j, domain=NonNegativeReals, initialize=0)

    model.Ystorage = Var(model.storage.j, model.h, domain=Binary, initialize=0)


####################################################################################|
# ----------------------------------- Add_costs -----------------------------------|
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
                    MW_TO_KW * model.StorageData['CostRatio', j] * \
                    model.StorageData['P_Capex', j]*model.Pcha[j]
                    + MW_TO_KW *(1 - model.StorageData['CostRatio', j]) * \
                    model.StorageData['P_Capex', j]*model.Pdis[j]
                    + MW_TO_KW *model.StorageData['E_Capex', j]*model.Ecap[j]
                )
                + MW_TO_KW *model.StorageData['CostRatio', j] * \
                model.StorageData['FOM', j]*model.Pcha[j]
                + MW_TO_KW *(1 - model.StorageData['CostRatio', j]) * \
                model.StorageData['FOM', j]*model.Pdis[j]
                for j in model.storage.j
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
                  for h in model.h) for j in model.storage.j )
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
def max_cycle_year_rule(model): #TODO check here this hardcoded Li-Ion
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
    model.ChargSt= Constraint(model.h, model.storage.j, rule=lambda m, h, j: m.PC[h, j] <= m.StorageData['Max_P', j] * m.Ystorage[j, h])
    model.DischargeSt = Constraint(model.h, model.storage.j, rule=lambda m, h, j: m.PD[h, j] <= m.StorageData['Max_P', j] * (1 - m.Ystorage[j, h]))

    # Hourly capacity bounds
    model.MaxHourlyCharging = Constraint(model.h, model.storage.j, rule= lambda m,h,j: m.PC[h, j] <= m.Pcha[j])
    model.MaxHourlyDischarging = Constraint(model.h, model.storage.j, rule= lambda m,h,j: m.PD[h, j] <= m.Pdis[j])

    # Limit state of charge of storage by its capacity
    model.MaxSOC = Constraint(model.h, model.storage.j, rule=lambda m, h, j: m.SOC[h,j]<= m.Ecap[j])
    # SOC Balance Constraint
    model.SOCBalance = Constraint(model.h, model.storage.j, rule=soc_balance_rule)

    # - Constraints on the maximum charging (Pcha) and discharging (Pdis) power for each technology
    model.MaxPcha = Constraint( model.storage.j, rule=lambda m, j: m.Pcha[j] <= m.StorageData['Max_P', j] )
    model.MaxPdis = Constraint( model.storage.j, rule=lambda m, j: m.Pdis[j] <= m.StorageData['Max_P', j] )

    # Charge and discharge rates are equal -
    model.PchaPdis = Constraint( model.storage.b, rule=lambda m, j: m.Pcha[j] == m.Pdis[j] )

    # Max and min energy capacity constraints (handle uninitialized variables)
    model.MinEcap = Constraint(model.storage.j, rule= lambda m,j: m.Ecap[j] >= m.StorageData['Min_Duration', j] * m.Pdis[j] / sqrt(m.StorageData['Eff', j]))
    model.MaxEcap = Constraint(model.storage.j, rule= lambda m,j: m.Ecap[j] <= m.StorageData['Max_Duration', j] * m.Pdis[j] / sqrt(m.StorageData['Eff', j]))


    model.MaxCycleYear = Constraint(rule=max_cycle_year_rule)