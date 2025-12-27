"""System-level formulations for the SDOM optimization model.

This module implements:
- Objective function: Total system cost minimization
- Supply-demand balance constraints
- Net load calculation (demand minus must-run generation)
- Generation mix constraints (renewable energy targets)
- Import/export integration

These formulations tie together all technology components into a cohesive system model.
"""

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
    Defines the total system cost objective function for minimization.
    
    The objective aggregates all fixed (capital and fixed O&M) and variable (fuel,
    variable O&M) costs across all technologies, plus import costs minus export revenues.
    
    Mathematical Formulation:
        $$\min Z = C_{fixed} + C_{variable} + C_{imports} - R_{exports}$$
    
    Where:
        $C_{fixed}$: Annualized capital costs + annual fixed O&M for VRE, storage, thermal
        $C_{variable}$: Fuel costs + variable O&M for thermal generation and storage
        $C_{imports}$: Cost of imported energy
        $R_{exports}$: Revenue from exported energy
    
    Cost components include:
    - VRE (solar PV, wind): CAPEX, fixed O&M, transmission costs
    - Storage: Power and energy CAPEX, fixed and variable O&M
    - Thermal: CAPEX, fuel costs, fixed and variable O&M
    - Imports/Exports: Energy purchase/sale at market prices
    
    Args:
        model: The Pyomo ConcreteModel instance with all cost expressions defined.
    
    Returns:
        Expression: Total annual system cost ($US/year) to be minimized.
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
    """
    Calculates net load for each hour after accounting for must-run generation.
    
    Net load represents the demand that must be met by dispatchable
    resources (thermal generation and storage). It equals total demand minus
    generation from must-run sources (VRE availability, nuclear, hydro, other renewables).
    
    Mathematical Formulation:
        $$NetLoad(h) = Load(h) - G_{PV,avail}(h) - G_{wind,avail}(h) - G_{nuclear}(h) - G_{hydro}(h) - G_{other}(h)$$
    
    Where:
        - $Load(h)$: Electricity demand in hour h (MW)
        - $G_{PV,avail}(h)$, $G_{wind,avail}(h)$: Available VRE generation (after curtailment) (MW)
        - $G_{nuclear}(h)$, $G_{hydro}(h)$, $G_{other}(h)$: Must-run generation sources (MW)
    
    Positive net load indicates need for dispatchable generation or storage discharge.
    Negative net load indicates excess generation requiring storage charging or curtailment.
    
    Args:
        model: The Pyomo ConcreteModel instance.
        h: Hour index.
    
    Returns:
        Expression: Net load for hour h (MW).
    """
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

def supply_balance_rule(model, h):
    """
    Enforces hourly supply-demand balance without imports/exports.
    
    This equality constraint ensures that total generation plus storage discharge
    exactly equals demand plus storage charging in every hour. It represents the
    fundamental energy conservation principle in power systems.
    
    Mathematical Formulation:
        $$Load(h) + \sum_j PC_j(h) = G_{PV}(h) + G_{wind}(h) + \sum_{bu} G_{thermal,bu}(h) + G_{nuclear}(h) + G_{hydro}(h) + G_{other}(h) + \sum_j PD_j(h)$$
    
    Where:
        - $Load(h)$: Demand in hour h (MW)
        - $PC_j(h)$, $PD_j(h)$: Storage charging/discharging for technology j (MW)
        - $G_{tech}(h)$: Generation from each technology (MW)
    
    Args:
        model: The Pyomo ConcreteModel instance.
        h: Hour index.
    
    Returns:
        Constraint expression: Supply = Demand equality.
    """
    return (
        model.demand.ts_parameter[h] + sum(model.storage.PC[h, j] for j in model.storage.j) - sum(model.storage.PD[h, j] for j in model.storage.j)
        - model.nuclear.alpha * model.nuclear.ts_parameter[h] - model.hydro.generation[h] - model.other_renewables.alpha * model.other_renewables.ts_parameter[h]
        - model.pv.generation[h] - model.wind.generation[h]
        - sum(model.thermal.generation[h, bu] for bu in model.thermal.plants_set)
        == 0
    )

