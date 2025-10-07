import logging

from pyomo.environ import Param, Set, RangeSet

from .models.formulations_vre import add_vre_parameters
from .models.formulations_thermal import add_thermal_parameters, initialize_thermal_sets
from .models.formulations_nuclear import add_nuclear_parameters
from .models.formulations_hydro import add_large_hydro_parameters, add_large_hydro_bound_parameters
from .models.formulations_other_renewables import add_other_renewables_parameters
from .models.formulations_load import add_load_parameters
from .models.formulations_storage import add_storage_parameters, initialize_storage_sets
from .models.formulations_resiliency import add_resiliency_parameters


from .constants import VALID_HYDRO_FORMULATIONS_TO_BUDGET_MAP, MONTHLY_BUDGET_HOURS_AGGREGATION, DAILY_BUDGET_HOURS_AGGREGATION
from .io_manager import get_formulation

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


def check_n_hours(n_hours: int, interval: int):
    if n_hours % interval == 0:
        return n_hours
    else:
        n = (n_hours // interval) + 1
        logging.warning(f"the selected number of hours ({n_hours}) is not multiple of the aggregation interval ({interval}) for the selected formulation. The number of hours will be approximated to {n*interval}.")
    return n * interval

def create_budget_set( model, 
                      block, 
                      n_hours_checked:int, 
                      budget_hours_aggregation:int ):
    breakpoints  = list(range(budget_hours_aggregation, n_hours_checked+1, budget_hours_aggregation))
    indices = list(range(1, len(breakpoints) + 1))
    
    block.budget_set = Set( within=model.h, initialize = indices  )
    return

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

    initialize_storage_sets(model.storage, data)
    logging.info(f"Storage technologies being considered: {list(model.storage.j)}")
    logging.info(f"Storage technologies with coupled charge/discharge power: {list(model.storage.b)}")

    initialize_thermal_sets(model.thermal, data)
   
    hydro_formulation = get_formulation(data, component = 'hydro')
    if "Budget" in hydro_formulation:
        n_hours_checked= check_n_hours(n_hours, VALID_HYDRO_FORMULATIONS_TO_BUDGET_MAP[hydro_formulation])
        model.h = RangeSet(1, n_hours_checked)
        model.storage.n_steps_modeled = Param( initialize = n_hours_checked )
        create_budget_set( model, model.hydro, n_hours_checked, VALID_HYDRO_FORMULATIONS_TO_BUDGET_MAP[hydro_formulation] )
        
    else:
        model.h = RangeSet(1, n_hours)
        model.storage.n_steps_modeled = Param( initialize = n_hours )

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
    if not (data["formulations"].loc[ data["formulations"]["Component"].str.lower() == 'hydro' ]["Formulation"].iloc[0]  == "RunOfRiverFormulation"):
        logging.debug("--Initializing large hydro budget parameters...")
        add_large_hydro_bound_parameters(model, data)
    
   

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