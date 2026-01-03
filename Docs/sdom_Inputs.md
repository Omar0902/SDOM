# Contents
- [1. Input Files Folder](#1-input-files-folder)
- [2. CSV input files](#2-csv-input-files)
    - [2.1. formulations.csv](#21-formulationscsv)
    - [2.2. Variable Renewable Energies (VRE)](#22-variable-renewable-energies-vre)
        - [2.2.1 CapSolar.csv/CapWind.csv](#221-capsolarcsvcapwindcsv)
        - [2.2.2 CFSolar.csv/CFWind.csv](#222-cfsolarcsvcfwindcsv)
    - [2.3. Data_BalancingUnits.csv](#23-data_balancingunitscsv)
    - [2.4. Hydro power](#24-hydro-power)
        - [2.4.1 lahy_hourly.csv](#241-lahy_hourlycsv)
        - [2.4.2 lahy_min_hourly.csv/lahy_max_hourly.csv (optional)](#242-lahy_min_hourlycsvlahy_max_hourlycsv-optional)
    - [2.5. Nucl_hourly.csv/otre_hourly.csv](#25-nucl_hourlycsvotre_hourlycsv)
    - [2.6. Load_hourly.csv](#26-load_hourlycsv)
    - [2.7. StorageData.csv](#27-storagedatacsv)
    - [2.8. scalars.csv](#28-scalarscsv)
    - [2.9. Imports/Exports (Optional files)](#29-importsexports-optional-files)
        - [2.9.1. Import_Cap.csv/Export_Cap.csv](#291-import_capcsvexport_capcsv)
        - [2.9.2. import_prices.csv/export_prices.csv](#292-import_pricescsvexport_pricescsv)
- [3. Next Section - Getting Started: Running SDOM with a Python Script](#3-next-section---getting-started-running-sdom-with-a-python-script)

# 1. Input Files Folder
All the csv files you'll use in an SDOM optimization runs should be in one single folder. In this case, sample files are located at the route: "sample_data\br_test_daily_b".

This folder will be specified as a string containing the path in sdom when you do:

```
data_dir = "sample_data\\br_test_daily_b\\" 
data = load_data( data_dir ) 
```

In the next section each file will be listed and the data it is supossed to be in each field will be described.

> **⚠️ Attention:**  
>  - Make sure all required CSV files are present in the specified folder before starting the simulation.
>  - Please keep the root names of each file. For instance, in the sample files you can change "2025" for whatever you prefer, but keeping the root name. For example, for "CapSolar_2025.csv" file you need to keep the root name as "CapSolar_".
>  - Please do not change the column names of each csv files.

# 2. CSV input files
In this section the SDOM input csv files will be grouped by technology, so all the data required for each technology is in a single subsection. The description of the required data for each field will be described.


## 2.1. formulations.csv

This file the user selects the modeling approach (formulation) for each major system component in the SDOM optimization model. Each row assigns a formulation to a component, determining how SDOM will represent its behavior and constraints during optimization.


**Important Notes:**
- Only one formulation should be assigned per component.
- The chosen formulation directly affects how SDOM optimizes and simulates each component.
- Refer to the tables below for valid formulations for each component.

**CSV file columns:**
| Field/Column           | Description                                                                    |Expected type |
|------------------------|--------------------------------------------------------------------------------|--------------|
| Component              | String with the component name you are going to set the formulation (Model).   |string        |
| Formulation            | Name of the formulation (model) you want to use. See more below.               |String        |
| Description (Optional) | Just a description/guidelines that developers let for users.                   |String        |

The following table, shows the valid formulations for each component:

| Component          | Available formulations                                                         |
|--------------------|--------------------------------------------------------------------------------|
| Hydro              | "MonthlyBudgetFormulation" (Budget of 730h), "DailyBudgetFormulation" (Budget of 24h), "RunOfRiverFormulation" (Generation according with input time series and it is not optimized). |
| Thermal            | "NoRampsDispatchFormulation".                                                  |
| Imports            | "CapacityPriceNetLoadFormulation", "NotModel" (When you want to ignore Imports).   |
| Exports            | "CapacityPriceNetLoadFormulation", "NotModel" (When you want to ignore Exports).   |


## 2.2. Variable Renewable Energies (VRE)

> **⚠️ Attention:**  
>  - Make sure that each "sc_gid" defined in "CapSolar.csv" and "CapWind.csv" has its correspondend capacity factor hourly profile in the "CFSolar.csv" or "CFWind.csv" files .


### 2.2.1 CapSolar.csv/CapWind.csv
This file lists all candidate sites for solar PV and wind energy deployment. For each site, it specifies the maximum allowed installed capacity, geographic coordinates, capital expenditure (CAPEX), fixed operation and maintenance (FOM) costs, and transmission interconnection costs. These parameters are used by SDOM to evaluate investment options and optimize resource allocation across the available sites.

**CSV file columns:**
| Field/Column    | Description                                                                                         |Expected type |
|-----------------|-----------------------------------------------------------------------------------------------------|--------------|
| sc_gid          | Unique identifier for each PV/Wind site or resource that will be represented by a single profile.   |string        |
| capacity        | Upper bound for the allowed installed capacity at the site (MW).                                    |float         |
| latitude        | Latitude coordinate of the site (optional for future fetching of VRE files).                        |float         |
| longitude       | Longitude coordinate of the site (optional for future fetching of VRE profiles).                    |float         |
| trans_cap_cost  | Transmission Capital expediture costs associated with transmission in USD/kW                        |float         |
| CAPEX_M         | Capital expenditure in USD/kW.                                                                      |float         |
| FOM_M           | Fixed operation and maintenance cost in USD/kW.                                                     |float         |


### 2.2.2 CFSolar.csv/CFWind.csv
This file defines the hourly solar/wind capacity factors for each one of the potential sites defined in 2.1.1. This information can be obtained using, for instance [NLR SAM simulations](https://sam.nrel.gov/download.html) or [reV](https://www.nrel.gov/gis/renewable-energy-potential).

**CSV file columns:**
| Field/Column    | Description                                                                                         |Expected type |
|-----------------|-----------------------------------------------------------------------------------------------------|--------------|
| Hour            | Number of the hour of the year, from 1 to 8760 (You can choose the number of hours you prefer)*.            |Int           |
| Col for each id | The estimated capacity factor at each hour of the year for each site in MWh/installed MW.          |float         |


> **\*⚠️ Attention:**  
>  - Ensure that your input files contain a number of hours equal to or greater than the `n_hours` parameter specified when calling the `initialize_model()` function:

```
model = initialize_model(
    data,
    n_hours=n_steps,
    with_resilience_constraints=with_resilience_constraints
)
```
## 2.3. Data_BalancingUnits.csv

This file contains essential data for thermal generation plants or aggregated units that participate in system balancing. Each row represents a plant or group of plants, specifying their technical and economic parameters required for SDOM optimization.

**Key considerations:**
- Each `Plant_id` must be unique and consistently referenced across other input files.
- Capacity values (`MinCapacity`, `MaxCapacity`) set the bounds for possible investments (installed capacity).
- To represent already existent generation fleet it is recomended add a new row where `MinCapacity` = `MaxCapacity` and CAPEX = 0


**CSV file columns:**
| Field/Column | Description | Expected type |
|--------------|-------------|---------------|
| Plant_id     | Unique identifier for each thermal generation plant or aggregation of plants. | string |
| MinCapacity  | Minimum allowed installed capacity at the plant (MW). | float |
| MaxCapacity  | Maximum allowed installed capacity at the plant (MW). | float |
| Lifetime     | Expected operational lifetime of the plant (years). | int |
| Capex        | Capital expenditure in USD/kW. | float |
| HeatRate     | Heat rate of the plant (fuel energy input per unit electricity output, typically in MMBtu/MWh). | float |
| FuelCost     | Fuel cost in USD/MMBtu. | float |
| VOM          | Variable operation and maintenance cost in USD/MWh. | float |
| FOM          | Fixed operation and maintenance cost in USD/kW. | float |



## 2.4. Hydro power

### 2.4.1 lahy_hourly.csv
This file provides the hourly generation time-series for hydropower plants. The way SDOM utilizes this data depends on the selected hydro formulation ([see section 2.1 formulations.csv](#21-formulationscsv)):

- **RunOfRiverFormulation:**  
    Hydropower generation is directly set to the values specified in the time-series. No optimization is performed; the model simply follows the provided hourly profile.

- **Budget Formulations (MonthlyBudgetFormulation or DailyBudgetFormulation):**  
    SDOM aggregates the time-series data into energy budgets over consecutive periods—24 hours for daily budgets and 730 hours for monthly budgets. These budgets define the total energy available for dispatch within each period, allowing SDOM to optimize the allocation of hydropower generation while respecting the specified limits.
    These budgets usually are outputs from long- and medium-term hydropower planning tools often based on Stochastic dual dynamic programming (SDDP). An example of open-source tool for this is [SimSEE](https://www.simsee.org/)

In summary, this file either serves as a fixed generation profile or as the basis for energy budgets, depending on the chosen hydro formulation.

**CSV file columns:**
| Field/Column    | Description                                                                                         |Expected type |
|-----------------|-----------------------------------------------------------------------------------------------------|--------------|
| *Hour           | Number of the hour of the year, from 1 to 8760 (You can teh number of hours you prefer).            |Int           |
| LargeHydro      | The estimated hydropower generation at each hour of the year in MWh or average values to make the budget.|float         |



### 2.4.2 lahy_min_hourly.csv/lahy_max_hourly.csv (optional)
These files determine the lower and upper bounds for hydropower dispatch when Budget Formulations are used.

**CSV file columns:**
| Field/Column    | Description                                                                                         |Expected type |
|-----------------|-----------------------------------------------------------------------------------------------------|--------------|
| *Hour           | Number of the hour of the year, from 1 to 8760 (You can teh number of hours you prefer).            |Int           |
| LargeHydro      | The estimated hydropower generation bounds at each hour of the year.                                |float         |


### 2.5. Nucl_hourly.csv/otre_hourly.csv
This file provides the hourly generation time-series for nuclear power plants and other renewable plants respectively.

**CSV file columns:**
| Field/Column    | Description                                                                                         |Expected type |
|-----------------|-----------------------------------------------------------------------------------------------------|--------------|
| *Hour           | Number of the hour of the year, from 1 to 8760 (You can teh number of hours you prefer).            |Int           |
| Nuclear/OtherRenewables| The estimated generation at each hour of the year in MWh from Nuclear of Other Renewables (Such as Biomass, for instance).|float    |


### 2.6. Load_hourly.csv
This file provides the system hourly electricity demand time-series.

**CSV file columns:**
| Field/Column    | Description                                                                                         |Expected type |
|-----------------|-----------------------------------------------------------------------------------------------------|--------------|
| *Hour           | Number of the hour of the year, from 1 to 8760 (You can teh number of hours you prefer).            |Int           |
| Load            | The estimated system electricity demand at each hour of the year in MWh.                            |float         |


## 2.7 StorageData.csv
This CSV input file provides key technical and economic parameters for diverse energy storage technologies (Some examples could be: Li-Ion (Lithium-Ion), CAES (Compressed Air Energy Storage), PHS (Pumped Hydro Storage), and H2 (Hydrogen Storage)). Each column represents a technology, and each row specifies a parameter:

| Field        | Description                                                                                                    | Expected type   |
|--------------|----------------------------------------------------------------------------------------------------------------|-----------------|
| P_Capex      | Power-related capital expenditure (USD/kW)                                                                     | float           |
| E_Capex      | Energy-related capital expenditure (USD/kWh)                                                                   | float           |
| Eff          | Round-trip efficiency (fraction)                                                                               | float           |
| Min_Duration | Minimum storage duration (hours)                                                                               | float/int       |
| Max_Duration | Maximum storage duration (hours)                                                                               | float/int       |
| Max_P        | Maximum power capacity (kW)                                                                                    | float/int       |
| MaxCycles    | Maximum number of charge/discharge cycles                                                                      | int             |
| Coupled      | Indicates if input and output power are coupled (1 = coupled - enforces input Power = output Power)            | int (0 or 1)    |
| FOM          | Fixed operation and maintenance cost (USD/kW/year)                                                             | float           |
| VOM          | Variable operation and maintenance cost (USD/kWh)                                                              | float           |
| Lifetime     | Expected system lifetime (years)                                                                               | int             |
| CostRatio    | Ratio of cost allocation between input and output power. If Input Power Capex = Output Power Capex, then CostRatio = 0.5| float           |

**Key considerations:**
- If you dont have energy CAPEX for the technology, and you only have power CAPEX for a particular duration, enforce Min_Duration==Max_Duration.
- If the power capex is equally divided for the input power capacity and output power capacity, set CostRatio = 0.5.
- if the storage technology does not have an specification for MaxCycles, use a large value.

**Cost Data Sources**
Some sources to get cost data for storage technologies are:
 - [NLR Annual Technology Baseline (ATB)](https://atb.nrel.gov/electricity/2024/utility-scale_battery_storage)
 - [PNNL “Energy Storage Cost and Performance Database v2024”](https://www.pnnl.gov/projects/esgc-cost-performance/download-reports)


## 2.8. scalars.csv

This CSV file contains key parameters and their corresponding values for an energy system model. Each row specifies a parameter name and its value, which are used to configure various aspects of the model, such as technology lifetimes, financial rates, and generation mix targets.

| Parameter        | Description                                                                             | Expected Type|
|------------------|-----------------------------------------------------------------------------------------|--------------|
| LifeTimeVRE      | Operational lifetime in years of Variable Renewable Energy sources (To calculate CRF)   | int          |
| GenMix_Target    | Target value for generation mix (e.g., share of renewables). Between 0 and 1.           | float        |
| AlphaNuclear     | Activation/Deactivation (1/0) for nuclear energy                                        | int (0 or 1) |
| AlphaLargHy      | Activation/Deactivation (1/0) for large hydro energy                                    | int (0 or 1) |
| AlphaOtheRe      | Activation/Deactivation (1/0) for other renewable energy sources                        | int (0 or 1) |
| r                | Discount rate or interest rate used in financial calculations (Example: r=0.06)         | float        |
| EUE_max          | Maximum allowed Expected Unserved Energy (EUE) - used when resiliency constraints = true| float        |

**Note:** Adjust parameter values as needed to reflect the specific scenario or assumptions for your energy system analysis.



## 2.9. Imports/Exports (Optional files)
These files are only required when Imports and Exports formulations are set different to "NotModel" in "formulations.csv" ([see section 2.1 formulations.csv](#21-formulationscsv)).

### 2.9.1. Import_Cap.csv/Export_Cap.csv
These files contain

**CSV file columns:**
| Field/Column    | Description                                                                                         |Expected type |
|-----------------|-----------------------------------------------------------------------------------------------------|--------------|
| *Hour           | Number of the hour of the year, from 1 to 8760 (You can teh number of hours you prefer).            |Int           |
| Imports/Exports | The hourly maximum capacity to import/export in MW.                                                 |float         |


### 2.9.2. import_prices.csv/export_prices.csv


**CSV file columns:**
| Field/Column    | Description                                                                                         |Expected type |
|-----------------|-----------------------------------------------------------------------------------------------------|--------------|
| *Hour           | Number of the hour of the year, from 1 to 8760 (You can teh number of hours you prefer).            |Int           |
| Imports_price/Exports_price| The estimated hourly electricity price for importing/exporting energy in USD/MWh.        |float         |


# 3. Next Section - Getting Started: Running SDOM with a Python Script
Now that you have all the input files required to run SDOM, [see here an script example to run sdom model](sdom_example_simple.md)