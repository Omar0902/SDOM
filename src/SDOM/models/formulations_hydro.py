from pyomo.environ import Param
from .models_utils import add_alpha_and_ts_parameters

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_large_hydro_parameters(model, data):

    add_alpha_and_ts_parameters(model.hydro, model.h, data, "AlphaLargHy", "large_hydro_data", "LargeHydro")
