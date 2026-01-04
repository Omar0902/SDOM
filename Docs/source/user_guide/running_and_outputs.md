# Running SDOM and Understanding Outputs

This guide covers how to run SDOM optimizations and interpret the results.

```{note}
You can include content from your `1_3_Running_SDOM and outputs.md` here.
```

## Running an Optimization

### Basic Workflow

```python
from sdom import (
    configure_logging,
    load_data, 
    initialize_model, 
    run_solver,
    get_default_solver_config_dict,
    export_results
)
import logging

# 1. Configure logging (optional but recommended)
configure_logging(level=logging.INFO)

# 2. Load input data
data = load_data('./Data/my_scenario/')

# 3. Initialize the optimization model
model = initialize_model(
    data=data,
    n_hours=8760,  # Full year
    with_resilience_constraints=False,
    model_name="SDOM_MyScenario"
)

# 4. Configure solver
solver_config = get_default_solver_config_dict(
    solver_name="cbc",  # or "highs"
    executable_path="./Solver/bin/cbc.exe"
)

# 5. Run optimization
results_list, best_result, solver_result = run_solver(model, solver_config)

# 6. Export results
export_results(model, case="scenario_1", output_dir="./results_pyomo/")

# 7. Access results
print(f"Optimization Status: {solver_result.solver.termination_condition}")
print(f"Total System Cost: ${best_result['Total_Cost']:,.2f}")
```

### Shorter Time Horizons

For testing or sensitivity analysis, you can run shorter simulations:

```python
# 24-hour test run
model = initialize_model(data, n_hours=24)

# One week (168 hours)
model = initialize_model(data, n_hours=168)

# One month (~730 hours)
model = initialize_model(data, n_hours=730)
```

```{warning}
Budget formulations (monthly/daily hydro) require specific hour multiples. SDOM will automatically adjust and log a warning.
```

## Solver Configuration

### CBC Solver (Open-Source)

```python
solver_config = get_default_solver_config_dict(
    solver_name="cbc",
    executable_path="./Solver/bin/cbc.exe"  # Windows
    # executable_path="./Solver/bin/cbc"     # Unix/MacOS
)

# Customize solver options
solver_config["options"]["mip_rel_gap"] = 0.01  # 1% MIP gap
solver_config["solve_keywords"]["timelimit"] = 3600  # 1 hour limit
```

### HiGHS Solver (Open-Source)

```python
solver_config = get_default_solver_config_dict(
    solver_name="highs",
    executable_path=""  # Uses system PATH
)
```

### Xpress Solver (Commercial)

```python
solver_config["solver_name"] = "xpress_direct"
solver_config["options"]["miprelstop"] = 0.002
```

## Understanding Results

### Results Dictionary Structure

The `best_result` dictionary contains:

```python
{
    'Total_Cost': float,           # Objective value ($)
    'GenMix_Target': float,        # Carbon-free target (0-1)
    
    # Installed Capacities
    'Total_CapWind': float,        # Wind capacity (MW)
    'Total_CapPV': float,          # Solar PV capacity (MW)
    'Total_CapCC': float,          # Thermal capacity (MW)
    'Total_CapScha': dict,         # Storage charge capacity by tech (MW)
    'Total_CapSdis': dict,         # Storage discharge capacity by tech (MW)
    'Total_EcapS': dict,           # Storage energy capacity by tech (MWh)
    
    # Total Generation
    'Total_GenWind': float,        # Total wind generation (MWh)
    'Total_GenPV': float,          # Total solar generation (MWh)
    'Total_GenS': dict,            # Total storage discharge by tech (MWh)
    
    # Hourly Dispatch
    'WindGen': dict,               # {hour: MW}
    'SolarPVGen': dict,            # {hour: MW}
    'AggThermalGen': dict,         # {hour: MW}
    
    # Cost Breakdowns
    'SolarCapex': float,           # Annualized solar CAPEX ($)
    'WindCapex': float,            # Annualized wind CAPEX ($)
    'SolarFOM': float,             # Solar fixed O&M ($)
    'WindFOM': float,              # Wind fixed O&M ($)
    'TotalThermalCapex': float,    # Thermal CAPEX ($)
    'ThermalFuel': float,          # Fuel costs ($)
    'ThermalFOM': float,           # Thermal fixed O&M ($)
    'ThermalVOM': float,           # Thermal variable O&M ($)
    
    # Storage costs per technology (e.g., for Li-Ion):
    'Li-IonPowerCapex': float,
    'Li-IonEnergyCapex': float,
    'Li-IonFOM': float,
    'Li-IonVOM': float,
}
```

### Exported CSV Files

SDOM exports three CSV files to `output_dir`:

#### 1. OutputGeneration_{case}.csv

Hourly dispatch for all technologies:

