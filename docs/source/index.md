# SDOM Documentation

Welcome to the **Storage Deployment Optimization Model (SDOM)** documentation!

SDOM is an open-source, high-resolution grid capacity-expansion framework developed by the National Lab of the Rockies (NLR). It's purpose-built to optimize the deployment and operation of energy storage technologies, leveraging hourly temporal resolution and granular spatial representation of Variable Renewable Energy (VRE) sources such as solar and wind.


## Key Features

- ⚡ **Accurate Storage Representation**: Short, long, and seasonal storage technologies
- 📆 **Hourly Resolution**: Full 8760-hour annual simulation
- 🌍 **Spatial Granularity**: Fine-grained VRE resource representation
- 🔌 **Copper Plate Modeling**: Computationally efficient system optimization
- 💰 **Cost Minimization**: Optimizes total system cost (CAPEX + OPEX)
- 🐍 **Open Source**: Fully Python-based using Pyomo

## Installation

### System Setup and Prerequisites 

- a. You'll need to install [python](https://www.python.org/downloads/)
  - After the installation make sure the [python enviroment variable is set](https://realpython.com/add-python-to-path/).
- b. Also, You'll need an IDE (Integrated Development Environment), we recommend to install [MS VS code](https://code.visualstudio.com/)
- c. We also recommend to install extensions such as:
  - [edit CSV](https://marketplace.visualstudio.com/items?itemName=janisdd.vscode-edit-csv): To edit and interact with input csv files for SDOM directly in vs code.
  - [vscode-pdf](https://marketplace.visualstudio.com/items?itemName=tomoki1207.pdf): to read and see pdf files directly in vscode.

### Installing SDOM python package
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
#import sdom
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
best_result = run_solver(model, solver_dict)

# Export results
output_dir = "your_output_dir"
export_results(model, case, output_dir=output_dir+"\\")
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

SDOM has been used in various research studies to analyze storage deployment needs under different renewable energy scenarios. See the [publications page](sdom_publications.md) for details.

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](sdom_Developers_guide.md) for details on how to:

- Lear how you can set-up your enviroment to contribute to SDOM source code
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
