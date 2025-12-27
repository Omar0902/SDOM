"""Load (electricity demand) formulations for the SDOM optimization model.

This module implements electricity demand modeling as a time-series parameter.
Demand is treated as a fixed input (inelastic), though the alpha parameter allows
scaling for sensitivity analysis or future growth scenarios.
"""

from pyomo.environ import Param
from .models_utils import add_alpha_and_ts_parameters
####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_load_parameters(model, data: dict):
    """
    Adds hourly electricity demand parameters to the model.
    
    Load is modeled as an exogenous time series representing electricity consumption
    that must be met by the system. The alpha parameter is optional and typically set
    to 1.0 (using demand as provided) but can be adjusted for scenarios.
    
    Args:
        model: The Pyomo ConcreteModel instance.
        data (dict): Dictionary containing 'load_data' DataFrame with hourly demand values.
    
    Side Effects:
        Adds parameters to model.demand block:
        - model.demand.alpha (Param): Demand scaling factor (optional, typically 1.0)
        - model.demand.ts_parameter[h] (Param): Hourly demand in MW for each hour h
    
    Notes:
        In the current implementation, alpha is empty ("") so only ts_parameter is added.
    """
    add_alpha_and_ts_parameters(model.demand, model.h, data, "", "load_data", "Load")
