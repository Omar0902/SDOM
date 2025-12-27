"""Energy storage formulations for the SDOM optimization model.

This module implements energy storage modeling including:
- Multiple storage technologies (Li-Ion, CAES, PHS, H2, etc.)
- Coupled vs. decoupled charge/discharge power sizing
- State-of-charge (SOC) balance with round-trip efficiency
- Duration constraints linking power and energy capacity
- Cycle life limitations

Storage provides temporal flexibility to balance renewable generation variability.
"""

from pyomo.core import Var, Constraint, Expression
from pyomo.environ import Set, Param, Binary, NonNegativeReals, sqrt
from ..constants import STORAGE_PROPERTIES_NAMES, MW_TO_KW
from .models_utils import crf_rule

def initialize_storage_sets(block, data: dict):
    """
    Initializes storage technology sets for the optimization model.
    
    Creates sets for:
    - All storage technologies (j): Technologies available for deployment
    - Coupled storage technologies (b ⊂ j): Technologies where charge and discharge
      power must be equal (e.g., Li-Ion batteries, pumped hydro)
    - Storage properties: Cost and performance parameters
    
    Args:
        block: Pyomo Block object (typically model.storage) where sets will be added.
        data (dict): Dictionary containing 'STORAGE_SET_J_TECHS' (list of all technologies),
            'STORAGE_SET_B_TECHS' (list of coupled technologies), derived from storage_data.
    
    Side Effects:
        Creates block attributes:
        - block.j (Set): All storage technologies
        - block.b (Set): Coupled storage technologies (subset of j)
        - block.properties_set (Set): Storage parameter names
    """
    block.j = Set( initialize = data['STORAGE_SET_J_TECHS'] )
    block.b = Set( within=block.j, initialize = data['STORAGE_SET_B_TECHS'] )
    
    # Initialize storage properties
    block.properties_set = Set( initialize = STORAGE_PROPERTIES_NAMES )
####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_storage_parameters(model, data: dict):
    """
    Adds storage technology parameters to the model.
    
    Initializes techno-economic parameters for each storage technology including:
    - Capital costs (power and energy capacity)
    - Operating costs (fixed and variable O&M)
    - Performance (efficiency, duration limits, maximum power)
    - Lifetime and cycling constraints
    - Financial parameters (discount rate, capital recovery factor)
    
    Args:
        model: The Pyomo ConcreteModel instance.
        data (dict): Dictionary containing 'storage_data' DataFrame with technology
            parameters and 'scalars' DataFrame with financial parameters.
    
    Side Effects:
        Adds parameters to model.storage block:
        - model.storage.MaxCycles[j]: Maximum lifetime cycles for technology j
        - model.storage.data[property, j]: Technology parameters (costs, efficiency, etc.)
        - model.storage.r: Discount rate
        - model.storage.CRF[j]: Capital Recovery Factor for annualizing capital costs
    """
    # Battery life and cycling
    max_cycles_dict = data['storage_data'].loc['MaxCycles'].to_dict()

    model.storage.MaxCycles = Param( model.storage.j,  initialize = max_cycles_dict )
    # Storage data initialization
    storage_dict = data["storage_data"].stack().to_dict()
    storage_tuple_dict = {(prop, tech): storage_dict[(prop, tech)] for prop in STORAGE_PROPERTIES_NAMES for tech in model.storage.j}
    model.storage.data = Param( model.storage.properties_set, model.storage.j, initialize = storage_tuple_dict )

    model.storage.r = Param( initialize = float(data["scalars"].loc["r"].Value) )  # Interest rate
    model.storage.CRF = Param( model.storage.j, initialize = crf_rule ) #Capital Recovery Factor -STORAGE

