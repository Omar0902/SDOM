from pyomo.environ import Param

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_nuclear_parameters(model, data):
    # Activation factors for nuclear, hydro, and other renewables
    model.AlphaNuclear = Param( initialize = float(data["scalars"].loc["AlphaNuclear"].Value), mutable=True )
    # Nuclear data initialization
    nuclear_data = data["nuclear_data"].set_index('*Hour')['Nuclear'].to_dict()
    filtered_nuclear_data = {h: nuclear_data[h] for h in model.h if h in nuclear_data}
    model.Nuclear = Param( model.h, initialize = filtered_nuclear_data )
