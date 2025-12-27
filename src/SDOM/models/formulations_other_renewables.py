"""Other renewable generation formulations for the SDOM optimization model.

This module implements modeling for renewable energy sources other than solar PV
and wind, including:
- Biomass/biogas
- Geothermal
- Small-scale hydro (not categorized as large hydro)
- Any other existing renewable generation

These are modeled as must-run generation with fixed profiles.
"""

from pyomo.environ import Param
from .models_utils import add_alpha_and_ts_parameters

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_other_renewables_parameters(model, data: dict):
    """
    Adds other renewable generation parameters to the model.
    
    Other renewables (biomass, geothermal, etc.) are modeled as must-run generation
    following historical patterns, scaled by an alpha factor. These resources are
    typically dispatchable to some degree in reality, but modeled as fixed for simplicity.
    
    Args:
        model: The Pyomo ConcreteModel instance.
        data (dict): Dictionary containing:
            - 'scalars' DataFrame with 'AlphaOtheRe' scaling factor
            - 'other_renewables_data' DataFrame with hourly historical generation
    
    Side Effects:
        Adds parameters to model.other_renewables block:
        - model.other_renewables.alpha (Param): Capacity scaling factor
        - model.other_renewables.ts_parameter[h] (Param): Hourly generation pattern (MW)
    
    Notes:
        Actual generation in hour h is: alpha × ts_parameter[h]
    """
    add_alpha_and_ts_parameters(model.other_renewables, model.h, data, "AlphaOtheRe", "other_renewables_data", "OtherRenewables")
    