
from pyomo.environ import *

# Fixed Charge Rates (FCR) for VRE and Gas CC
def fcr_rule( model, lifetime = 30 ):
    return ( model.r * (1 + model.r) ** lifetime ) / ( (1 + model.r) ** lifetime - 1 )

# Capital recovery factor for storage
def crf_rule( model, j):
    lifetime = model.StorageData['Lifetime', j]
    return ( model.r * (1 + model.r) ** lifetime ) / ( (1 + model.r) ** lifetime - 1 )

def initialize_params(model, data):
    """
    Initialize model parameters from the provided data dictionary.
    
    Args:
        model: The optimization model instance to initialize.
        data: A dictionary containing model parameters and data.
    """

    # Initialize storage properties
    storage_properties = ['P_Capex', 'E_Capex', 'Eff', 'Min_Duration',
                          'Max_Duration', 'Max_P', 'FOM', 'VOM', 'Lifetime', 'CostRatio']
    model.sp = Set( initialize = storage_properties )


    # Scalar parameters
    model.r = Param( initialize = float(data["scalars"].loc["r"].Value) )  # Discount rate
    model.GasPrice = Param( initialize = float(data["scalars"].loc["GasPrice"].Value))  # Gas prices (US$/MMBtu)
    # Heat rate for gas combined cycle (MMBtu/MWh)
    model.HR = Param( initialize = float(data["scalars"].loc["HR"].Value) )
    # Capex for gas combined cycle units (US$/kW)
    model.CapexGasCC = Param( initialize =float(data["scalars"].loc["CapexGasCC"].Value) )
    # Fixed O&M for gas combined cycle (US$/kW-year)
    model.FOM_GasCC = Param( initialize = float(data["scalars"].loc["FOM_GasCC"].Value) )
    # Variable O&M for gas combined cycle (US$/MWh)
    model.VOM_GasCC = Param( initialize = float(data["scalars"].loc["VOM_GasCC"].Value) )
    model.EUE_max = Param( initialize = float(data["scalars"].loc["EUE_max"].Value), mutable=True )  # Maximum EUE (in MWh) - Maximum unserved Energy

    # GenMix_Target, mutable to change across multiple runs
    model.GenMix_Target = Param( initialize = float(data["scalars"].loc["GenMix_Target"].Value), mutable=True)


    model.FCR_VRE = Param( initialize = fcr_rule( model, float(data["scalars"].loc["LifeTimeVRE"].Value) ) )
    model.FCR_GasCC = Param( initialize = fcr_rule( model, float(data["scalars"].loc["LifeTimeGasCC"].Value) ) )

    # Activation factors for nuclear, hydro, and other renewables
    model.AlphaNuclear = Param( initialize = float(data["scalars"].loc["AlphaNuclear"].Value), mutable=True )
    # Control for large hydro generation
    model.AlphaLargHy = Param( initialize = float(data["scalars"].loc["AlphaLargHy"].Value) )
    # Control for other renewable generation
    model.AlphaOtheRe = Param( initialize = float(data["scalars"].loc["AlphaOtheRe"].Value) )

    # Battery life and cycling
    model.MaxCycles = Param( initialize = float(data["scalars"].loc["MaxCycles"].Value) )

    # Load data initialization
    load_data = data["load_data"].set_index('*Hour')['Load'].to_dict()
    filtered_load_data = {h: load_data[h] for h in model.h if h in load_data}
    model.Load = Param(model.h, initialize=filtered_load_data)

    # Nuclear data initialization
    nuclear_data = data["nuclear_data"].set_index('*Hour')['Nuclear'].to_dict()
    filtered_nuclear_data = {h: nuclear_data[h] for h in model.h if h in nuclear_data}
    model.Nuclear = Param(model.h, initialize=filtered_nuclear_data)

    # Large hydro data initialization
    large_hydro_data = data["large_hydro_data"].set_index('*Hour')['LargeHydro'].to_dict()
    filtered_large_hydro_data = {h: large_hydro_data[h] for h in model.h if h in large_hydro_data}
    model.LargeHydro = Param(model.h, initialize=filtered_large_hydro_data)

    # Other renewables data initialization
    other_renewables_data = data["other_renewables_data"].set_index('*Hour')['OtherRenewables'].to_dict()
    filtered_other_renewables_data = {h: other_renewables_data[h] for h in model.h if h in other_renewables_data}
    model.OtherRenewables = Param(model.h, initialize=filtered_other_renewables_data)

    # Solar capacity factor initialization
    cf_solar_melted = data["cf_solar"].melt(id_vars='Hour', var_name='plant', value_name='CF')
    cf_solar_filtered = cf_solar_melted[(cf_solar_melted['plant'].isin(model.k)) & (cf_solar_melted['Hour'].isin(model.h))]
    cf_solar_dict = cf_solar_filtered.set_index(['Hour', 'plant'])['CF'].to_dict()
    model.CFSolar = Param(model.h, model.k, initialize=cf_solar_dict)

    # Wind capacity factor initialization
    cf_wind_melted = data["cf_wind"].melt(id_vars='Hour', var_name='plant', value_name='CF')
    cf_wind_filtered = cf_wind_melted[(cf_wind_melted['plant'].isin(model.w)) & (cf_wind_melted['Hour'].isin(model.h))]
    cf_wind_dict = cf_wind_filtered.set_index(['Hour', 'plant'])['CF'].to_dict()
    model.CFWind = Param(model.h, model.w, initialize=cf_wind_dict)

    # Storage data initialization
    storage_dict = data["storage_data"].stack().to_dict()
    storage_tuple_dict = {(prop, tech): storage_dict[(prop, tech)] for prop in storage_properties for tech in model.j}
    model.StorageData = Param(model.sp, model.j, initialize=storage_tuple_dict)

    model.CRF = Param( model.j, initialize = crf_rule ) #Capital Recovery Factor
    #model.CRF.display()