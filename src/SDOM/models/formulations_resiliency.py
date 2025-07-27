from pyomo.core import Var, Constraint
from pyomo.environ import *

####################################################################################|
# ------------------------------------ Variables -----------------------------------|
####################################################################################|

def add_resiliency_variables( model ):
    # Define variables related to system resiliency
    model.LoadShed = Var( model.h, domain=NonNegativeReals, initialize = 0 )

####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|
def pcls_constraint_rule( model ):
    # PCLS - Percentage of Critical Load Served - Constraint : Resilience
    critical_load_percentage = 1  # 10% of the total load
    PCLS_target = 0.9  # 90% of the total load
    return sum( model.Load[h] - model.LoadShed[h] for h in model.h ) \
        >= PCLS_target * sum( model.Load[h] for h in model.h ) * critical_load_percentage

# EUE - Expected Unserved Energy - Constraint : Resilience
def max_eue_constraint_rule( model ):
    return sum( model.LoadShed[h] for h in model.h ) <= model.EUE_max