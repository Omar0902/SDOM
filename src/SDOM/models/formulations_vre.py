from pyomo.core import Var, Constraint
from pyomo.environ import *

def add_vre_variables(model):
    """
    Add variables related to variable renewable energy (VRE) to the model.
    
    Parameters:
    model: The optimization model to which VRE variables will be added.
    
    Returns:
    None
    """
    model.GenPV = Var(model.h, domain=NonNegativeReals,initialize=0)  # Generated solar PV power
    model.CurtPV = Var(model.h, domain=NonNegativeReals, initialize=0) # Curtailment for solar PV power
    model.GenWind = Var(model.h, domain=NonNegativeReals,initialize=0)  # Generated wind power
    model.CurtWind = Var(model.h, domain=NonNegativeReals,initialize=0)  # Curtailment for wind power

