import pandas as pd

REL_PATH_DATA_RUN_OF_RIVER_TEST = 'Data/no_exchange_run_of_river'
REL_PATH_DATA_HYDRO_BUDGET_TEST = 'Data/exchange_hydro_budget_multiple_balancing'

DICT_EXPECTED_DATA_KEYS_TO_TYPE = {
    "solar_plants": list,
    "wind_plants": list,
    "load_data": pd.DataFrame,
    "nuclear_data": pd.DataFrame,
    "large_hydro_data": pd.DataFrame,
    "large_hydro_max": pd.DataFrame,
    "large_hydro_min": pd.DataFrame,
    "other_renewables_data": pd.DataFrame,
    "cf_solar": pd.DataFrame,
    "cf_wind": pd.DataFrame,
    "cap_solar": pd.DataFrame,
    "cap_wind": pd.DataFrame,
    "storage_data": pd.DataFrame,
    "STORAGE_SET_J_TECHS": list,
    "STORAGE_SET_B_TECHS": list,
    "thermal_data": pd.DataFrame,
    "scalars": pd.DataFrame}

   