####################################################################################|
# ------------------------------------ Variables -----------------------------------|
####################################################################################|
def add_storage_variables(model):
    """
    Adds storage operation and capacity decision variables to the model.
    
    Creates variables for:
    - Hourly charging/discharging power (operational decisions)
    - State-of-charge tracking (energy inventory)
    - Installed power capacity (investment decisions: charge/discharge)
    - Installed energy capacity (investment decision: storage duration)
    - Binary variables for preventing simultaneous charge/discharge
    
    Args:
        model: The Pyomo ConcreteModel instance.
    
    Side Effects:
        Adds variables to model.storage block:
        - model.storage.PC[h,j]: Charging power in hour h for tech j (MW)
        - model.storage.PD[h,j]: Discharging power in hour h for tech j (MW)
        - model.storage.SOC[h,j]: State of charge in hour h for tech j (MWh)
        - model.storage.Pcha[j]: Installed charging capacity for tech j (MW)
        - model.storage.Pdis[j]: Installed discharging capacity for tech j (MW)
        - model.storage.Ecap[j]: Installed energy capacity for tech j (MWh)
        - model.storage.capacity_fraction[j,h]: Binary for charge/discharge control
    """
    # Charging power for storage technology j in hour h
    model.storage.PC = Var(model.h, model.storage.j, domain=NonNegativeReals, initialize=0)
    # Discharging power for storage technology j in hour h
    model.storage.PD = Var(model.h, model.storage.j, domain=NonNegativeReals, initialize=0)
    # State-of-charge for storage technology j in hour h
    model.storage.SOC = Var(model.h, model.storage.j, domain=NonNegativeReals, initialize=0)
    # Charging capacity for storage technology j
    model.storage.Pcha = Var(model.storage.j, domain=NonNegativeReals, initialize=0)
    # Discharging capacity for storage technology j
    model.storage.Pdis = Var(model.storage.j, domain=NonNegativeReals, initialize=0)
    # Energy capacity for storage technology j
    model.storage.Ecap = Var(model.storage.j, domain=NonNegativeReals, initialize=0)

    model.storage.capacity_fraction = Var(model.storage.j, model.h, domain=Binary, initialize=0)


####################################################################################|
# ----------------------------------- Expressions ----------------------------------|
####################################################################################|

def storage_power_capex_cost_expr_rule(block, j):
    """
    Calculates annualized power capacity capital costs for a storage technology.
    
    For technologies with decoupled charge/discharge power (e.g., flow batteries),
    costs depend on both charging and discharging capacity. The cost ratio determines
    the weighting between charge and discharge capacity costs.
    
    Args:
        block: The storage block containing parameters and variables.
        j: Storage technology index.
    
    Returns:
        Expression for annualized power capacity costs ($US/year).
    """
    return (   block.CRF[j] * (
                    MW_TO_KW * block.data['CostRatio', j] * block.data['P_Capex', j]*block.Pcha[j]
                    + MW_TO_KW * (1 - block.data['CostRatio', j]) * block.data['P_Capex', j]*block.Pdis[j]
                    )
                )

def storage_energy_capex_cost_expr_rule(block, j):
    """
    Calculates annualized energy capacity capital costs for a storage technology.
    
    Args:
        block: The storage block containing parameters and variables.
        j: Storage technology index.
    
    Returns:
        Expression for annualized energy capacity costs ($US/year).
    """
    return ( block.CRF[j] * ( MW_TO_KW *block.data['E_Capex', j]*block.Ecap[j] ) )

def storage_fixed_om_cost_expr_rule(block, j):
    """
    Calculates annual fixed O&M costs for a storage technology.
    
    Similar to power CAPEX, fixed O&M depends on installed charge and discharge
    capacity for decoupled technologies.
    
    Args:
        block: The storage block containing parameters and variables.
        j: Storage technology index.
    
    Returns:
        Expression for annual fixed O&M costs ($US/year).
    """
    return (    MW_TO_KW * block.data['CostRatio', j] * block.data['FOM', j]*block.Pcha[j]
                + MW_TO_KW * (1 - block.data['CostRatio', j]) * block.data['FOM', j]*block.Pdis[j]
                )

def _add_storage_expressions(block):
    block.power_capex_cost_expr = Expression(block.j, rule = storage_power_capex_cost_expr_rule )
    block.energy_capex_cost_expr = Expression(block.j, rule = storage_energy_capex_cost_expr_rule )
    block.capex_cost_expr = Expression(block.j,  rule = lambda m,j: m.power_capex_cost_expr[j] + m.energy_capex_cost_expr[j] )

    block.fixed_om_cost_expr = Expression(block.j,  rule = storage_fixed_om_cost_expr_rule )

    block.total_capex_cost = Expression( rule = sum( block.capex_cost_expr[j] for j in block.j ) )
    block.total_fixed_om_cost = Expression( rule = sum( block.fixed_om_cost_expr[j] for j in block.j ) )


def add_storage_expressions(model):
    """
    Adds cost expressions for storage technologies to the model.
    
    Creates Pyomo Expression objects that calculate various cost components for each
    storage technology. These expressions are evaluated during optimization and used
    in the objective function and results reporting.
    
    Args:
        model: The Pyomo ConcreteModel instance.
    
    Side Effects:
        Adds expressions to model.storage block:
        - model.storage.power_capex_cost_expr[j]: Annualized power capacity costs
        - model.storage.energy_capex_cost_expr[j]: Annualized energy capacity costs
        - model.storage.capex_cost_expr[j]: Total annualized CAPEX per technology
        - model.storage.fixed_om_cost_expr[j]: Annual fixed O&M per technology
        - model.storage.total_capex_cost: Sum of all storage CAPEX
        - model.storage.total_fixed_om_cost: Sum of all storage fixed O&M
    """
    _add_storage_expressions(model.storage)
     


