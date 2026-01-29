# Core Optimization Functions

Main functions for running SDOM optimizations.

## Model Initialization

```{eval-rst}
.. autofunction:: sdom.optimization_main.initialize_model
```

## Solver Configuration

```{eval-rst}
.. autofunction:: sdom.optimization_main.get_default_solver_config_dict

.. autofunction:: sdom.optimization_main.configure_solver
```

## Running Optimization

```{eval-rst}
.. autofunction:: sdom.optimization_main.run_solver
```

## Collecting Results

```{eval-rst}
.. autofunction:: sdom.optimization_main.collect_results
```

## Configuration

```{eval-rst}
.. autofunction:: sdom.config_sdom.configure_logging

.. autoclass:: sdom.config_sdom.ColorFormatter
   :members:
   :special-members: __init__
```

## Example Usage

```python
from sdom import (
    load_data,
    initialize_model, 
    get_default_solver_config_dict,
    run_solver
)

# Load data
data = load_data('./Data/scenario/')

# Initialize model
model = initialize_model(
    data=data,
    n_hours=8760,
    with_resilience_constraints=False
)

# Configure solver
solver_config = get_default_solver_config_dict(
    solver_name="cbc",
    executable_path="./Solver/bin/cbc.exe"
)

# Run optimization
results_list, best_result, solver_result = run_solver(model, solver_config)

# Access results
print(f"Total Cost: ${best_result['Total_Cost']:,.2f}")
```
