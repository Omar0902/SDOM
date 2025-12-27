"""Utility functions for building Pyomo model components.

This module provides reusable functions for:
- Financial calculations (FCR, CRF for annualizing capital costs)
- Parameter initialization (time series, alpha factors, bounds, budgets)
- Variable creation (generation variables)
- Expression building (capacity totals, cost calculations)
- Constraint rules (budget constraints)

These utilities promote code reuse across different technology formulations.
"""

from pyomo.environ import Param, NonNegativeReals
from pyomo.core import Var
from ..constants import MW_TO_KW

def fcr_rule( model, lifetime = 30 ):
    """
    Calculates the Fixed Charge Rates (FCR) for annualizing capital costs.
    
    FCR converts a one-time capital investment into an equivalent annual cost,
    accounting for the discount rate and equipment lifetime. Used for technologies
    with uniform lifetimes (e.g., VRE and thermal generation).
    
    Mathematical Formula:
        $$FCR = \frac{r(1+r)^{lifetime}}{(1+r)^{lifetime} - 1}$$
    
    Where:
        - $r$: Discount rate (e.g., 0.07 for 7%)
        - $lifetime$: Equipment lifetime in years
    
    Args:
        model: Pyomo model or block containing parameter 'r' (discount rate).
        lifetime (int, optional): Asset lifetime in years. Defaults to 30.
    
    Returns:
        float: Fixed charge rate (dimensionless factor)
    """
    return ( model.r * (1 + model.r) ** lifetime ) / ( (1 + model.r) ** lifetime - 1 )


# Capital recovery factor for storage
def crf_rule( model, j ):
    """
    Calculates the Capital Recovery Factor (CRF) for storage technologies.
    
    Similar to FCR but reads technology-specific lifetimes from model.data.
    Each storage technology may have a different lifetime (e.g., Li-Ion: 15 years,
    PHS: 50 years), requiring individual CRF calculations.
    
    Mathematical Formula:
        $$CRF_j = \frac{r(1+r)^{lifetime_j}}{(1+r)^{lifetime_j} - 1}$$
    
    Args:
        model: Pyomo storage block containing 'r' and 'data' parameters.
        j: Storage technology index.
    
    Returns:
        float: Capital recovery factor for technology j.
    """
    lifetime = model.data['Lifetime', j]
    return ( model.r * (1 + model.r) ** lifetime ) / ( (1 + model.r) ** lifetime - 1 )


####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|
def get_filtered_ts_parameter_dict( hourly_set, data: dict, key_ts: str, key_col: str):
    """
    Extracts and filters a time-series parameter for specified hours.
    
    Reads a time-series DataFrame from data, extracts a specific column, and
    filters it to include only hours present in the model's hourly set.
    
    Args:
        hourly_set: Pyomo Set or iterable of hour indices to include.
        data (dict): Dictionary containing time-series DataFrames.
        key_ts (str): Key for the DataFrame in data dictionary.
        key_col (str): Column name to extract from the DataFrame.
    
    Returns:
        dict: Mapping from hour indices to parameter values, e.g., {1: 150.2, 2: 148.7, ...}
    """
    selected_data          = data[key_ts].set_index('*Hour')[key_col].to_dict()
    filtered_selected_data = {h: selected_data[h] for h in hourly_set if h in selected_data}
    return filtered_selected_data

def add_alpha_parameter(block, data, key_scalars: str):
    """
    Adds an alpha scaling parameter to a Pyomo block if it doesn't already exist.
    
    Alpha parameters scale historical generation profiles to represent different
    capacity levels (e.g., nuclear, hydro, other renewables). An alpha of 1.0
    means using historical generation as-is.
    
    Args:
        block: Pyomo Block where the parameter will be added.
        data (dict): Dictionary containing 'scalars' DataFrame.
        key_scalars (str): Row name in scalars DataFrame. If empty string, no parameter added.
    
    Side Effects:
        Adds block.alpha (Param) if key_scalars is non-empty and alpha doesn't exist.
    """
    if not hasattr(block, "alpha") and key_scalars != "":
        block.alpha = Param( initialize = float(data["scalars"].loc[key_scalars].Value) )

def add_alpha_and_ts_parameters( block, 
                                hourly_set, 
                                data: dict, 
                                key_scalars: str, 
                                key_ts: str,
                                key_col: str):
    """
    Adds both alpha scaling factor and time-series parameter to a block.
    
    Convenience function combining add_alpha_parameter and time-series initialization.
    Used for technologies with fixed generation profiles (nuclear, hydro, other renewables).
    
    Args:
        block: Pyomo Block where parameters will be added.
        hourly_set: Pyomo Set of hour indices.
        data (dict): Dictionary containing input data.
        key_scalars (str): Row name in scalars DataFrame for alpha value.
        key_ts (str): Key for time-series DataFrame in data.
        key_col (str): Column name to extract from time-series DataFrame.
    
    Side Effects:
        Adds to block:
        - block.alpha (Param): Scaling factor
        - block.ts_parameter[h] (Param): Time-series values for each hour h
    """
    # Control parameter to activate certain device.
    add_alpha_parameter(block, data, key_scalars)

    # Time-series parameter data initialization
    filtered_selected_data = get_filtered_ts_parameter_dict(hourly_set, data, key_ts, key_col)
    block.ts_parameter = Param( hourly_set, initialize = filtered_selected_data)