####################################################################################|
# ----------------------------------- Add_costs -----------------------------------|
####################################################################################|
def add_storage_fixed_costs(model):
    """
    Calculates total annual fixed costs for all storage technologies.
    
    Fixed costs include annualized capital expenditures (CAPEX) for both power and
    energy capacity, plus annual fixed operation and maintenance (FOM) costs. These
    costs are independent of how much the storage is actually operated.
    
    Mathematical Formulation:
        $$C_{storage,fixed} = \sum_j (CAPEX_{power,j} + CAPEX_{energy,j} + FOM_j)$$
    
    Args:
        model: The Pyomo ConcreteModel instance with storage cost expressions defined.
    
    Returns:
        Expression: Total annual fixed costs for storage ($US/year).
    
    Notes:
        Used in the objective function as part of total system fixed costs.
    """
    return ( # Storage Capex and Fixed O&M
            model.storage.total_capex_cost  + model.storage.total_fixed_om_cost 
            )

def add_storage_variable_costs(model):
    """
    Calculates total annual variable costs for all storage technologies.
    
    Variable costs are proportional to energy throughput (discharge). They represent
    wear-and-tear costs that depend on how intensively the storage is operated.
    
    Mathematical Formulation:
        $$C_{storage,variable} = \sum_j \sum_h VOM_j \cdot PD_j(h)$$
    
    Where:
        - $VOM_j$: Variable O&M cost for technology j ($US/MWh)
        - $PD_j(h)$: Discharge power in hour h (MW)
    
    Args:
        model: The Pyomo ConcreteModel instance with storage variables and parameters.
    
    Returns:
        Expression: Total annual variable costs for storage ($US/year).
    
    Notes:
        Used in the objective function as part of total system variable costs.
    """
    return (
        sum( model.storage.data['VOM', j] * sum(model.storage.PD[h, j]
                  for h in model.h) for j in model.storage.j )
    )

####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|

# State-Of-Charge Balance -
def soc_balance_rule(model, h, j):
    """
    Defines the state-of-charge balance equation for energy storage.
    
    The SOC tracks the energy inventory in storage, accounting for:
    - Energy added through charging (with round-trip efficiency loss)
    - Energy removed through discharging (with round-trip efficiency loss)
    - Cyclical boundary condition (SOC at end of year = SOC at start)
    
    Mathematical Formulation:
        For h > 1:
        $$SOC_j(h) = SOC_j(h-1) + \sqrt{\eta_j} \cdot PC_j(h) - \frac{PD_j(h)}{\sqrt{\eta_j}}$$
        
        For h = 1 (cyclical condition):
        $$SOC_j(1) = SOC_j(H) + \sqrt{\eta_j} \cdot PC_j(1) - \frac{PD_j(1)}{\sqrt{\eta_j}}$$
    
    Where:
        - $SOC_j(h)$: State of charge for tech j in hour h (MWh)
        - $PC_j(h)$: Charging power for tech j in hour h (MW)
        - $PD_j(h)$: Discharging power for tech j in hour h (MW)
        - $\eta_j$: Round-trip efficiency (dimensionless, 0-1)
        - $H$: Total hours in simulation period
    
    Args:
        model: The Pyomo storage block.
        h: Hour index.
        j: Storage technology index.
    
    Returns:
        Pyomo constraint expression for SOC balance.
    """
    if h > 1: 
        return model.storage.SOC[h, j] == model.storage.SOC[h-1, j] \
            + sqrt(model.storage.data['Eff', j]) * model.storage.PC[h, j] \
            - model.storage.PD[h, j] / sqrt(model.storage.data['Eff', j])
    else:
        # cyclical or initial condition
        return model.storage.SOC[h, j] == model.storage.SOC[max(model.h), j] \
            + sqrt(model.storage.data['Eff', j]) * model.storage.PC[h, j] \
            - model.storage.PD[h, j] / sqrt(model.storage.data['Eff', j])

