from pyomo.environ import Param
from .models_utils import add_alpha_and_ts_parameters
####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_load_parameters(model, data: dict):

    add_alpha_and_ts_parameters(model.demand, model.h, data, "", "load_data", "Load")
