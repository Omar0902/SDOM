from pyomo.core import Var, Constraint
from pyomo.environ import *

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_large_hydro_parameters(model, data):
    # Control for large hydro generation
    model.AlphaLargHy = Param( initialize = float(data["scalars"].loc["AlphaLargHy"].Value) )
    # Large hydro data initialization
    large_hydro_data = data["large_hydro_data"].set_index('*Hour')['LargeHydro'].to_dict()
    filtered_large_hydro_data = {h: large_hydro_data[h] for h in model.h if h in large_hydro_data}
    model.LargeHydro = Param( model.h, initialize = filtered_large_hydro_data)