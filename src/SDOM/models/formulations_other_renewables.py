from pyomo.environ import Param
from .models_utils import add_alpha_and_ts_parameters

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_other_renewables_parameters(model, data):

    add_alpha_and_ts_parameters(model.other_renewables, model.h, data, "AlphaOtheRe", "other_renewables_data", "OtherRenewables")
    