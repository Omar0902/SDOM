from pyomo.core import Var, Constraint
from pyomo.environ import *

def add_gascc_variables(model):
    model.CapCC = Var(domain=NonNegativeReals, initialize=0)
    model.GenCC = Var(model.h, domain=NonNegativeReals,initialize=0)  # Generation from GCC units

    # Compute and set the upper bound for CapCC
    CapCC_upper_bound_value = max(
        value(model.Load[h]) - value(model.AlphaNuclear) *
        value(model.Nuclear[h])
        - value(model.AlphaLargHy) * value(model.LargeHydro[h])
        - value(model.AlphaOtheRe) * value(model.OtherRenewables[h])
        for h in model.h
    )

    model.CapCC.setub(CapCC_upper_bound_value)
   # model.CapCC.setub(0)
    #print(CapCC_upper_bound_value)