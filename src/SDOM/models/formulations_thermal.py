from pyomo.core import Var, Constraint, Expression
from pyomo.environ import Param, value, NonNegativeReals
import logging
from .models_utils import fcr_rule_thermal
from ..constants import MW_TO_KW, THERMAL_PROPERTIES_NAMES

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|
def add_thermal_parameters(model, data):

    df = data["thermal_data"].set_index("Plant_id")
    thermal_dict = df.stack().to_dict()
    thermal_tuple_dict = {( prop, name ): thermal_dict[( name, prop )] for prop in THERMAL_PROPERTIES_NAMES for name in model.bu}
    
    model.ThermalData = Param( model.tp, model.bu, initialize = thermal_tuple_dict )
    
    # Gas prices (US$/MMBtu)
    model.GasPrice = Param(
        model.bu,
        initialize={bu: model.ThermalData["FuelCost", bu] for bu in model.bu}
    )

    # Heat rate for gas combined cycle (MMBtu/MWh)
    model.HR = Param( 
        model.bu, 
        initialize = {bu: model.ThermalData["HeatRate", bu] for bu in model.bu}
    )

    # Capex for gas combined cycle units (US$/kW)
    model.CapexGasCC = Param( 
        model.bu, 
        initialize ={bu: model.ThermalData["Capex", bu] for bu in model.bu}
    )

    # Fixed O&M for gas combined cycle (US$/kW-year)
    model.FOM_GasCC = Param( 
        model.bu, 
        initialize = {bu: model.ThermalData["FOM", bu] for bu in model.bu}
    )

    # Variable O&M for gas combined cycle (US$/MWh)
    model.VOM_GasCC = Param( 
        model.bu, 
        initialize = {bu: model.ThermalData["VOM", bu] for bu in model.bu} 
    )

    model.FCR_GasCC = Param( model.bu, initialize = fcr_rule_thermal ) #Capital Recovery Factor -THERMAL


####################################################################################|
# ------------------------------------ Variables -----------------------------------|
####################################################################################|

def annual_thermal_expr_rule(m):
    """
    Expression to calculate the annual generation from thermal units.
    
    Parameters:
    m: The optimization model instance.
    h: Time period index.
    bu: Balancing unit index.
    
    Returns:
    The sum of generation from the specified thermal unit across all time periods.
    """
    return sum(m.GenCC[h, bu] for h in m.h for bu in m.bu)


def add_thermal_variables(model):
    model.CapCC = Var(model.bu, domain=NonNegativeReals, initialize=0)
    model.GenCC = Var(model.h, model.bu, domain=NonNegativeReals,initialize=0)  # Generation from thermal units

    # Compute and set the upper bound for CapCC
    CapCC_upper_bound_value = max(
        value(model.Load[h]) - value(model.AlphaNuclear) *
        value(model.Nuclear[h])
        - value(model.AlphaLargHy) * value(model.LargeHydro[h])
        - value(model.AlphaOtheRe) * value(model.OtherRenewables[h])
        for h in model.h
    )

    if ( len( list(model.bu) ) <= 1 ) & ( CapCC_upper_bound_value > model.ThermalData['MaxCapacity', model.bu[1]] ):
        model.CapCC[model.bu[1]].setub( CapCC_upper_bound_value )
        logging.warning(f"There is only one thermal balancing unit. " \
        f"Upper bound for Capacity variable was set to {CapCC_upper_bound_value} instead of the input = {model.ThermalData['MaxCapacity', model.bu[1]]} to ensure feasibility.")
    else:
        sum_cap = 0
        for bu in model.bu:
            model.CapCC[bu].setub( model.ThermalData["MaxCapacity", bu] )
            model.CapCC[bu].setlb( model.ThermalData["MinCapacity", bu] )
            sum_cap += model.ThermalData["MaxCapacity", bu]
        if ( CapCC_upper_bound_value > model.ThermalData['MaxCapacity', model.bu[1]] ):
            logging.warning(f"Total allowed capacity for thermal units is {sum_cap}MW. This value might be insufficient to achieve problem feasibility, consider increase it to at least {CapCC_upper_bound_value}MW.")

def add_thermal_expressions(model):
    model.annual_thermal_gen_expr = Expression(rule=annual_thermal_expr_rule )
    

####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|

def add_thermal_constraints( model ):
    # Capacity of the backup generation
    model.BackupGen = Constraint( model.h, model.bu, rule = lambda m,h,bu: m.CapCC[bu] >= m.GenCC[h,bu]  )



####################################################################################|
# -----------------------------------= Add_costs -----------------------------------|
####################################################################################|
def add_thermal_fixed_costs(model):
    """
    Add cost-related variables for thermal units to the model.

    Parameters:
    model: The optimization model to which thermal cost variables will be added.

    Returns:
    Costs sum for each thermal unit, including capital and fixed O&M costs.
    """
    return (
        sum(
            model.FCR_GasCC[bu]*MW_TO_KW*model.CapexGasCC[bu]*model.CapCC[bu]
            + MW_TO_KW*model.FOM_GasCC[bu]*model.CapCC[bu]
            for bu in model.bu
        )
    )

def add_thermal_variable_costs(model):
    """
    Add variable costs for thermal units to the model.

    Parameters:
    model: The optimization model to which thermal variable costs will be added.

    Returns:
    Variable costs sum for thermal units, including fuel costs.
    """
    return (

        sum(
            (model.GasPrice[bu] * model.HR[bu] + model.VOM_GasCC[bu]) *
            sum(model.GenCC[h, bu] for h in model.h)
            for bu in model.bu )
    )

