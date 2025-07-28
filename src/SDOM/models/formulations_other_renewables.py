from pyomo.environ import *

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_other_renewables_parameters(model, data):
    # Control for other renewable generation
    model.AlphaOtheRe = Param( initialize = float(data["scalars"].loc["AlphaOtheRe"].Value) )

    # Other renewables data initialization
    other_renewables_data = data["other_renewables_data"].set_index('*Hour')['OtherRenewables'].to_dict()
    filtered_other_renewables_data = {h: other_renewables_data[h] for h in model.h if h in other_renewables_data}
    model.OtherRenewables = Param( model.h, initialize = filtered_other_renewables_data )