def add_budget_parameter(block, formulation, valid_formulation_to_budget_map: dict):
    """
    Adds a budget aggregation interval parameter based on the selected formulation.
    
    Args:
        block: Pyomo Block where the parameter will be added.
        formulation (str): Formulation name (e.g., 'MonthlyBudgetFormulation').
        valid_formulation_to_budget_map (dict): Mapping from formulation names to
            aggregation intervals in hours.
    
    Side Effects:
        Adds block.budget_scalar (Param) with the aggregation interval.
    """
    if not hasattr(block, "budget_scalar"):
        block.budget_scalar = Param( initialize = valid_formulation_to_budget_map[formulation])

def add_upper_bound_paramenters(block, 
                                hourly_set, 
                                data, 
                                key_ts: str = "large_hydro_max", 
                                key_col: str = "LargeHydro"):
    """
    Adds hourly upper bound time-series parameter to a block.
    
    Used for technologies with operational limits (e.g., maximum hydro generation
    based on reservoir levels and turbine capacity).
    
    Args:
        block: Pyomo Block where the parameter will be added.
        hourly_set: Pyomo Set of hour indices.
        data (dict): Dictionary containing time-series data.
        key_ts (str, optional): Key for DataFrame in data. Defaults to "large_hydro_max".
        key_col (str, optional): Column name to extract. Defaults to "LargeHydro".
    
    Side Effects:
        Adds block.ts_parameter_upper_bound[h] (Param): Maximum values for each hour h.
    """
    selected_data          = data[key_ts].set_index('*Hour')[key_col].to_dict()
    filtered_selected_data = {h: selected_data[h] for h in hourly_set if h in selected_data}
    block.ts_parameter_upper_bound = Param( hourly_set, initialize = filtered_selected_data)

def add_lower_bound_paramenters(block, 
                                hourly_set, 
                                data: dict, 
                                key_ts: str = "large_hydro_min", 
                                key_col: str = "LargeHydro"):
    """
    Adds hourly lower bound time-series parameter to a block.
    
    Used for technologies with minimum operation requirements (e.g., minimum hydro
    generation for ecological flows or operational stability).
    
    Args:
        block: Pyomo Block where the parameter will be added.
        hourly_set: Pyomo Set of hour indices.
        data (dict): Dictionary containing time-series data.
        key_ts (str, optional): Key for DataFrame in data. Defaults to "large_hydro_min".
        key_col (str, optional): Column name to extract. Defaults to "LargeHydro".
    
    Side Effects:
        Adds block.ts_parameter_lower_bound[h] (Param): Minimum values for each hour h.
    """
    selected_data          = data[key_ts].set_index('*Hour')[key_col].to_dict()
    filtered_selected_data = {h: selected_data[h] for h in hourly_set if h in selected_data}
    block.ts_parameter_lower_bound = Param( hourly_set, initialize = filtered_selected_data)

####################################################################################|
# ------------------------------------ Variables -----------------------------------|
####################################################################################|
def add_generation_variables(block, *sets, domain=NonNegativeReals, initialize=0):
    """
    Adds a generation variable to the block over an arbitrary number of sets.

    Parameters:
    block: The Pyomo block to which the variable will be added.
    *sets: Any number of iterable sets to define the variable's index.
    initialize: Initial value for the variable.

    Example:
    add_generation_variables(block, set_hours)
    add_generation_variables(block, set_plants, set_hours)
    """
    block.generation = Var(*sets, domain=domain, initialize=initialize)

# def add_generation_variables(block, set_hours, initialize=0):
#     block.generation = Var(set_hours, domain=NonNegativeReals, initialize=initialize)



####################################################################################|
# ----------------------------------- Expressions ----------------------------------|
####################################################################################|

def sum_installed_capacity_by_plants_set_expr_rule( block ):
    """
    Expression to calculate the total installed capacity for plants contained in a plants_set of a pyomo block.
    """
    return sum( block.plant_installed_capacity[plant] for plant in block.plants_set )
 

def generic_fixed_om_cost_expr_rule( block ):
    """
    Expression to calculate the fixed O&M costs for generic technologies.
    """
    return sum( ( MW_TO_KW * block.FOM_M[k]) * block.plant_installed_capacity[k] for k in block.plants_set )


def generic_capex_cost_expr_rule( block ):
    """
    Expression to calculate the capital expenditures (Capex) for generic technologies when lifetime and fcr are the same for all the "block.plants_set".
    """
    return sum( ( (MW_TO_KW * block.CAPEX_M[k] + block.trans_cap_cost[k]))\
                                         * block.plant_installed_capacity[k] for k in block.plants_set )


def different_fcr_capex_cost_expr_rule( block ):
    """
    Expression to calculate the capital expenditures (Capex) for generic technologies when lifetime and fcr are specific for each element in "block.plants_set".
    """
    return sum( ( block.FCR[k] * (MW_TO_KW * block.CAPEX_M[k] + block.trans_cap_cost[k]))\
                                         * block.plant_installed_capacity[k] for k in block.plants_set )


####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|

def generic_budget_rule(block, hhh):
    budget_n_hours = block.budget_scalar
    start = ( (hhh - 1) * budget_n_hours ) + 1
    end = hhh * budget_n_hours + 1
    list_budget = list(range(start, end))
    return sum(block.generation[h] for h in list_budget) == sum(block.ts_parameter[h] for h in list_budget)

####################################################################################|
# -----------------------------------= Add_costs -----------------------------------|
####################################################################################|

def add_generic_fixed_costs(block):
    """
    Add fixed costs (FOM+CAPEX) for generic technologies to the block.
    
    Parameters:
    block: The optimization block to which cost variables will be added.
    The block should have the expressions `capex_cost_expr` and `fixed_om_cost_expr`.

    Returns:
    Costs sum for generic technologies, including capital and fixed O&M costs.
    """
    return block.capex_cost_expr + block.fixed_om_cost_expr