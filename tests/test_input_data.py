import os
import pandas as pd
from constants_test import REL_PATH_DATA_RUN_OF_RIVER_TEST, DICT_EXPECTED_DATA_KEYS_TO_TYPE

from sdom import load_data, initialize_model

def test_load_data_folder_exist():
    test_data_path = os.path.join(os.path.dirname(__file__), '..', REL_PATH_DATA_RUN_OF_RIVER_TEST)
    test_data_path = os.path.abspath(test_data_path)

    assert os.path.exists(test_data_path)
    


def test_load_data_keys_and_types():
    test_data_path = os.path.join(os.path.dirname(__file__), '..', REL_PATH_DATA_RUN_OF_RIVER_TEST)
    test_data_path = os.path.abspath(test_data_path)
    
    data = load_data( test_data_path )
    data_keys = data.keys()

    for key, expected_type in DICT_EXPECTED_DATA_KEYS_TO_TYPE.items():
        if key == "large_hydro_max" or key == "large_hydro_min":
                continue  # Skip these keys as they are not for run of River
        assert key in data_keys, f"Missing expected key: {key}"
        assert isinstance(data[key], expected_type), f"Key '{key}' has incorrect type. Expected {expected_type}, got {type(data[key])}"

    

def test_load_data_param_values():
    test_data_path = os.path.join(os.path.dirname(__file__), '..', REL_PATH_DATA_RUN_OF_RIVER_TEST)
    test_data_path = os.path.abspath(test_data_path)
    
    data = load_data( test_data_path )
    
    df = data["scalars"]
    # Check some specific values in the scalars DataFrame
    assert abs( df.loc["LifeTimeVRE"].Value - 30 ) <= 0.05
    assert abs( df.loc["GenMix_Target"].Value - 1 ) <= 0.05
    assert abs( df.loc["MaxCycles"].Value - 3250 ) <= 10
    assert abs( df.loc["r"].Value - 0.06 ) <= 0.0005

def test_load_data_thermal_values():
    test_data_path = os.path.join(os.path.dirname(__file__), '..', REL_PATH_DATA_RUN_OF_RIVER_TEST)
    test_data_path = os.path.abspath(test_data_path)

    data = load_data( test_data_path )

    df = data["thermal_data"]
    min_capacity_v = [0.0 , 0.0]
    max_capacity_v = [4897.0, 0.0]
    lifetime_v = [30.0, 30.0]
    Capex_v = [0, 0]
    heat_rate_v = [1, 1]
    fuel_cost_v = [129.2517007, 129.2517007]
    vom_v = [7.5, 7.5]
    for idx, row in df.iterrows():
        assert abs( row["MinCapacity"] - min_capacity_v[idx] ) <= 0.05
        assert abs( row["MaxCapacity"] - max_capacity_v[idx] ) <= 0.05
        assert abs( row["Lifetime"] - lifetime_v[idx] ) <= 0.05
        assert abs( row["Capex"] - Capex_v[idx] ) <= 0.05
        assert abs( row["HeatRate"] - heat_rate_v[idx] ) <= 0.05
        assert abs( row["FuelCost"] - fuel_cost_v[idx] ) <= 0.05
        assert abs( row["VOM"] - vom_v[idx] ) <= 0.05

    model = initialize_model(data, n_hours = 24, with_resilience_constraints=False)
    assert list(model.thermal.plants_set) == ['83_GAS', '83_Coal']
    

def test_load_data_storage_values():
    test_data_path = os.path.join(os.path.dirname(__file__), '..', REL_PATH_DATA_RUN_OF_RIVER_TEST)
    test_data_path = os.path.abspath(test_data_path)

    data = load_data( test_data_path )

    assert data["STORAGE_SET_J_TECHS"] == ["Li-Ion", "CAES", "PHS", "H2"]
    assert data["STORAGE_SET_B_TECHS"] == ["Li-Ion", "PHS",]

    df = data["storage_data"]
    P_capex_v = [97.78, 842.63, 1063.32, 1414.84]
    E_capex_v = [115.67, 34.66, 53.12, 1.09]
    Eff_v = [0.86,0.632133333,0.782,0.44]
    Min_Duration_v = [1, 1, 1, 1]
    Max_Duration_v = [12, 24, 24, 6480]
    Max_P_v = [100000, 100000, 100000, 100000]
    FOM_v = [10.3, 4.120718067, 8.241436134, 47.38825777]
    VOM_v = [3.09, 4.120718067, 1.030179517, 0]
    Lifetime_v = [13, 30, 55, 18]
    CostRatio_v = [0.5, 0.325, 0.5, 0.49]

    # Check some specific values in the storage_data DataFrame
    for i, tech in enumerate( data["STORAGE_SET_J_TECHS"] ):
        assert abs( df.loc["P_Capex", tech] - P_capex_v[i] ) <= 0.05
        assert abs( df.loc["E_Capex", tech] - E_capex_v[i] ) <= 0.05
        assert abs( df.loc["Eff", tech] - Eff_v[i] ) <= 0.05
        assert abs( df.loc["Min_Duration", tech] - Min_Duration_v[i] ) <= 0.05
        assert abs( df.loc["Max_Duration", tech] - Max_Duration_v[i] ) <= 0.05
        assert abs( df.loc["Max_P", tech] - Max_P_v[i] ) <= 0.05
        assert abs( df.loc["FOM", tech] - FOM_v[i] ) <= 0.05
        assert abs( df.loc["VOM", tech] - VOM_v[i] ) <= 0.05
        assert abs( df.loc["Lifetime", tech] - Lifetime_v[i] ) <= 0.05
        assert abs( df.loc["CostRatio", tech] - CostRatio_v[i] ) <= 0.05


