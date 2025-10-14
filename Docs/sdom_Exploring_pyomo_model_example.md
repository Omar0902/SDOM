# Contents

- [1. Debugging and Exploring SDOM Pyomo Model](#1-debugging-and-exploring-sdom-pyomo-model)
    - [1.1. Pyomo Model Instance](#11-pyomo-model-instance)
    - [1.2. Pyomo Blocks](#12-pyomo-blocks)
    - [1.3. Discovering model names for parameters, expressions, constraints, etc](#13-discovering-model-names-for-parameters-expressions-constraints-etc)
    - [1.4. Exploring a parameter - model.thermal.heat_rate](#14-exploring-a-parameter---modelthermalheat_rate)
    - [1.5. Exploring a Constraint - model.thermal.heat_rate](#15-exploring-a-constraint---modelthermalheat_rate)

# 1. Debugging and Exploring SDOM Pyomo Model.

# 1.1. Pyomo Model Instance
This section introduces how the user can explore the pyomo model created by sdom and in that way debug the model in a detailed way by accessing all the variables, sets, parameters, expressions, constraints, etc.

SDOM uses [pyomo](https://pyomo.readthedocs.io/en/stable/index.html) to write the optimization model.

When you run

    ```python
    model = initialize_model(
        data,
        n_hours=n_steps,
        with_resilience_constraints=with_resilience_constraints
    )
    ```

the function `initialize_model()` returns the pyomo instance of the optimization model, which in this case is stores in the variable `model`. 

## 1.2. Pyomo Blocks

SDOM leverages on pyomo blocks to separate in different blocks the variables, parameters, expressions, constraints, etc of diferent model components. In this way, in that pyomo instance, SDOM creates the following blocks:

- Core optimization Blocks (Blocks that include variables, sets and parameters)
  - thermal 
  - pv 
  - wind 
  - hydro
  - storage
- Blocks containing onnly parameters (Do not include decision variables)
  - demand
  - nuclear
  - other_renewables
- Optional blocks (These are created depending on the configuration provided by the user)
  - imports
  - exports
  - resiliency

## 1.3. Discovering model names for parameters, expressions, constraints, etc

You can access to parameters, expressions, constraints, etc by doing: model_instance.block_name. For instance:

    ```python
    model.thermal
    ```

when you open this in a debug sesion, you'll observe:

    ```python
    <pyomo.core.base.block.ScalarBlock object at 0x0000021A4C424280>
    special variables
    function variables
    class variables
    CAPEX_M = <pyomo.core.base.param.IndexedParam object at 0x0000021A4C4A34D0>
    FCR = <pyomo.core.base.param.IndexedParam object at 0x0000021A4C4A3C90>
    FOM_M = <pyomo.core.base.param.IndexedParam object at 0x0000021A4C4A36D0>
    VOM_M = <pyomo.core.base.param.IndexedParam object at 0x0000021A4B3BD790>
    active = True
    capacity_generation_constraint = <pyomo.core.base.constraint.IndexedConstraint object at 0x0000021A4D3AA610>
    capex_cost_expr = <pyomo.core.base.expression.ScalarExpression object at 0x0000021A4C4D3BB0>
    data = <pyomo.core.base.param.IndexedParam object at 0x0000021A4C4A2C90>
    doc = None
    fixed_om_cost_expr = <pyomo.core.base.expression.ScalarExpression object at 0x0000021A4C4D3B10>
    fuel_price = <pyomo.core.base.param.IndexedParam object at 0x0000021A4C4AC610>
    generation = <pyomo.core.base.var.IndexedVar object at 0x0000021A4C5F3190>
    heat_rate = <pyomo.core.base.param.IndexedParam object at 0x0000021A4C4A3290>
    ...
    ```
## 1.4. Exploring a parameter - model.thermal.heat_rate

Using `pprint()` function, you'll be able to explore model objects in a simple way. If you run:

    ```python
    model.thermal.heat_rate.pprint()
    ```

You can obtain:

    ```python
    heat_rate : Size=13, Index=thermal.plants_set, Domain=Any, Default=None, Mutable=False
    Key  : Value
    106c :   1.0
    147c :   1.0
    162c :   1.0
    163c :   1.0
    167c :   1.0
    170c :   1.0
    221c :   1.0
    223c :   1.0
    224c :   1.0
    235c :   1.0
    241c :   1.0
     83c :   1.0
     98c :   1.0
    ```

## 1.5. Exploring a Constraint - model.thermal.capacity_generation_constraint

Run

    ```python
    model.thermal.capacity_generation_constraint.pprint()
    ```

an in this way, you can obtain the constraint that limits the output generation of each thermal power plant (Variable) for each time-step to the installed capacity (Variable):

    ```python
    capacity_generation_constraint : Size=9672, Index=h*thermal.plants_set, Active=True
    Key           : Lower : Body                                                                  : Upper : Active
      (1, '106c') :  -Inf :   thermal.generation[1,106c] - thermal.plant_installed_capacity[106c] :   0.0 :   True
      (1, '147c') :  -Inf :   thermal.generation[1,147c] - thermal.plant_installed_capacity[147c] :   0.0 :   True
      (1, '162c') :  -Inf :   thermal.generation[1,162c] - thermal.plant_installed_capacity[162c] :   0.0 :   True
      (1, '163c') :  -Inf :   thermal.generation[1,163c] - thermal.plant_installed_capacity[163c] :   0.0 :   True
      (1, '167c') :  -Inf :   thermal.generation[1,167c] - thermal.plant_installed_capacity[167c] :   0.0 :   True
      (1, '170c') :  -Inf :   thermal.generation[1,170c] - thermal.plant_installed_capacity[170c] :   0.0 :   True
      (1, '221c') :  -Inf :   thermal.generation[1,221c] - thermal.plant_installed_capacity[221c] :   0.0 :   True
      (1, '223c') :  -Inf :   thermal.generation[1,223c] - thermal.plant_installed_capacity[223c] :   0.0 :   True
      (1, '224c') :  -Inf :   thermal.generation[1,224c] - thermal.plant_installed_capacity[224c] :   0.0 :   True
      (1, '235c') :  -Inf :   thermal.generation[1,235c] - thermal.plant_installed_capacity[235c] :   0.0 :   True
      (1, '241c') :  -Inf :   thermal.generation[1,241c] - thermal.plant_installed_capacity[241c] :   0.0 :   True
       (1, '83c') :  -Inf :     thermal.generation[1,83c] - thermal.plant_installed_capacity[83c] :   0.0 :   True
       (1, '98c') :  -Inf :     thermal.generation[1,98c] - thermal.plant_installed_capacity[98c] :   0.0 :   True
      (2, '106c') :  -Inf :   thermal.generation[2,106c] - thermal.plant_installed_capacity[106c] :   0.0 :   True
      ...
    ```

Notice that the index of each constraint and variable in thos case is given by `(time_step, plant_name)`.

