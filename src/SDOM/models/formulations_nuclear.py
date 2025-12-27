"""Nuclear generation formulations for the SDOM optimization model.

This module implements nuclear power modeling as must-run generation following
a predetermined schedule. Nuclear plants typically operate at near-constant
output due to economic and technical constraints, with outages for refueling
and maintenance reflected in the historical time series.
"""

from pyomo.environ import Param
from .models_utils import add_alpha_and_ts_parameters

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_nuclear_parameters(model, data: dict):
    """
    Adds nuclear generation parameters to the model.
    
    Nuclear is modeled as a fixed time series scaled by an alpha parameter.
    The time series typically shows near-constant generation with periodic
    drops for refueling outages. Nuclear generation is non-dispatchable
    (must-run) in the optimization.
    
    Args:
        model: The Pyomo ConcreteModel instance.
        data (dict): Dictionary containing:
            - 'scalars' DataFrame with 'AlphaNuclear' scaling factor
            - 'nuclear_data' DataFrame with hourly historical generation
    
    Side Effects:
        Adds parameters to model.nuclear block:
        - model.nuclear.alpha (Param): Nuclear capacity scaling factor
        - model.nuclear.ts_parameter[h] (Param): Hourly generation pattern (MW)
    
    Notes:
        Actual generation in hour h is: alpha × ts_parameter[h]
    """
    add_alpha_and_ts_parameters(model.nuclear, model.h, data, "AlphaNuclear", "nuclear_data", "Nuclear")
    