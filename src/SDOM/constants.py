# INCLUDE HERE ALL THE CONSTATS AND USE UPPER CASE NAMES

MW_TO_KW = 1000.0

#---------------- -------------------- --------------|
#---------------- LOGGING COLOR CONFIG --------------|
#---------------- -------------------- --------------|
LOG_COLORS = {
        'INFO': '\033[92m',    # Green
        'WARNING': '\033[93m', # Yellow
        'ERROR': '\033[91m',   # Red
        'CRITICAL': '\033[91m',# Red
        'DEBUG': '\033[94m',   # Blue (optional)
    }

INPUT_CSV_NAMES = {
    # 'solar_plants': 'Set_k_SolarPV.csv', #Now this set is optional since are col names CFSolar_2050.csv
    # 'wind_plants': 'Set_w_Wind.csv', #Now this set is optional since are col names CFWind_2050.csv
    'formulations': 'formulations.csv',
    'load_data': 'Load_hourly.csv',#'Load_hourly_2050.csv',
    'nuclear_data': 'Nucl_hourly.csv',#'Nucl_hourly_2019.csv',
    'large_hydro_data': 'lahy_hourly.csv', #'lahy_hourly_2019.csv',
    'large_hydro_max': 'lahy_max_hourly.csv', #'lahy_hourly_2019.csv',
    'large_hydro_min': 'lahy_min_hourly.csv', #'lahy_hourly_2019.csv',
    'other_renewables_data': 'otre_hourly.csv', #'otre_hourly_2019.csv',
    'cf_solar': 'CFSolar.csv', #'CFSolar_2050.csv',
    'cf_wind': 'CFWind.csv', #'CFWind_2050.csv',
    'cap_solar': 'CapSolar.csv', #'CapSolar_2050.csv',
    'cap_wind': 'CapWind.csv', #'CapWind_2050.csv',
    'thermal_data': 'Data_BalancingUnits.csv', #'Data_BalancingUnits_2030(in).csv',
    'storage_data': 'StorageData.csv', #'StorageData_2050.csv',
    #"imports": "Imports.csv", #'Imports_2019.csv',
    #"exports": "Exports.csv", #'Exports_2019.csv',
    'scalars': 'scalars.csv', #'scalars.csv',
}

VRE_PROPERTIES_NAMES = ['trans_cap_cost', 'CAPEX_M', 'FOM_M']
STORAGE_PROPERTIES_NAMES = ['P_Capex', 'E_Capex', 'Eff', 'Min_Duration',
                          'Max_Duration', 'Max_P', 'Coupled', 'FOM', 'VOM', 'Lifetime', 'CostRatio']

THERMAL_PROPERTIES_NAMES = ['MinCapacity', 'MaxCapacity', 'Lifetime', 'Capex', 'HeatRate', 'FuelCost', 'VOM', 'FOM']

#TODO this set is the col names of the StorageData_2050.csv file
#STORAGE_SET_J_TECHS = ['Li-Ion', 'CAES', 'PHS', 'H2'] - THIS WAS REPLACED BY "data["STORAGE_SET_J_TECHS"]" which reads the cols of storage_data
#STORAGE_SET_B_TECHS = ['Li-Ion', 'PHS'] #THIS WAS REPLACED BY "data["STORAGE_SET_B_TECHS"]"

MONTHLY_BUDGET_HOURS_AGGREGATION = 730
DAILY_BUDGET_HOURS_AGGREGATION = 24
RUN_OF_RIVER_AGGREGATION = 1
VALID_HYDRO_FORMULATIONS_TO_BUDGET_MAP = {
    "MonthlyBudgetFormulation": MONTHLY_BUDGET_HOURS_AGGREGATION,
    "DailyBudgetFormulation": DAILY_BUDGET_HOURS_AGGREGATION,
    "RunOfRiverFormulation": RUN_OF_RIVER_AGGREGATION
}

#RESILIENCY CONSTANTS HARD-CODED
# PCLS - Percentage of Critical Load Served - Constraint : Resilience
CRITICAL_LOAD_PERCENTAGE = 1  # 10% of the total load
PCLS_TARGET = 0.9  # 90% of the total load