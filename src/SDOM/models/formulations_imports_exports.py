"""Imports and exports formulations for international electricity trade.

This module implements cross-border electricity trade modeling including:
- Hourly import/export capacity limits (interconnection constraints)
- Time-varying electricity prices for imports and exports
- Binary logic to prevent simultaneous import/export
- Net load-based trade restrictions (imports when demand > generation)

Trade provides economic opportunities and system flexibility by accessing
external markets, but is subject to transmission capacity constraints.
"""

from pyomo.core import Var, Expression, Constraint
from pyomo.environ import *
from .models_utils import get_filtered_ts_parameter_dict
from ..io_manager import get_formulation

####################################################################################|
# ----------------------------------- Parameters -----------------------------------|
####################################################################################|

def add_import_export_ts_parameters( block, 
                                hourly_set, 
                                data: dict, 
                                key_ts: str,
                                key_col: str):
    # Time-series parameter data initialization
    filtered_selected_data = get_filtered_ts_parameter_dict(hourly_set, data, key_ts, key_col)
    if key_ts in ["cap_imports", "cap_exports"]:
        block.ts_capacity_parameter = Param( hourly_set, initialize = filtered_selected_data)
    elif key_ts in ["price_imports", "price_exports"]:
        block.ts_price_parameter = Param( hourly_set, initialize = filtered_selected_data)
    return


def add_imports_parameters(model, data: dict):
    add_import_export_ts_parameters( model.imports, model.h, data, "cap_imports", "Imports")
    add_import_export_ts_parameters( model.imports, model.h, data, "price_imports", "Imports_price")
    return

def add_exports_parameters(model, data: dict):
    add_import_export_ts_parameters( model.exports, model.h, data, "cap_exports", "Exports")
    add_import_export_ts_parameters( model.exports, model.h, data, "price_exports", "Exports_price")
    return



####################################################################################|
# ------------------------------------ Variables -----------------------------------|
####################################################################################|
def _add_generic_import_export_variables(block, *sets, domain=NonNegativeReals, initialize=0):
    block.variable = Var(*sets, domain=domain, initialize=initialize)
    return

def add_imports_variables(model):
    _add_generic_import_export_variables(model.imports, model.h, domain=NonNegativeReals, initialize=0)
    return


def add_exports_variables(model):
    _add_generic_import_export_variables(model.exports, model.h, domain=NonNegativeReals, initialize=0)
    return

####################################################################################|
# ----------------------------------- Expressions ----------------------------------|
####################################################################################|
def _add_imports_exports_cost_expressions(block, hourly_set, data: dict, component: str):
    if get_formulation(data, component=component) != "NotModel":
        block.total_cost_expr = Expression( rule = sum(block.ts_price_parameter[h] * block.variable[h] for h in hourly_set) )
    else:
        block.total_cost_expr = Expression( rule = 0 )
    return

def add_imports_exports_cost_expressions(model, data: dict):
   
    _add_imports_exports_cost_expressions(model.imports, model.h, data, 'Imports')
    _add_imports_exports_cost_expressions(model.exports, model.h, data, 'Exports')
    return


####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|
def _add_imports_exports_capacity_constraint(block, hourly_set):
    block.capacity_constraint = Constraint(hourly_set, rule=lambda m,h: m.variable[h] <= m.ts_capacity_parameter[h] )
    return

def add_import_export_binary_variable(model, big_m_constant):

    if hasattr(model, 'aux_imp_exp_binary_variable'):
        return
    
    model.aux_imp_exp_binary_variable = Var(model.h, domain=Binary, initialize=0)
    
    model.imp_exp_aux_bigM_constraint_positive = Constraint(
        model.h,
        rule=lambda m, h: m.net_load[h] <= big_m_constant * m.aux_imp_exp_binary_variable[h]
    )
    model.imp_exp_aux_bigM_constraint_negative = Constraint(
        model.h,
        rule=lambda m, h: - m.net_load[h] + 1e-6 <= big_m_constant * (1 - m.aux_imp_exp_binary_variable[h])
    )
    return

 
def add_imports_constraints( model, data: dict ):
    big_m_constant = 1e6 #TODO make a logic to get Big M constant from input data/parameters
    _add_imports_exports_capacity_constraint(model.imports, model.h)
    add_import_export_binary_variable(model, big_m_constant)
    

    model.imp_net_load_constraint = Constraint(
        model.h,
        rule=lambda m, h: m.imports.variable[h] <= m.aux_imp_exp_binary_variable[h] * model.demand.ts_parameter[h]
    )
    return


def add_exports_constraints( model, data: dict ):
    big_m_constant = 1e6 #TODO make a logic to get Big M constant from input data/parameters
    _add_imports_exports_capacity_constraint(model.exports, model.h)

    add_import_export_binary_variable(model, big_m_constant)
    max_capacity_exports = max( model.exports.ts_capacity_parameter[h] for h in model.h )
    model.exp_net_load_constraint = Constraint(
        model.h,
        rule=lambda m, h: m.exports.variable[h] <= ( 1 - m.aux_imp_exp_binary_variable[h] ) * max_capacity_exports
    )
    return


####################################################################################|
# -----------------------------------= Add_costs -----------------------------------|
####################################################################################|
def add_imports_exports_cost(model):
    """
    Calculates net annual costs for cross-border electricity imports and exports.
    
    This function computes the difference between total import costs (money paid
    to buy electricity from neighbors) and export revenues (money earned by selling
    electricity to neighbors). A positive value indicates net import costs, while
    a negative value indicates net export revenues.
    
    Mathematical Formulation:
        $$C_{net,trade} = C_{imports} - R_{exports}$$
        $$C_{imports} = \sum_h Price_{import}(h) \cdot Import(h)$$
        $$R_{exports} = \sum_h Price_{export}(h) \cdot Export(h)$$
    
    Where:
        - $Price_{import}(h)$: Import price in hour h ($US/MWh)
        - $Import(h)$: Quantity imported in hour h (MW)
        - $Price_{export}(h)$: Export price in hour h ($US/MWh)
        - $Export(h)$: Quantity exported in hour h (MW)
    
    Args:
        model: The Pyomo ConcreteModel instance with import/export cost expressions.
    
    Returns:
        Expression: Net annual trade costs ($US/year). Positive = net importer,
                   negative = net exporter.
    
    Notes:
        - Used in the objective function to account for cross-border trade economics
        - Import and export prices typically follow different market dynamics
        - Binary constraint ensures imports and exports don't occur simultaneously
    """
    return model.imports.total_cost_expr - model.exports.total_cost_expr