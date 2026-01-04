# SDOM Input Data

This page describes all input data requirements for running SDOM optimizations.

```{note}
You can include your original `1_2_SDOM_Inputs.md` content here.
```

## Input Data Structure

All input CSV files should be placed in a directory (e.g., `Data/scenario_name/`). The file names are defined in `constants.py` and are flexible (case-insensitive matching with spaces/hyphens/underscores ignored).

## Required Files

### 1. Formulations Configuration

**File**: `formulations.csv`

Specifies which formulation to use for each model component:

| Component | Formulation | Description |
|-----------|-------------|-------------|
| hydro | RunOfRiverFormulation | Fixed hourly hydro profile |
| hydro | MonthlyBudgetFormulation | Monthly energy budget constraint |
| hydro | DailyBudgetFormulation | Daily energy budget constraint |
| Imports | NotModel | No imports modeled |
| Imports | CapacityPriceNetLoadFormulation | Price-based import optimization |
| Exports | NotModel | No exports modeled |
| Exports | CapacityPriceNetLoadFormulation | Price-based export optimization |

**Example**:
```csv
Component,Formulation
hydro,MonthlyBudgetFormulation
Imports,CapacityPriceNetLoadFormulation
Exports,NotModel
```

### 2. Load Data

**File**: `Load_hourly.csv`

Hourly electricity demand profile.

**Columns**:
- `*Hour`: Hour index (1-8760)
- `Load`: Demand in MW

**Example**:
```csv
*Hour,Load
1,45230.5
2,43100.2
3,41500.8
...
```

### 3. VRE (Variable Renewable Energy) Data

#### Solar PV

**Capacity Factors**: `CFSolar.csv`
- Columns: `*Hour`, `plant_1`, `plant_2`, ..., `plant_n`
- Values: Capacity factors (0-1) for each hour and plant

**Plant Data**: `CapSolar.csv`
- Columns: `sc_gid` (plant ID), `capacity` (MW), `CAPEX_M` ($/kW), `FOM_M` ($/kW-yr), `trans_cap_cost` ($)

#### Wind

**Capacity Factors**: `CFWind.csv`
**Plant Data**: `CapWind.csv`
(Same structure as solar)

### 4. Fixed Generation Sources

#### Nuclear
**File**: `Nucl_hourly.csv`
- Fixed nuclear generation profile (MW)

#### Large Hydropower
**File**: `lahy_hourly.csv`
- Hourly hydro generation/availability (MW)

**Budget Formulation Files** (if using Monthly/Daily budgets):
- `lahy_max_hourly.csv`: Maximum hourly capacity (MW)
- `lahy_min_hourly.csv`: Minimum hourly generation (MW)

#### Other Renewables
**File**: `otre_hourly.csv`
- Other renewable sources (geothermal, biomass, etc.)

### 5. Storage Technology Data

**File**: `StorageData.csv`

Technology characteristics for each storage type:

| Parameter | Description | Unit |
|-----------|-------------|------|
| P_Capex | Power capacity cost | $/kW |
| E_Capex | Energy capacity cost | $/kWh |
| Eff | Round-trip efficiency | fraction (0-1) |
| Min_Duration | Minimum energy duration | hours |
| Max_Duration | Maximum energy duration | hours |
| Max_P | Maximum power capacity | MW |
| Coupled | Charge/discharge coupling | 0 or 1 |
| FOM | Fixed O&M | $/kW-yr |
| VOM | Variable O&M | $/MWh |
| Lifetime | Expected lifetime | years |
| CostRatio | Charge/discharge cost ratio | fraction |

**Example**:
```csv
Parameter,Li-Ion,CAES,PHS,H2
P_Capex,300,100,1500,800
E_Capex,150,2,10,5
Eff,0.85,0.70,0.80,0.40
...
```

### 6. Thermal Generation Data

**File**: `Data_BalancingUnits.csv`

Parameters for thermal balancing units (e.g., natural gas):

| Parameter | Description | Unit |
|-----------|-------------|------|
| MinCapacity | Minimum deployable capacity | MW |
| MaxCapacity | Maximum deployable capacity | MW |
| Lifetime | Expected lifetime | years |
| Capex | Capital cost | $/kW |
| HeatRate | Heat rate | MMBtu/MWh |
| FuelCost | Fuel cost | $/MMBtu |
| VOM | Variable O&M | $/MWh |
| FOM | Fixed O&M | $/kW-yr |

### 7. System Scalars

**File**: `scalars.csv`

System-level parameters:

| Parameter | Description | Example Value |
|-----------|-------------|---------------|
| r | Discount rate | 0.07 |
| GenMix_Target | Carbon-free generation target | 0.95 (95%) |
| alpha_Nuclear | Nuclear activation flag | 1.0 |
| alpha_Hydro | Hydro activation flag | 1.0 |
| alpha_OtherRenewables | Other renewables flag | 1.0 |

**Example**:
```csv
Parameter,Value
r,0.07
GenMix_Target,0.95
alpha_Nuclear,1.0
alpha_Hydro,1.0
alpha_OtherRenewables,1.0
```

### 8. Import/Export Data (Optional)

**If using CapacityPriceNetLoadFormulation**:

- `Import_Cap.csv`: Hourly import capacity limits (MW)
- `Import_Prices.csv`: Hourly import prices ($/MWh)
- `Export_Cap.csv`: Hourly export capacity limits (MW)
- `Export_Prices.csv`: Hourly export prices ($/MWh)

## Data Validation

SDOM performs several validation checks during data loading:

1. **File Existence**: All required files must be present
2. **Plant Consistency**: Solar/wind plant IDs must match between CF and CAPEX files
3. **Completeness**: Filters out plants with missing data (NaN values)
4. **Formulation Validity**: Checks that specified formulations are valid
5. **Hour Count**: For budget formulations, adjusts hours to be multiple of budget interval

## Example Data Loading

```python
from sdom import load_data

# Load data from directory
data = load_data('./Data/my_scenario/')

# Access loaded data
print(f"Number of solar plants: {len(data['solar_plants'])}")
print(f"Number of wind plants: {len(data['wind_plants'])}")
print(f"Storage technologies: {data['STORAGE_SET_J_TECHS']}")
print(f"Discount rate: {data['scalars'].loc['r', 'Value']}")
```

## Tips for Data Preparation

1. **Consistent Plant IDs**: Use string IDs for VRE plants (e.g., "101", "202")
2. **Hour Indexing**: Use 1-based indexing (1-8760) for consistency
3. **Units**: Stick to MW for power, MWh for energy, $ for costs
4. **File Naming**: Use flexible naming (case doesn't matter, underscores/hyphens optional)
5. **Missing Data**: Remove rows/plants with incomplete data before running

## Next Steps

- [Run SDOM optimization](running_and_outputs.md)
- [Explore model structure](exploring_model.md)
