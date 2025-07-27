
from pyomo.environ import *
from .constants import VRE_PROPERTIES_NAMES, STORAGE_PROPERTIES_NAMES, STORAGE_SET_J_TECHS, STORAGE_SET_B_TECHS

# Fixed Charge Rates (FCR) for VRE and Gas CC
def fcr_rule( model, lifetime = 30 ):
    return ( model.r * (1 + model.r) ** lifetime ) / ( (1 + model.r) ** lifetime - 1 )

# Capital recovery factor for storage
def crf_rule( model, j):
    lifetime = model.StorageData['Lifetime', j]
    return ( model.r * (1 + model.r) ** lifetime ) / ( (1 + model.r) ** lifetime - 1 )

def initialize_sets(model, data):
    """
    Initialize model sets from the provided data dictionary.
    
    Args:
        model: The optimization model instance to initialize.
        data: A dictionary containing model parameters and data.
    """

   # Solar plant ID alignment
    solar_plants_cf = data['cf_solar'].columns[1:].astype(str).tolist()
    solar_plants_cap = data['cap_solar']['sc_gid'].astype(str).tolist()
    common_solar_plants = list(set(solar_plants_cf) & set(solar_plants_cap))

    # Filter solar data and initialize model set
    complete_solar_data = data["cap_solar"][data["cap_solar"]['sc_gid'].astype(str).isin(common_solar_plants)]
    complete_solar_data = complete_solar_data.dropna(subset=['CAPEX_M', 'trans_cap_cost', 'FOM_M', 'capacity'])
    common_solar_plants_filtered = complete_solar_data['sc_gid'].astype(str).tolist()
    model.k = Set( initialize = common_solar_plants_filtered )

    # Load the solar capacities
    cap_solar_dict = complete_solar_data.set_index('sc_gid')['capacity'].to_dict()

    # Filter the dictionary to ensure only valid keys are included
    default_capacity_value = 0.0
    filtered_cap_solar_dict = {k: cap_solar_dict.get(k, default_capacity_value) for k in model.k}
    
    # Wind plant ID alignment
    wind_plants_cf = data['cf_wind'].columns[1:].astype(str).tolist()
    wind_plants_cap = data['cap_wind']['sc_gid'].astype(str).tolist()
    common_wind_plants = list( set( wind_plants_cf ) & set( wind_plants_cap ) )

    # Filter wind data and initialize model set
    complete_wind_data = data["cap_wind"][data["cap_wind"]['sc_gid'].astype(str).isin(common_wind_plants)]
    complete_wind_data = complete_wind_data.dropna(subset=['CAPEX_M', 'trans_cap_cost', 'FOM_M', 'capacity'])
    common_wind_plants_filtered = complete_wind_data['sc_gid'].astype(str).tolist()
    model.w = Set(initialize=common_wind_plants_filtered)

    # Load the wind capacities
    cap_wind_dict = complete_wind_data.set_index('sc_gid')['capacity'].to_dict()

    # Filter the dictionary to ensure only valid keys are included
    filtered_cap_wind_dict = {w: cap_wind_dict.get(w, default_capacity_value) for w in model.w}

    #add to data dict new data pre-procesing dicts
    data['filtered_cap_solar_dict'] = filtered_cap_solar_dict
    data['filtered_cap_wind_dict'] = filtered_cap_wind_dict
    data['complete_solar_data'] = complete_solar_data
    data['complete_wind_data'] = complete_wind_data

    # Define sets
    model.h = RangeSet(1, 24)
    model.j = Set( initialize = STORAGE_SET_J_TECHS )
    model.b = Set( initialize = STORAGE_SET_B_TECHS )

    # Initialize storage properties
    model.sp = Set( initialize = STORAGE_PROPERTIES_NAMES )



def initialize_params(model, data):
    """
    Initialize model parameters from the provided data dictionary.
    
    Args:
        model: The optimization model instance to initialize.
        data: A dictionary containing model parameters and data.
        filtered_cap_solar_dict
    """
    filtered_cap_solar_dict = data['filtered_cap_solar_dict']
    filtered_cap_wind_dict = data['filtered_cap_wind_dict']
    complete_solar_data = data['complete_solar_data']
    complete_wind_data = data['complete_wind_data']

    # Initialize solar and wind parameters, with default values for missing data
    for property_name in VRE_PROPERTIES_NAMES:#['trans_cap_cost', 'CAPEX_M', 'FOM_M']:
        property_dict_solar = complete_solar_data.set_index('sc_gid')[property_name].to_dict()
        property_dict_wind = complete_wind_data.set_index('sc_gid')[property_name].to_dict()
        default_value = 0.0
        filtered_property_dict_solar = {k: property_dict_solar.get(k, default_value) for k in model.k}
        filtered_property_dict_wind = {w: property_dict_wind.get(w, default_value) for w in model.w}
        model.add_component(f"CapSolar_{property_name}", Param(model.k, initialize=filtered_property_dict_solar))
        model.add_component(f"CapWind_{property_name}", Param(model.w, initialize=filtered_property_dict_wind))

    model.CapSolar_capacity = Param( model.k, initialize = filtered_cap_solar_dict )  
    model.CapWind_capacity = Param(model.w, initialize=filtered_cap_wind_dict)


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
    storage_tuple_dict = {(prop, tech): storage_dict[(prop, tech)] for prop in STORAGE_PROPERTIES_NAMES for tech in model.j}
    model.StorageData = Param(model.sp, model.j, initialize=storage_tuple_dict)

    model.CRF = Param( model.j, initialize = crf_rule ) #Capital Recovery Factor
    #model.CRF.display()