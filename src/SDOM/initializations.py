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
from .models.formulations_imports_exports import add_imports_parameters, add_exports_parameters

from .constants import VALID_HYDRO_FORMULATIONS_TO_BUDGET_MAP
from .io_manager import get_formulation

def initialize_vre_sets(data, block, vre_type: str):
    """
    Initializes Variable Renewable Energy (VRE) plant sets for solar or wind resources.
    
    This function aligns capacity factor data with capacity and cost data, filters out
    plants with missing critical information, and creates Pyomo sets for the optimization
    model. It ensures data consistency between CF profiles and plant characteristics.
    
    Args:
        data (dict): Dictionary containing input data including capacity factors (cf_solar/cf_wind)
            and capacity/cost information (cap_solar/cap_wind).
        block: Pyomo Block object (e.g., model.pv or model.wind) where the sets will be added.
        vre_type (str): Type of VRE technology, either 'solar' or 'wind'.
    
    Side Effects:
        - Creates block.plants_set: Pyomo Set containing valid plant IDs.
        - Adds 'filtered_cap_{vre_type}_dict' and 'complete_{vre_type}_data' to data dictionary.
    
    Examples:
        >>> initialize_vre_sets(data, model.pv, vre_type='solar')
        >>> print(list(model.pv.plants_set))  # ['plant001', 'plant002', ...]
    """
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
    """
    Validates and adjusts the simulation horizon to be compatible with budget aggregation intervals.
    
    For budget formulations (daily or monthly), the number of hours must be a multiple of
    the aggregation interval. This function checks the compatibility and rounds up if necessary,
    logging a warning when adjustments are made.
    
    Args:
        n_hours (int): Requested number of hours to simulate (e.g., 8760 for a full year).
        interval (int): Budget aggregation interval in hours (e.g., 24 for daily, 730 for monthly).
    
    Returns:
        int: Adjusted number of hours that is a multiple of the interval.
    
    Examples:
        >>> check_n_hours(8760, 24)  # 8760 is divisible by 24
        8760
        >>> check_n_hours(8700, 730)  # 8700 is not divisible by 730
        8760  # Logs warning and rounds up to 12*730
    """
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
    """
    Creates a Pyomo set for hydro budget constraints based on aggregation intervals.
    
    This function divides the simulation horizon into budget periods (e.g., daily or monthly)
    and creates indices for budget constraints. Each budget period represents a time window
    within which hydro generation must satisfy cumulative energy limits.
    
    Args:
        model: The Pyomo ConcreteModel instance (needed to reference model.h).
        block: Pyomo Block where the budget_set will be added (typically model.hydro).
        n_hours_checked (int): Total number of hours in the simulation (must be multiple
            of budget_hours_aggregation).
        budget_hours_aggregation (int): Hours per budget period (24 for daily, 730 for monthly).
    
    Side Effects:
        Creates block.budget_set: Pyomo Set with indices [1, 2, ..., num_periods] representing
        each budget period.
    
    Examples:
        >>> create_budget_set(model, model.hydro, 8760, 730)  # 12 monthly periods
        >>> print(list(model.hydro.budget_set))  # [1, 2, 3, ..., 12]
    """
    breakpoints  = list(range(budget_hours_aggregation, n_hours_checked+1, budget_hours_aggregation))
    indices = list(range(1, len(breakpoints) + 1))
    
    block.budget_set = Set( within=model.h, initialize = indices  )
    return

def initialize_sets( model, data, n_hours = 8760 ):
    """
    Initializes all model sets including time horizon, technology sets, and budget sets.
    
    This function orchestrates set initialization for all model components:
    - VRE plants (solar PV and wind)
    - Storage technologies
    - Thermal generation units
    - Time horizon (hourly set)
    - Hydro budget periods (if applicable)
    
    The time horizon is adjusted based on the selected hydro formulation to ensure
    compatibility with budget aggregation intervals.
    
    Args:
        model: The Pyomo ConcreteModel instance to initialize.
        data (dict): Dictionary containing all input data loaded from CSV files.
        n_hours (int, optional): Number of hours to simulate. Defaults to 8760 (full year).
    
    Side Effects:
        - Creates model.h: Pyomo RangeSet for hourly time steps
        - Creates sets in model.pv, model.wind, model.storage, model.thermal blocks
        - Creates model.hydro.budget_set if using budget formulation
        - Logs information about configured technologies
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
    Initializes all model parameters from the loaded input data.
    
    This function populates Pyomo parameters for all model components by calling
    component-specific parameter initialization functions. Parameters include:
    - Economic parameters (discount rate, generation mix targets)
    - Time-series data (load, capacity factors, hydro availability)
    - Technology characteristics (costs, efficiencies, capacities)
    - Formulation-specific parameters (budgets, bounds, prices)
    
    The function handles conditional parameter initialization based on selected
    formulations (e.g., hydro budget bounds only for budget formulations).
    
    Args:
        model: The Pyomo ConcreteModel instance with initialized sets.
        data (dict): Dictionary containing all input data including scalars, time series,
            and formulation specifications.
    
    Side Effects:
        - Adds Pyomo Param objects to model and all block objects
        - Logs debug information about parameter initialization progress
    
    Notes:
        This function should be called after initialize_sets() to ensure all required
        sets are defined before parameters that reference them.
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

    if get_formulation(data, component="Imports") != "NotModel":
        logging.debug("--Initializing Imports parameters...")
        add_imports_parameters(model, data)

    if get_formulation(data, component="Exports") != "NotModel":
        logging.debug("--Initializing Exports parameters...")
        add_exports_parameters(model, data)
        

    # GenMix_Target, mutable to change across multiple runs
    model.GenMix_Target = Param( initialize = float(data["scalars"].loc["GenMix_Target"].Value), mutable=True)
    
    logging.debug("--Initializing resiliency parameters...")
    add_resiliency_parameters(model, data)
    #model.CRF.display()