# Contents

- [1. Getting Started: Running SDOM with a Python Script](#1-getting-started-running-sdom-with-a-python-script)
- [2. Outputs](#2-outputs)
- [3. Next Section - Debugging and Exploring SDOM Pyomo Model](#3-next-section---debugging-and-exploring-sdom-pyomo-model)

# 1. Getting Started: Running SDOM with a Python Script

This section explains the steps involved in running the SDOM model using Python, with code snippets for each step:

1. **Import Required Modules**  
    Import SDOM functions, utilities for logging and the solver interface module:
    ```python
    import sdom
    from sdom import run_solver, initialize_model, configure_logging, get_default_solver_config_dict
    from sdom import load_data, export_results

    import logging
    import highspy
    ```
2. **Configure Logging**  
    Set up logging to display informational messages:
    ```python
    configure_logging(level=logging.INFO)
    ```

3. **Set Simulation Parameters**  
    Define simulation steps, resilience constraints, and case name:
    ```python
    n_steps = 730*1  # Number of steps in the simulation (in hours)
    with_resilience_constraints = False
    case = "br_test_daily_b"
    ```
> **⚠️ Attention:**  
>  - Make sure all required CSV files are present in the specified folder before starting the simulation. [See the required input files here](./sdom_Inputs.md)
>  - Please keep the root names of each file. For instance, in the sample files you can change "2025" for whatever you prefer, but keeping the root name. For example, for "CapSolar_2025.csv" file you need to keep the root name as "CapSolar".
>  - Please do not change the column names of each csv files.

4. **Load Input Data**  
    Load input data from the specified directory and define output folder:
    ```python
    data_dir = "sample_data\\br_test_daily_b\\"
    data = load_data(data_dir)
    output_dir = f'./sample_results_{case}/'
    ```

5. **Initialize the Model**  
    Initialize the SDOM model with data and parameters and get the pyomo instance of the model:
    ```python
    model = initialize_model(
        data,
        n_hours=n_steps,
        with_resilience_constraints=with_resilience_constraints
    )
    ```

6. **Configure Solver**  
    Get default solver configuration for HiGHS open-source solver:
    ```python
    solver_dict = get_default_solver_config_dict(
        solver_name="highs",
        executable_path=""
    )
    ```
Currently the SDOM python version has been tested using [open-source CBC solver](https://www.coin-or.org/Cbc/cbcuserguide.html) through windows executable and [HiGHS open-source solver](https://highs.dev/) through highspy module.

7. **Run the Solver**  
    Execute the solver to find an optimal solution:
    ```python
    best_result = run_solver(model, solver_dict)
    ```

8. **Export Results**  
    Export results if a solution is found, otherwise print a message:
    ```python
    if best_result:
        export_results(model, case, output_dir=output_dir)
    else:
        print(f"Solver did not find an optimal solution for given data and with resilience constraints = {with_resilience_constraints}, skipping result export.")
    ```

9. **Outputs**
# 1. Getting Started: Running SDOM with a Python Script

This section explains the steps involved in running the SDOM model using Python, with code snippets for each step:

1. **Import Required Modules**  
    Import SDOM functions, utilities for logging and the solver interface module:
    ```python
    import sdom
    from sdom import run_solver, initialize_model, configure_logging, get_default_solver_config_dict
    from sdom import load_data, export_results

    import logging
    import highspy
    ```
2. **Configure Logging**  
    Set up logging to display informational messages:
    ```python
    configure_logging(level=logging.INFO)
    ```

3. **Set Simulation Parameters**  
    Define simulation steps, resilience constraints, and case name:
    ```python
    n_steps = 730*1  # Number of steps in the simulation (in hours)
    with_resilience_constraints = False
    case = "br_test_daily_b"
    ```
> **⚠️ Attention:**  
>  - Make sure all required CSV files are present in the specified folder before starting the simulation. [See the required input files here](training_material/training_sesion_1/1_2_SDOM_Inputs.md)
>  - Please keep the root names of each file. For instance, in the sample files you can change "2025" for whatever you prefer, but keeping the root name. For example, for "CapSolar_2025.csv" file you need to keep the root name as "CapSolar".
>  - Please do not change the column names of each csv files.

4. **Load Input Data**  
    Load input data from the specified directory and define output folder:
    ```python
    data_dir = "sample_data\\br_test_daily_b\\"
    data = load_data(data_dir)
    output_dir = f'./sample_results_{case}/'
    ```

5. **Initialize the Model**  
    Initialize the SDOM model with data and parameters:
    ```python
    model = initialize_model(
        data,
        n_hours=n_steps,
        with_resilience_constraints=with_resilience_constraints
    )
    ```

6. **Configure Solver**  
    Get default solver configuration for HiGHS open-source solver:
    ```python
    solver_dict = get_default_solver_config_dict(
        solver_name="highs",
        executable_path=""
    )
    ```

7. **Run the Solver**  
    Execute the solver to find an optimal solution:
    ```python
    best_result = run_solver(model, solver_dict)
    ```

8. **Export Results**  
    Export results if a solution is found, otherwise print a message:
    ```python
    if best_result:
        export_results(model, case, output_dir=output_dir)
    else:
        print(f"Solver did not find an optimal solution for given data and with resilience constraints = {with_resilience_constraints}, skipping result export.")
    ```


# 2. Outputs

In the path specified by "output_dir", sdom will writhe the following output csv files:

| File name                            | Description                                              |
|--------------------------------------|----------------------------------------------------------|
| OutputGeneration_CASENAME.csv        | Hourly generation results aggregated by technology, curtailment, imports/exports and Load. |
| OutputStorage_CASENAME.csv           | Hourly storage operation results (charging/discharging and SOC). |
| OutputSummary_CASENAME.csv           | Summary of key simulation results and statistics.        |
| OutputThermalGeneration_CASENAME.csv | Hourly results for thermal generation plants.             |


# 3. Next Section - Debugging and Exploring SDOM Pyomo Model
Now, continue to the next section, [Debugging and Exploring SDOM Pyomo Model](sdom_Exploring_pyomo_model_example.md)