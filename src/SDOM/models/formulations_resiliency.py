from pyomo.core import Var, Constraint
from pyomo.environ import *

def add_resiliency_variables(model):
    # Define variables related to system resiliency
    model.LoadShed = Var(model.h, domain=NonNegativeReals, initialize=0)