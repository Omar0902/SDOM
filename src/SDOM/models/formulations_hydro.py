"""Hydropower generation formulations for the SDOM optimization model.

This module implements multiple hydropower modeling approaches:
- Run-of-River: Fixed hourly generation following historical patterns
- Daily Budget: Flexible dispatch within daily energy budgets
- Monthly Budget: Flexible dispatch within monthly energy budgets

Each formulation allows different degrees of operational flexibility while respecting
physical constraints on reservoir operations.
"""

from pyexpat import model
from pyomo.environ import Set, Param, value, NonNegativeReals
from .models_utils import add_generation_variables, add_alpha_and_ts_parameters, add_budget_parameter, add_upper_bound_paramenters, add_lower_bound_paramenters, generic_budget_rule
from pyomo.core import Var, Constraint, Expression

from ..constants import VALID_HYDRO_FORMULATIONS_TO_BUDGET_MAP, MONTHLY_BUDGET_HOURS_AGGREGATION, DAILY_BUDGET_HOURS_AGGREGATION
from ..io_manager import get_formulation


####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_large_hydro_parameters(model, data: dict):
    """
    Adds hydropower parameters to the model including scaling factors and time series.
    
    This function initializes:
    - alpha: Scaling factor for historical hydro generation
    - ts_parameter: Hourly historical generation time series (MW)
    - budget_hours_aggregation: Aggregation interval for budget formulations
    
    Args:
        model: The Pyomo ConcreteModel instance.
        data (dict): Dictionary containing 'large_hydro_data' DataFrame with hourly
            generation data and 'formulations' specifying the hydro formulation type.
    
    Side Effects:
        Adds parameters to model.hydro block:
        - model.hydro.alpha (Param): Hydropower capacity scaling factor
        - model.hydro.ts_parameter (Param[h]): Historical generation time series
        - model.hydro.budget_hours_aggregation (Param): Hours per budget period (if applicable)
    """
    add_alpha_and_ts_parameters(model.hydro, model.h, data, "AlphaLargHy", "large_hydro_data", "LargeHydro")
    formulation = get_formulation(data, component='hydro')
    add_budget_parameter(model.hydro, formulation, VALID_HYDRO_FORMULATIONS_TO_BUDGET_MAP)


def add_large_hydro_bound_parameters(model, data: dict):
    """
    Adds upper and lower bound parameters for hydropower generation in budget formulations.
    
    These bounds represent physical constraints on reservoir operations:
    - Maximum generation based on available water and turbine capacity
    - Minimum generation for ecological flow requirements or operational constraints
    
    Only used with Daily or Monthly Budget formulations; not needed for Run-of-River.
    
    Args:
        model: The Pyomo ConcreteModel instance.
        data (dict): Dictionary containing 'large_hydro_max' and 'large_hydro_min'
            DataFrames with hourly upper and lower generation bounds (MW).
    
    Side Effects:
        Adds time-indexed parameters to model.hydro block:
        - model.hydro.ts_parameter_upper_bound[h] (Param): Maximum generation per hour (MW)
        - model.hydro.ts_parameter_lower_bound[h] (Param): Minimum generation per hour (MW)
    """
    # Time-series parameter data initialization
    add_upper_bound_paramenters(model.hydro, model.h, data, "large_hydro_max", "LargeHydro")
    add_lower_bound_paramenters(model.hydro, model.h, data, "large_hydro_min", "LargeHydro")



####################################################################################|
# ------------------------------------ Variables -----------------------------------|
####################################################################################|

def add_hydro_variables(model):
    """
    Adds hydropower generation decision variables to the model.
    
    Creates hourly generation variables for large hydropower facilities. The interpretation
    depends on the formulation:
    - Run-of-River: Fixed to historical patterns (essentially a parameter)
    - Budget: Optimized within energy budget and physical bounds
    
    Args:
        model: The Pyomo ConcreteModel instance.
    
    Side Effects:
        Adds to model.hydro block:
        - model.hydro.generation[h] (Var): Hourly hydropower generation (MW), h ∈ model.h
          Domain: NonNegativeReals, initialized to 0
    """
    add_generation_variables(model.hydro, model.h, domain=NonNegativeReals, initialize=0)

####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|

def add_hydro_run_of_river_constraints(model, data: dict):
    """
    Adds run-of-river constraints that fix hydropower generation to historical patterns.
    
    Run-of-river formulation assumes hydropower follows a predetermined schedule based
    on historical generation, scaled by an alpha factor. This represents systems with
    limited or no reservoir storage capacity.
    
    Mathematical Formulation:
        For all hours h:
        $$G_{hydro}(h) = \alpha_{hydro} \cdot \overline{G}_{hydro}(h)$$
    
    Where:
        - $G_{hydro}(h)$: Actual generation in hour h (MW)
        - $\alpha_{hydro}$: Scaling factor (typically 1.0)
        - $\overline{G}_{hydro}(h)$: Historical generation pattern in hour h (MW)
    
    Args:
        model: The Pyomo ConcreteModel instance with hydro variables and parameters.
        data (dict): Dictionary containing input data (not used in this formulation).
    
    Side Effects:
        Adds constraint to model.hydro block:
        - model.hydro.run_of_river_constraint[h]: Equality constraint fixing generation
    
    Returns:
        None
    """
    model.hydro.run_of_river_constraint = Constraint(model.h, rule=lambda m,h: m.generation[h] == m.alpha * m.ts_parameter[h] )
    return


def add_hydro_budget_constraints(model, data: dict):
    """
    Adds budget-based constraints for flexible hydropower dispatch.
    
    Budget formulations allow operational flexibility by permitting generation to vary
    within hourly bounds, subject to cumulative energy constraints over budget periods
    (daily or monthly). This represents systems with reservoir storage.
    
    Mathematical Formulation:
        Hourly bounds for all h:
        $$\alpha_{hydro} \cdot \underline{G}_{hydro}(h) \leq G_{hydro}(h) \leq \alpha_{hydro} \cdot \overline{G}_{hydro}(h)$$
        
        Budget constraint for each period p:
        $$\sum_{h \in \mathcal{H}_p} G_{hydro}(h) \leq Budget_p$$
    
    Where:
        - $G_{hydro}(h)$: Hydropower generation in hour h (MW)
        - $\alpha_{hydro}$: Capacity scaling factor
        - $\underline{G}_{hydro}(h)$, $\overline{G}_{hydro}(h)$: Min/max generation bounds (MW)
        - $\mathcal{H}_p$: Set of hours in budget period p
        - $Budget_p$: Total energy available in period p (MWh)
    
    Args:
        model: The Pyomo ConcreteModel instance with hydro variables, parameters, and budget_set.
        data (dict): Dictionary containing input data (not directly used).
    
    Side Effects:
        Adds constraints to model.hydro block:
        - model.hydro.upper_bound_ts_constraint[h]: Hourly maximum generation
        - model.hydro.lower_bound_ts_constraint[h]: Hourly minimum generation  
        - model.hydro.budget_constraint[p]: Energy budget for period p
    
    Returns:
        None
    """
    model.hydro.upper_bound_ts_constraint = Constraint(model.h, rule=lambda m,h: m.generation[h] <= m.alpha * m.ts_parameter_upper_bound[h] )
    model.hydro.lower_bound_ts_constraint = Constraint(model.h, rule=lambda m,h: m.generation[h] >= m.alpha * m.ts_parameter_lower_bound[h] )

    model.hydro.budget_constraint = Constraint(model.hydro.budget_set, rule = generic_budget_rule )
    
    return
