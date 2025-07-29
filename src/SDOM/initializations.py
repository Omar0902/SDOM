
from pyomo.environ import *
from .constants import STORAGE_PROPERTIES_NAMES, STORAGE_SET_J_TECHS, STORAGE_SET_B_TECHS
from .models.formulations_vre import add_vre_parameters
from .models.formulations_thermal import add_gascc_parameters
from .models.formulations_nuclear import add_nuclear_parameters
from .models.formulations_hydro import add_large_hydro_parameters
from .models.formulations_other_renewables import add_other_renewables_parameters
from .models.formulations_load import add_load_parameters
from .models.formulations_storage import add_storage_parameters
from .models.formulations_resiliency import add_resiliency_parameters
from .models.models_utils import crf_rule

def initialize_sets( model, data, n_hours = 8760 ):
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
    model.h = RangeSet(1, n_hours)
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
    model.r = Param( initialize = float(data["scalars"].loc["r"].Value) )  # Discount rate
    
    add_vre_parameters(model, data)

    add_gascc_parameters(model,data)

    add_load_parameters(model, data)

    add_nuclear_parameters(model, data)

    add_large_hydro_parameters(model, data)

    add_other_renewables_parameters(model, data)

    add_storage_parameters(model, data)

    # GenMix_Target, mutable to change across multiple runs
    model.GenMix_Target = Param( initialize = float(data["scalars"].loc["GenMix_Target"].Value), mutable=True)
    model.CRF = Param( model.j, initialize = crf_rule ) #Capital Recovery Factor
    
    add_resiliency_parameters(model, data)
    #model.CRF.display()