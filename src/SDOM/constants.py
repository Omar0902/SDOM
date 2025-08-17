# INCLUDE HERE ALL THE CONSTATS AND USE UPPER CASE NAMES

MW_TO_KW = 1000.0



INPUT_CSV_NAMES = {
    'solar_plants': 'Set_k_SolarPV.csv', #TODO this set should be optional since are col names CFSolar_2050.csv
    'wind_plants': 'Set_w_Wind.csv', #TODO this set should be optional since are col names CFWind_2050.csv
    'load_data': 'Load_hourly_2050.csv',
    'nuclear_data': 'Nucl_hourly_2019.csv',
    'large_hydro_data': 'lahy_hourly_2019.csv',
    'other_renewables_data': 'otre_hourly_2019.csv',
    'cf_solar': 'CFSolar_2050.csv',
    'cf_wind': 'CFWind_2050.csv',
    'cap_solar': 'CapSolar_2050.csv',
    'cap_wind': 'CapWind_2050.csv',
    'storage_data': 'StorageData_2050.csv',
    'scalars': 'Scalars.csv',
}

VRE_PROPERTIES_NAMES = ['trans_cap_cost', 'CAPEX_M', 'FOM_M']
STORAGE_PROPERTIES_NAMES = ['P_Capex', 'E_Capex', 'Eff', 'Min_Duration',
                          'Max_Duration', 'Max_P', 'FOM', 'VOM', 'Lifetime', 'CostRatio']

#TODO this set is the col names of the StorageData_2050.csv file
STORAGE_SET_J_TECHS = ['Li-Ion', 'CAES', 'PHS', 'H2']
STORAGE_SET_B_TECHS = ['Li-Ion', 'PHS'] #TODO INCLUDE DECOUPLED STORAGE FLAG IN THE CSV FILE

#RESILIENCY CONSTANTS HARD-CODED
# PCLS - Percentage of Critical Load Served - Constraint : Resilience
CRITICAL_LOAD_PERCENTAGE = 1  # 10% of the total load
PCLS_TARGET = 0.9  # 90% of the total load