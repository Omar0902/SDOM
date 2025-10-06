from pyexpat import model
from pyomo.environ import Set, Param, value, NonNegativeReals
from .models_utils import add_generation_variables, add_alpha_and_ts_parameters, add_budget_parameter, add_upper_bound_paramenters, add_lower_bound_paramenters
from pyomo.core import Var, Constraint, Expression

from ..constants import VALID_HYDRO_FORMULATIONS_TO_BUDGET_MAP, MONTHLY_BUDGET_HOURS_AGGREGATION, DAILY_BUDGET_HOURS_AGGREGATION
from ..io_manager import get_formulation


####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_large_hydro_parameters(model, data):
    add_alpha_and_ts_parameters(model.hydro, model.h, data, "AlphaLargHy", "large_hydro_data", "LargeHydro")
    formulation = get_formulation(data, component='hydro')
    add_budget_parameter(model.hydro, formulation, VALID_HYDRO_FORMULATIONS_TO_BUDGET_MAP)


def add_large_hydro_bound_parameters(model, data):
    # Time-series parameter data initialization
    add_upper_bound_paramenters(model.hydro, model.h, data, "large_hydro_max", "LargeHydro")
    add_lower_bound_paramenters(model.hydro, model.h, data, "large_hydro_min", "LargeHydro")



####################################################################################|
# ------------------------------------ Variables -----------------------------------|
####################################################################################|

def add_hydro_variables(model):
    add_generation_variables(model.hydro, model.h, initialize=0) # Generation from hydro units
    #print(model.hydro.generation.pprint())
    #print(model.hydro.budget_set.pprint())

####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|

def add_hydro_run_of_river_constraints(model, data):
    model.hydro.run_of_river_constraint = Constraint(model.h, rule=lambda m,h: m.generation[h] == m.alpha * m.ts_parameter[h] )
    return

def monthly_hydro_budget_rule(block, hhh):
    start = ( (hhh - 1) * MONTHLY_BUDGET_HOURS_AGGREGATION ) + 1
    end = hhh * MONTHLY_BUDGET_HOURS_AGGREGATION
    list_budget = list(range(start, end))
    print(list_budget)
    return sum(block.generation[h] for h in list_budget) == sum(block.ts_parameter[h] for h in list_budget)


def daily_hydro_budget_rule(block, hhh):
    start = ( (hhh - 1) * DAILY_BUDGET_HOURS_AGGREGATION ) + 1
    end = hhh * DAILY_BUDGET_HOURS_AGGREGATION
    list_budget = list(range(start, end))
    return sum(block.generation[h] for h in list_budget) == sum(block.ts_parameter[h] for h in list_budget)


def add_hydro_budget_constraints(model, data):
    
    model.hydro.upper_bound_ts_constraint = Constraint(model.h, rule=lambda m,h: m.generation[h] <= m.alpha * m.ts_parameter_upper_bound[h] )
    model.hydro.lower_bound_ts_constraint = Constraint(model.h, rule=lambda m,h: m.generation[h] >= m.alpha * m.ts_parameter_lower_bound[h] )

    formulation = get_formulation(data, component='hydro')
    if formulation == "MonthlyBudgetHydroFormulation":
        model.hydro.budget_constraint = Constraint(model.hydro.budget_set, rule = monthly_hydro_budget_rule )
    elif formulation == "DailyBudgetHydroFormulation":
       model.hydro.budget_constraint = Constraint(model.hydro.budget_set, rule = daily_hydro_budget_rule )
    
    return
