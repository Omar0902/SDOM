from pyomo.environ import *

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_load_parameters(model, data):
    # Load data initialization
    load_data = data["load_data"].set_index('*Hour')['Load'].to_dict()
    filtered_load_data = {h: load_data[h] for h in model.h if h in load_data}
    model.Load = Param( model.h, initialize = filtered_load_data )
