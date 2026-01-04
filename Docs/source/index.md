# SDOM Documentation

Welcome to the **Storage Deployment Optimization Model (SDOM)** documentation!

SDOM is an open-source, high-resolution grid capacity-expansion framework developed by NREL. It's purpose-built to optimize the deployment and operation of energy storage technologies, leveraging hourly temporal resolution and granular spatial representation of Variable Renewable Energy (VRE) sources such as solar and wind.

## Quick Links

::::{grid} 2
:gutter: 3

:::{grid-item-card} 📚 User Guide
:link: user_guide/introduction
:link-type: doc

Get started with SDOM, learn about inputs, and run your first optimization
:::

:::{grid-item-card} 🔧 API Reference
:link: api/index
:link-type: doc

Detailed documentation of all modules, classes, and functions
:::

::::

## Key Features

- ⚡ **Accurate Storage Representation**: Short, long, and seasonal storage technologies
- 📆 **Hourly Resolution**: Full 8760-hour annual simulation
- 🌍 **Spatial Granularity**: Fine-grained VRE resource representation
- 🔌 **Copper Plate Modeling**: Computationally efficient system optimization
- 💰 **Cost Minimization**: Optimizes total system cost (CAPEX + OPEX)
- 🐍 **Open Source**: Fully Python-based using Pyomo

## Installation

```bash
# Install uv if you haven't already
pip install uv

# Create virtual environment
uv venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Unix/MacOS)
source .venv/bin/activate

# Install SDOM
uv pip install sdom

# Or install from source
uv pip install -e .
```

## Quick Start

```python
from sdom import load_data, initialize_model, run_solver, get_default_solver_config_dict

# Load input data
data = load_data("./Data/your_scenario/")

# Initialize model (8760 hours = full year)
model = initialize_model(data, n_hours=8760)

# Configure solver
solver_config = get_default_solver_config_dict(
    solver_name="cbc", 
    executable_path="./Solver/bin/cbc.exe"
)

# Solve optimization problem
results_list, best_result, solver_result = run_solver(model, solver_config)

# Access results
print(f"Total Cost: ${best_result['Total_Cost']:,.2f}")
print(f"Wind Capacity: {best_result['Total_CapWind']:.2f} MW")
print(f"Solar Capacity: {best_result['Total_CapPV']:.2f} MW")
```

## Documentation Contents

```{toctree}
:maxdepth: 2
:caption: User Guide

user_guide/introduction
user_guide/inputs
user_guide/running_and_outputs
user_guide/exploring_model
```

```{toctree}
:maxdepth: 2
:caption: API Reference

api/index
api/core
api/models
api/io_manager
api/utilities
```

```{toctree}
:maxdepth: 1
:caption: Development

GitHub Repository <https://github.com/Omar0902/SDOM>
```

## Publications and Use Cases

SDOM has been used in various research studies to analyze storage deployment needs under different renewable energy scenarios. See the [publications page](https://github.com/Omar0902/SDOM#publications-and-use-cases-of-sdom) for details.

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](https://github.com/Omar0902/SDOM/blob/master/CONTRIBUTING.md) for details on how to:

- Report bugs
- Suggest enhancements
- Submit pull requests
- Run tests locally

## License

SDOM is released under the [MIT License](https://github.com/Omar0902/SDOM/blob/master/LICENSE).

## Indices and tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
