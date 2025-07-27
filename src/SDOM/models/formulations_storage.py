from pyomo.core import Var, Constraint
from pyomo.environ import *

def add_storage_variables(model):
    # Charging power for storage technology j in hour h
    model.PC = Var(model.h, model.j, domain=NonNegativeReals, initialize=0)
    # Discharging power for storage technology j in hour h
    model.PD = Var(model.h, model.j, domain=NonNegativeReals, initialize=0)
    # State-of-charge for storage technology j in hour h
    model.SOC = Var(model.h, model.j, domain=NonNegativeReals, initialize=0)
    # Charging capacity for storage technology j
    model.Pcha = Var(model.j, domain=NonNegativeReals, initialize=0)
    # Discharging capacity for storage technology j
    model.Pdis = Var(model.j, domain=NonNegativeReals, initialize=0)
    # Energy capacity for storage technology j
    model.Ecap = Var(model.j, domain=NonNegativeReals, initialize=0)

    # Capacity selection variables with continuous bounds between 0 and 1
    model.Ypv = Var(model.k, domain=NonNegativeReals, bounds=(0, 1), initialize=1)
    model.Ywind = Var(model.w, domain=NonNegativeReals, bounds=(0, 1), initialize=1)

    model.Ystorage = Var(model.j, model.h, domain=Binary, initialize=0)