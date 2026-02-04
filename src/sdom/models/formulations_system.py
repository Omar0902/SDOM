from pyomo.core import Expression, Constraint


from .formulations_vre import add_vre_fixed_costs
from .formulations_thermal import add_thermal_fixed_costs, add_thermal_variable_costs
from .formulations_storage import add_storage_fixed_costs, add_storage_variable_costs
from .formulations_imports_exports import add_imports_exports_cost
from ..io_manager import get_formulation
####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|



####################################################################################|
# ------------------------------- Objective Function -------------------------------|
####################################################################################|

def objective_rule(model):
    """
    Calculates the total objective value for the optimization model.
    This function computes the sum of annual fixed costs and variable costs for the system.
    Fixed costs include VRE (Variable Renewable Energy), storage, and gas combined cycle (Gas CC) fixed costs.
    Variable costs include Gas CC fuel and variable operation & maintenance (VOM) costs, as well as storage VOM costs.
    Args:
        model: The optimization model instance containing relevant parameters and variables.
    Returns:
        The total objective value as the sum of fixed and variable costs.
    """

    # Annual Fixed Costs
    fixed_costs = (
        add_vre_fixed_costs(model)
        +
        add_storage_fixed_costs(model)
        +
        add_thermal_fixed_costs(model)
    )

    # Variable Costs (Gas CC Fuel & VOM, Storage VOM)
    variable_costs = (
        add_thermal_variable_costs(model)
        + 
        add_storage_variable_costs(model)
    )

    imports_exports_costs = add_imports_exports_cost(model)

    return fixed_costs + variable_costs + imports_exports_costs


####################################################################################|
# ----------------------------------- Expressions ----------------------------------|
####################################################################################|
def net_load_rule(model, h):
    return ( model.demand.ts_parameter[h] 
            - model.pv.total_hourly_availability[h] - model.wind.total_hourly_availability[h] 
            - model.nuclear.alpha * model.nuclear.ts_parameter[h] - model.other_renewables.alpha * model.other_renewables.ts_parameter[h]
            - model.hydro.generation[h] )

def add_system_expressions(model):
    model.net_load = Expression(model.h, rule=net_load_rule)
    return



####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|
# Energy supply demand

def create_supply_balance_rule(has_imports, has_exports):
    """
    Creates a supply balance rule function based on whether imports and exports are enabled.

    Parameters
    ----------
    has_imports : bool
        Whether imports are included in the model.
    has_exports : bool
        Whether exports are included in the model.

    Returns
    -------
    function
        A Pyomo constraint rule function for supply balance.
    """
    def supply_balance_rule(model, h):
        # Base supply balance expression
        balance = (
            model.demand.ts_parameter[h]
            + sum(model.storage.PC[h, j] for j in model.storage.j)
            - sum(model.storage.PD[h, j] for j in model.storage.j)
            - model.nuclear.alpha * model.nuclear.ts_parameter[h]
            - model.hydro.generation[h]
            - model.other_renewables.alpha * model.other_renewables.ts_parameter[h]
            - model.pv.generation[h]
            - model.wind.generation[h]
            - sum(model.thermal.generation[h, bu] for bu in model.thermal.plants_set)
        )

        # Conditionally add imports (imports reduce the need for other generation)
        if has_imports:
            balance = balance - model.imports.variable[h]

        # Conditionally add exports (exports increase the need for generation)
        if has_exports:
            balance = balance + model.exports.variable[h]

        return balance == 0

    return supply_balance_rule

# Generation mix target
# Limit on generation from NG
def genmix_share_rule(model):
    return model.thermal.total_generation <= (1 - model.GenMix_Target)*sum(model.demand.ts_parameter[h] + sum(model.storage.PC[h, j] for j in model.storage.j)
                        - sum(model.storage.PD[h, j] for j in model.storage.j) for h in model.h)

def add_system_constraints(model, data):
    """
    Adds system constraints to the optimization model.

    Parameters
    ----------
    model : pyomo.core.base.PyomoModel.ConcreteModel
        The optimization model to which system constraints will be added.
    data : dict
        Dictionary containing formulation configuration data.

    Returns
    -------
    None
    """
    # Check which components are enabled
    has_imports = get_formulation(data, component="Imports") != "NotModel"
    has_exports = get_formulation(data, component="Exports") != "NotModel"

    # Create and add supply balance constraint with appropriate terms
    supply_balance_rule = create_supply_balance_rule(has_imports, has_exports)
    model.SupplyBalance = Constraint(model.h, rule=supply_balance_rule)

    # Generation mix share constraint
    model.GenMix_Share = Constraint(rule=genmix_share_rule)