from pyomo.environ import Param
from .models_utils import add_alpha_and_ts_parameters

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_nuclear_parameters(model, data):
    add_alpha_and_ts_parameters(model.nuclear, model.h, data, "AlphaNuclear", "nuclear_data", "Nuclear")
    