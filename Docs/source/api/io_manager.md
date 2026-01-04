# Data I/O Manager

Functions for loading input data and exporting results.

## Data Loading

```{eval-rst}
.. autofunction:: sdom.io_manager.load_data
```

## Formulation Management

```{eval-rst}
.. autofunction:: sdom.io_manager.get_formulation

.. autofunction:: sdom.io_manager.check_formulation
```

## Results Export

```{eval-rst}
.. autofunction:: sdom.io_manager.export_results
```

## Example: Loading Data

```python
from sdom import load_data

# Load data from directory
data = load_data('./Data/my_scenario/')

# Examine loaded data
print(f"Solar plants: {len(data['solar_plants'])}")
print(f"Wind plants: {len(data['wind_plants'])}")
print(f"Storage technologies: {data['STORAGE_SET_J_TECHS']}")

# Access formulation settings
hydro_form = data['formulations']
print(hydro_form)
```

## Example: Exporting Results

```python
from sdom import export_results

# After solving the model
export_results(
    model=model,
    case="scenario_95pct_clean",
    output_dir="./results_pyomo/"
)

# This creates three CSV files:
# - OutputGeneration_scenario_95pct_clean.csv
# - OutputStorage_scenario_95pct_clean.csv
# - OutputSummary_scenario_95pct_clean.csv
```

## Data Dictionary Structure

The `load_data()` function returns a dictionary with these keys:

- `formulations`: Component formulation specifications
- `solar_plants`, `wind_plants`: Lists of plant IDs
- `cf_solar`, `cf_wind`: DataFrames with capacity factors
- `cap_solar`, `cap_wind`: DataFrames with CAPEX and capacity data
- `load_data`: Hourly demand DataFrame
- `nuclear_data`: Hourly nuclear generation
- `large_hydro_data`: Hourly hydro generation
- `other_renewables_data`: Hourly other renewables
- `storage_data`: Storage technology parameters
- `STORAGE_SET_J_TECHS`: List of all storage technologies
- `STORAGE_SET_B_TECHS`: List of coupled storage technologies
- `thermal_data`: Thermal unit parameters
- `scalars`: System-level parameters
- `import_cap`, `export_cap` (optional): Trade capacity limits
- `import_prices`, `export_prices` (optional): Trade prices
