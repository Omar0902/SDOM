from pyomo.core import Var, Constraint, Expression
from pyomo.environ import Set, Param, value, NonNegativeReals
import logging
from .models_utils import fcr_rule_thermal
from ..constants import MW_TO_KW, THERMAL_PROPERTIES_NAMES

def initialize_thermal_sets(block, data):
    # Initialize THERMAL properties
    block.bu = Set( initialize = data['thermal_data']['Plant_id'].astype(str).tolist() )
    block.tp = Set( initialize = THERMAL_PROPERTIES_NAMES )
    logging.info(f"Thermal balancing units being considered: {list(block.bu)}")

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def _add_thermal_parameters(block, df):
    
    thermal_dict = df.stack().to_dict()
    thermal_tuple_dict = {( prop, name ): thermal_dict[( name, prop )] for prop in THERMAL_PROPERTIES_NAMES for name in block.bu}
    
    block.ThermalData = Param( block.tp, block.bu, initialize = thermal_tuple_dict )
    
    # Gas prices (US$/MMBtu)
    block.fuel_price = Param(
        block.bu,
        initialize={bu: block.ThermalData["FuelCost", bu] for bu in block.bu}
    )

    # Heat rate for gas combined cycle (MMBtu/MWh)
    block.heat_rate = Param( 
        block.bu, 
        initialize = {bu: block.ThermalData["HeatRate", bu] for bu in block.bu}
    )
#block.GasPrice, block.HR, block.FOM_GasCC, block.VOM_GasCC
    # Capex for gas combined cycle units (US$/kW)
    block.CAPEX_M = Param( 
        block.bu, 
        initialize ={bu: block.ThermalData["Capex", bu] for bu in block.bu}
    )

    # Fixed O&M for gas combined cycle (US$/kW-year)
    block.FOM_M = Param( 
        block.bu, 
        initialize = {bu: block.ThermalData["FOM", bu] for bu in block.bu}
    )

    # Variable O&M for gas combined cycle (US$/MWh)
    block.VOM_M = Param( 
        block.bu, 
        initialize = {bu: block.ThermalData["VOM", bu] for bu in block.bu} 
    )



def add_thermal_parameters(model, data):
    df = data["thermal_data"].set_index("Plant_id")
    _add_thermal_parameters(model.thermal, df)
    model.thermal.r = Param( initialize = float(data["scalars"].loc["r"].Value) )  # Interest rate
    model.thermal.FCR = Param( model.thermal.bu, initialize = fcr_rule_thermal ) #Capital Recovery Factor -THERMAL

####################################################################################|
# ------------------------------------ Variables -----------------------------------|
####################################################################################|

def add_thermal_variables(model):
    model.thermal.capacity = Var(model.thermal.bu, domain=NonNegativeReals, initialize=0)
    model.thermal.generation = Var(model.h, model.thermal.bu, domain=NonNegativeReals,initialize=0)  # Generation from thermal units
    #model.thermal.CapCC, model.thermal.GenCC
    # Compute and set the upper bound for CapCC
    CapCC_upper_bound_value = max(
        value(model.demand.ts_parameter[h]) - value(model.nuclear.alpha) *
        value(model.nuclear.ts_parameter[h])
        - value(model.hydro.alpha) * value(model.hydro.ts_parameter[h])
        - value(model.other_renewables.alpha) * value(model.other_renewables.ts_parameter[h])
        for h in model.h
    )

    if ( len( list(model.thermal.bu) ) <= 1 ) & ( CapCC_upper_bound_value > model.thermal.ThermalData['MaxCapacity', model.thermal.bu[1]] ):
        model.thermal.capacity[model.thermal.bu[1]].setub( CapCC_upper_bound_value )
        logging.warning(f"There is only one thermal balancing unit. " \
        f"Upper bound for Capacity variable was set to {CapCC_upper_bound_value} instead of the input = {model.thermal.ThermalData['MaxCapacity', model.thermal.bu[1]]} to ensure feasibility.")
    else:
        sum_cap = 0
        for bu in model.thermal.bu:
            model.thermal.capacity[bu].setub( model.thermal.ThermalData["MaxCapacity", bu] )
            model.thermal.capacity[bu].setlb( model.thermal.ThermalData["MinCapacity", bu] )
            sum_cap += model.thermal.ThermalData["MaxCapacity", bu]
        if ( CapCC_upper_bound_value > model.thermal.ThermalData['MaxCapacity', model.thermal.bu[1]] ):
            logging.warning(f"Total allowed capacity for thermal units is {sum_cap}MW. This value might be insufficient to achieve problem feasibility, consider increase it to at least {CapCC_upper_bound_value}MW.")


####################################################################################|
# ----------------------------------- Expressions ----------------------------------|
####################################################################################|
def total_thermal_expr_rule(m):
    """
    Expression to calculate the total generation from thermal units.
    
    Parameters:
    m: The optimization model instance.
    h: Time period index.
    bu: Balancing unit index.
    
    Returns:
    The sum of generation from the specified thermal unit across all time periods.
    """
    return sum(m.GenCC[h, bu] for h in m.h for bu in m.thermal.bu)

def _add_thermal_expressions(block, set_hours):
    block.total_generation = Expression( rule = sum(block.generation[h, bu] for h in set_hours for bu in block.bu) )

def add_thermal_expressions(model):
    _add_thermal_expressions(model.thermal, model.h)
    #model.thermal.total_generation = Expression( rule = total_thermal_expr_rule )
    


####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|

def add_thermal_constraints( model ):
    set_hours = model.h
    # Capacity of the backup generation
    model.thermal.BackupGen = Constraint( set_hours, model.thermal.bu, rule = lambda m,h,bu: m.capacity[bu] >= m.generation[h,bu]  )



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
            model.thermal.FCR[bu]*MW_TO_KW*model.thermal.CAPEX_M[bu]*model.thermal.capacity[bu]
            + MW_TO_KW*model.thermal.FOM_M[bu]*model.thermal.capacity[bu]
            for bu in model.thermal.bu
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
            (model.thermal.fuel_price[bu] * model.thermal.heat_rate[bu] + model.thermal.VOM_M[bu]) *
            sum(model.thermal.generation    [h, bu] for h in model.h)
            for bu in model.thermal.bu )
    )