# Max cycle year
def max_cycle_year_rule(model, j):
    """
    Constrains annual energy throughput based on lifetime cycle limitations.
    
    Batteries and other storage technologies have finite cycle life. This constraint
    ensures that the average annual number of equivalent full cycles doesn't exceed
    the allowable rate based on expected lifetime.
    
    Mathematical Formulation:
        $$\sum_{h=1}^{H} PD_j(h) \leq \frac{MaxCycles_j}{Lifetime_j} \cdot Ecap_j$$
    
    Where:
        - $PD_j(h)$: Discharge in hour h (MW)
        - $MaxCycles_j$: Maximum lifetime cycles for technology j
        - $Lifetime_j$: Expected lifetime (years)
        - $Ecap_j$: Installed energy capacity (MWh)
        - Right side represents allowable annual energy throughput (MWh/year)
    
    Args:
        model: The Pyomo storage block.
        j: Storage technology index.
    
    Returns:
        Pyomo constraint expression limiting annual cycles.
    """
    n_steps = model.n_steps_modeled
    iterate = range(1, n_steps + 1)
    return sum(model.PD[h, j] for h in iterate) <= (model.MaxCycles[j] / model.data['Lifetime', j]) * model.Ecap[j]

def add_storage_constraints( model ):
    """
    Adds all operational and design constraints for energy storage technologies.
    
    This function creates a comprehensive set of constraints governing storage behavior:
    
    Operational constraints (hourly, for each technology j):
    - Charge/discharge power limits (≤ installed capacity)
    - Charge/discharge mutual exclusivity (binary variable)
    - SOC upper bound (≤ energy capacity)
    - SOC balance (charge/discharge accounting with efficiency)
    
    Design constraints (for each technology j):
    - Power capacity limits (min/max from technology data)
    - Coupled charge/discharge equality (for technologies in set b)
    - Duration constraints (min/max energy-to-power ratios)
    - Annual cycle life limits (cumulative throughput)
    
    Args:
        model: The Pyomo ConcreteModel instance with storage variables and parameters.
    
    Side Effects:
        Adds constraints to model.storage block and model root:
        - model.storage.ChargSt[h,j], DischargeSt[h,j]: Binary mutual exclusivity
        - model.storage.MaxHourlyCharging[h,j], MaxHourlyDischarging[h,j]: Capacity bounds
        - model.storage.MaxSOC[h,j]: State-of-charge limit
        - model.SOCBalance[h,j]: Energy balance equation
        - model.storage.MaxPcha[j], MaxPdis[j]: Technology power limits
        - model.storage.PchaPdis[j]: Coupled technology equality
        - model.storage.MinEcap[j], MaxEcap[j]: Duration constraints
        - model.storage.MaxCycleYear_constraint[j]: Cycle life constraint
    
    Returns:
        None
    """
    # Ensure that the charging and discharging power do not exceed storage limits
    model.storage.ChargSt= Constraint(model.h, model.storage.j, rule=lambda m, h, j: m.PC[h, j] <= m.data['Max_P', j] * m.capacity_fraction[j, h])
    model.storage.DischargeSt = Constraint(model.h, model.storage.j, rule=lambda m, h, j: m.PD[h, j] <= m.data['Max_P', j] * (1 - m.capacity_fraction[j, h]))

    # Hourly capacity bounds
    model.storage.MaxHourlyCharging = Constraint(model.h, model.storage.j, rule= lambda m,h,j: m.PC[h, j] <= m.Pcha[j])
    model.storage.MaxHourlyDischarging = Constraint(model.h, model.storage.j, rule= lambda m,h,j: m.PD[h, j] <= m.Pdis[j])

    # Limit state of charge of storage by its capacity
    model.storage.MaxSOC = Constraint(model.h, model.storage.j, rule=lambda m, h, j: m.SOC[h,j]<= m.Ecap[j])
    # SOC Balance Constraint
    model.SOCBalance = Constraint(model.h, model.storage.j, rule=soc_balance_rule)

    # - Constraints on the maximum charging (Pcha) and discharging (Pdis) power for each technology
    model.storage.MaxPcha = Constraint( model.storage.j, rule=lambda m, j: m.Pcha[j] <= m.data['Max_P', j] )
    model.storage.MaxPdis = Constraint( model.storage.j, rule=lambda m, j: m.Pdis[j] <= m.data['Max_P', j] )

    # Charge and discharge rates are equal -
    model.storage.PchaPdis = Constraint( model.storage.b, rule=lambda m, j: m.Pcha[j] == m.Pdis[j] )

    # Max and min energy capacity constraints (handle uninitialized variables)
    model.storage.MinEcap = Constraint(model.storage.j, rule= lambda m,j: m.Ecap[j] >= m.data['Min_Duration', j] * m.Pdis[j] / sqrt(m.data['Eff', j]))
    model.storage.MaxEcap = Constraint(model.storage.j, rule= lambda m,j: m.Ecap[j] <= m.data['Max_Duration', j] * m.Pdis[j] / sqrt(m.data['Eff', j]))


    model.storage.MaxCycleYear_constraint = Constraint( model.storage.j, rule=max_cycle_year_rule)