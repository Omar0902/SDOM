VRE_PROPERTIES_NAMES = ['trans_cap_cost', 'CAPEX_M', 'FOM_M']
STORAGE_PROPERTIES_NAMES = ['P_Capex', 'E_Capex', 'Eff', 'Min_Duration',
                          'Max_Duration', 'Max_P', 'FOM', 'VOM', 'Lifetime', 'CostRatio']
STORAGE_SET_J_TECHS = ['Li-Ion', 'CAES', 'PHS', 'H2']
STORAGE_SET_B_TECHS = ['Li-Ion', 'PHS']

#RESILIENCY CONSTANTS HARD-CODED
# PCLS - Percentage of Critical Load Served - Constraint : Resilience
CRITICAL_LOAD_PERCENTAGE = 1  # 10% of the total load
PCLS_TARGET = 0.9  # 90% of the total load