| Column | Description | Unit |
|--------|-------------|------|
| Scenario | Case identifier | - |
| Hour | Hour index (1-8760) | - |
| Solar PV Generation (MW) | Solar dispatch | MW |
| Solar PV Curtailment (MW) | Curtailed solar | MW |
| Wind Generation (MW) | Wind dispatch | MW |
| Wind Curtailment (MW) | Curtailed wind | MW |
| All Thermal Generation (MW) | Thermal dispatch | MW |
| Hydro Generation (MW) | Hydro dispatch | MW |
| Nuclear Generation (MW) | Nuclear generation | MW |
| Other Renewables Generation (MW) | Other renewables | MW |
| Imports (MW) | Cross-border imports | MW |
| Storage Charge/Discharge (MW) | Net storage (+ discharge) | MW |
| Exports (MW) | Cross-border exports | MW |
| Load (MW) | Demand | MW |

#### 2. OutputStorage_{case}.csv

Hourly storage operation by technology:

| Column | Description | Unit |
|--------|-------------|------|
| Hour | Hour index | - |
| Technology | Storage type | - |
| Charging power (MW) | Charge rate | MW |
| Discharging power (MW) | Discharge rate | MW |
| State of charge (MWh) | Energy stored | MWh |

#### 3. OutputSummary_{case}.csv

Summary metrics and capacities:

- Total system cost
- Installed capacities by technology
- Total generation by technology
- Cost breakdowns (CAPEX, OPEX by component)
- Storage characteristics

## Analyzing Results

### Capacity Results

```python
# Print installed capacities
print("Installed Capacities:")
print(f"  Wind: {best_result['Total_CapWind']:.2f} MW")
print(f"  Solar PV: {best_result['Total_CapPV']:.2f} MW")
print(f"  Thermal: {best_result['Total_CapCC']:.2f} MW")

# Storage capacities
print("\nStorage Capacities:")
for tech in best_result['Total_CapScha'].keys():
    print(f"  {tech}:")
    print(f"    Charge: {best_result['Total_CapScha'][tech]:.2f} MW")
    print(f"    Discharge: {best_result['Total_CapSdis'][tech]:.2f} MW")
    print(f"    Energy: {best_result['Total_EcapS'][tech]:.2f} MWh")
    duration = best_result['Total_EcapS'][tech] / best_result['Total_CapSdis'][tech]
    print(f"    Duration: {duration:.2f} hours")
```

### Cost Breakdown

```python
import pandas as pd

# Create cost summary
costs = {
    'Solar CAPEX': best_result['SolarCapex'],
    'Wind CAPEX': best_result['WindCapex'],
    'Thermal CAPEX': best_result['TotalThermalCapex'],
    'Solar FOM': best_result['SolarFOM'],
    'Wind FOM': best_result['WindFOM'],
    'Thermal FOM': best_result['ThermalFOM'],
    'Thermal Fuel': best_result['ThermalFuel'],
    'Thermal VOM': best_result['ThermalVOM'],
}

# Add storage costs
for tech in ['Li-Ion', 'CAES', 'PHS', 'H2']:
    if f'{tech}PowerCapex' in best_result:
        costs[f'{tech} Power CAPEX'] = best_result[f'{tech}PowerCapex']
        costs[f'{tech} Energy CAPEX'] = best_result[f'{tech}EnergyCapex']
        costs[f'{tech} FOM'] = best_result[f'{tech}FOM']
        costs[f'{tech} VOM'] = best_result[f'{tech}VOM']

df_costs = pd.DataFrame.from_dict(costs, orient='index', columns=['Cost ($)'])
print(df_costs.sort_values('Cost ($)', ascending=False))
```

### Time Series Analysis

```python
import matplotlib.pyplot as plt
import pandas as pd

# Extract hourly data
hours = list(range(1, len(best_result['SolarPVGen']) + 1))
solar_gen = [best_result['SolarPVGen'][h] for h in hours]
wind_gen = [best_result['WindGen'][h] for h in hours]
thermal_gen = [best_result['AggThermalGen'][h] for h in hours]

# Plot first week
plt.figure(figsize=(12, 6))
week_hours = hours[:168]
plt.plot(week_hours, solar_gen[:168], label='Solar PV')
plt.plot(week_hours, wind_gen[:168], label='Wind')
plt.plot(week_hours, thermal_gen[:168], label='Thermal')
plt.xlabel('Hour')
plt.ylabel('Generation (MW)')
plt.title('First Week Generation Dispatch')
plt.legend()
plt.grid(True)
plt.show()
```

## Troubleshooting

### Infeasible Solutions

If the solver returns infeasible:

```python
from pyomo.util.infeasible import log_infeasible_constraints

# Log which constraints are violated
log_infeasible_constraints(model)
```

Common causes:
- GenMix_Target too high for available VRE resources
- Insufficient storage or thermal capacity limits
- Budget constraints that don't match load patterns

### Solver Performance

For large problems:
- Increase MIP gap: `solver_config["options"]["mip_rel_gap"] = 0.01`
- Set time limit: `solver_config["solve_keywords"]["timelimit"] = 7200`
- Use parallel processing: `solver_config["options"]["threads"] = 4`

## Next Steps

- [Explore the Pyomo model structure](exploring_model.md)
- [View API reference](../api/index.md)
