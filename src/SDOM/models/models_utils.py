from pyomo.environ import Param

# Fixed Charge Rates (FCR) for VRE and Gas CC
def fcr_rule( model, lifetime = 30 ):
    return ( model.r * (1 + model.r) ** lifetime ) / ( (1 + model.r) ** lifetime - 1 )

def fcr_rule_thermal( model, bu ):
    lifetime = model.ThermalData['LifeTime', bu]
    return ( model.r * (1 + model.r) ** lifetime ) / ( (1 + model.r) ** lifetime - 1 )

# Capital recovery factor for storage
def crf_rule( model, j ):
    lifetime = model.StorageData['Lifetime', j]
    return ( model.r * (1 + model.r) ** lifetime ) / ( (1 + model.r) ** lifetime - 1 )


####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_alpha_and_ts_parameters( block, 
                                hourly_set, 
                                data, 
                                key_scalars: str, 
                                key_ts: str,
                                key_col: str):
    # Control parameter to activate certain device.
    if key_scalars != "":
        # Initialize alpha parameter from scalars
        block.alpha = Param( initialize = float(data["scalars"].loc[key_scalars].Value) )

    # Time-series parameter data initialization
    selected_data          = data[key_ts].set_index('*Hour')[key_col].to_dict()
    filtered_selected_data = {h: selected_data[h] for h in hourly_set if h in selected_data}

    block.ts_parameter = Param( hourly_set, initialize = filtered_selected_data)