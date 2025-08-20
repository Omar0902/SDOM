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
    # Control for large hydro generation
    block.alpha = Param( initialize = float(data["scalars"].loc[key_scalars].Value) )

    # Large hydro data initialization
    large_hydro_data          = data[key_ts].set_index('*Hour')[key_col].to_dict()
    filtered_large_hydro_data = {h: large_hydro_data[h] for h in hourly_set if h in large_hydro_data}

    block.ts_parameter = Param( hourly_set, initialize = filtered_large_hydro_data)