def imp_exp_supply_balance_rule(model, h):
    """
    Enforces hourly supply-demand balance with imports/exports.
    
    Extended version of supply balance that includes international electricity trade.
    Imports add to supply, exports add to demand.
    
    Mathematical Formulation:
        $$Load(h) + \sum_j PC_j(h) + Exports(h) = G_{total}(h) + \sum_j PD_j(h) + Imports(h)$$
    
    Where:
        - $Imports(h)$: Electricity purchased from external markets (MW)
        - $Exports(h)$: Electricity sold to external markets (MW)
        - Other terms same as supply_balance_rule
    
    Args:
        model: The Pyomo ConcreteModel instance.
        h: Hour index.
    
    Returns:
        Constraint expression: Supply + Imports = Demand + Exports equality.
    """
    return (
        model.demand.ts_parameter[h] + sum(model.storage.PC[h, j] for j in model.storage.j) - sum(model.storage.PD[h, j] for j in model.storage.j)
        - model.nuclear.alpha * model.nuclear.ts_parameter[h] - model.hydro.generation[h] - model.other_renewables.alpha * model.other_renewables.ts_parameter[h]
        - model.pv.generation[h] - model.wind.generation[h]
        - sum(model.thermal.generation[h, bu] for bu in model.thermal.plants_set)
        - model.imports.variable[h]
        + model.exports.variable[h]
        == 0
    )

# Generation mix target
# Limit on generation from NG
def genmix_share_rule(model):
    """
    Constrains thermal generation to meet renewable energy share targets.
    
    This policy constraint limits fossil fuel generation to a specified fraction of
    total system demand (including storage losses). It enforces clean energy targets
    by requiring that (1 - target) fraction comes from renewables and other sources.
    
    Mathematical Formulation:
        $$\sum_{h,bu} G_{thermal,bu}(h) \leq (1 - GenMix\_Target) \cdot \sum_h \left[ Load(h) + \sum_j PC_j(h) - \sum_j PD_j(h) \right]$$
    
    Where:
        - $GenMix\_Target$: Minimum clean energy fraction (e.g., 0.8 for 80% clean)
        - $G_{thermal,bu}(h)$: Thermal generation from unit bu in hour h (MW)
        - Right side represents total energy demand including storage losses (MWh)
    
    Examples:
        GenMix_Target = 0.8 → Thermal generation limited to 20% of total demand
        GenMix_Target = 0.5 → Thermal generation limited to 50% of total demand
    
    Args:
        model: The Pyomo ConcreteModel instance.
    
    Returns:
        Constraint expression: Annual thermal generation inequality.
    """
    return model.thermal.total_generation <= (1 - model.GenMix_Target)*sum(model.demand.ts_parameter[h] + sum(model.storage.PC[h, j] for j in model.storage.j)
                        - sum(model.storage.PD[h, j] for j in model.storage.j) for h in model.h)

def add_system_constraints(model, data):
    """
    Adds system-level constraints that tie all generation technologies together.
    
    This function creates two critical system-wide constraints:
    
    1. Supply-Demand Balance: Ensures total generation equals total demand in every hour,
       including storage charging/discharging and optionally imports/exports.
    
    2. Generation Mix Target: Enforces clean energy policy by limiting fossil fuel
       generation to a specified fraction of total system energy.
    
    The function automatically selects the appropriate supply balance formulation based
    on whether international trade (imports/exports) is enabled in the model.
    
    Args:
        model: The Pyomo ConcreteModel instance with all technology variables defined.
        data (dict): Dictionary containing formulation specifications for imports/exports.
    
    Side Effects:
        Adds constraints to model:
        - model.SupplyBalance[h]: Hourly energy balance (equality)
        - model.GenMix_Share: Annual clean energy requirement (inequality)
    
    Returns:
        None
    
    Notes:
        GenMix_Target=0.8 means thermal generation limited to 20% of total demand.
    """
    if (get_formulation(data, component="Exports") != "NotModel") & (get_formulation(data, component="Imports") != "NotModel"):
        # Supply balance constraint
        model.SupplyBalance = Constraint(model.h, rule=imp_exp_supply_balance_rule)
    else:
        model.SupplyBalance = Constraint(model.h, rule=supply_balance_rule)
        
    
    # Generation mix share constraint
    model.GenMix_Share = Constraint(rule=genmix_share_rule)