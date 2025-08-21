import logging
from pyomo.environ import Param, Set, RangeSet
from .constants import STORAGE_PROPERTIES_NAMES, THERMAL_PROPERTIES_NAMES
from .models.formulations_vre import add_vre_parameters
from .models.formulations_thermal import add_thermal_parameters, initialize_thermal_sets
from .models.formulations_nuclear import add_nuclear_parameters
from .models.formulations_hydro import add_large_hydro_parameters
from .models.formulations_other_renewables import add_other_renewables_parameters
from .models.formulations_load import add_load_parameters
from .models.formulations_storage import add_storage_parameters, initialize_storage_sets
from .models.formulations_resiliency import add_resiliency_parameters


def initialize_vre_sets(data, block, vre_type: str):
     # Solar plant ID alignment
    vre_plants_cf = data[f'cf_{vre_type}'].columns[1:].astype(str).tolist()
    vre_plants_cap = data[f'cap_{vre_type}']['sc_gid'].astype(str).tolist()
    common_vre_plants = list(set(vre_plants_cf) & set(vre_plants_cap))

    # Filter solar data and initialize model set
    complete_vre_data = data[f"cap_{vre_type}"][data[f"cap_{vre_type}"]['sc_gid'].astype(str).isin(common_vre_plants)]
    complete_vre_data = complete_vre_data.dropna(subset=['CAPEX_M', 'trans_cap_cost', 'FOM_M', 'capacity'])
    common_vre_plants_filtered = complete_vre_data['sc_gid'].astype(str).tolist()
    
    block.plants_set = Set( initialize = common_vre_plants_filtered )

    # Load the solar capacities
    cap_vre_dict = complete_vre_data.set_index('sc_gid')['capacity'].to_dict()

    # Filter the dictionary to ensure only valid keys are included
    default_capacity_value = 0.0
    filtered_cap_vre_dict = {k: cap_vre_dict.get(k, default_capacity_value) for k in block.plants_set}

    data[f'filtered_cap_{vre_type}_dict'] = filtered_cap_vre_dict
    data[f'complete_{vre_type}_data'] = complete_vre_data

    
def initialize_sets( model, data, n_hours = 8760 ):
    """
    Initialize model sets from the provided data dictionary.
    
    Args:
        model: The optimization model instance to initialize.
        data: A dictionary containing model parameters and data.
    """
    initialize_vre_sets(data, model.pv, vre_type='solar')
    initialize_vre_sets(data, model.wind, vre_type='wind')


    # Define sets
    model.h = RangeSet(1, n_hours)

    initialize_storage_sets(model.storage, data)
    logging.info(f"Storage technologies being considered: {list(model.storage.j)}")
    logging.info(f"Storage technologies with coupled charge/discharge power: {list(model.storage.b)}")

    initialize_thermal_sets(model.thermal, data)


def initialize_params(model, data):
    """
    Initialize model parameters from the provided data dictionary.
    
    Args:
        model: The optimization model instance to initialize.
        data: A dictionary containing model parameters and data.
        filtered_cap_solar_dict
    """
    model.r = Param( initialize = float(data["scalars"].loc["r"].Value) )  # Discount rate

    logging.debug("--Initializing large hydro parameters...")
    add_large_hydro_parameters(model, data)

    logging.debug("--Initializing load parameters...")
    add_load_parameters(model, data)

    logging.debug("--Initializing nuclear parameters...")
    add_nuclear_parameters(model, data)

    logging.debug("--Initializing other renewables parameters...")
    add_other_renewables_parameters(model, data)

    logging.debug("--Initializing storage parameters...")
    add_storage_parameters(model, data)

    logging.debug("--Initializing thermal parameters...")
    add_thermal_parameters(model,data)

    logging.debug("--Initializing VRE parameters...")
    add_vre_parameters(model, data)

    # GenMix_Target, mutable to change across multiple runs
    model.GenMix_Target = Param( initialize = float(data["scalars"].loc["GenMix_Target"].Value), mutable=True)
    
    logging.debug("--Initializing resiliency parameters...")
    add_resiliency_parameters(model, data)
    #model.CRF.display()