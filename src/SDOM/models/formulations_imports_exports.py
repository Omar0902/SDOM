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
    big_m_constant = 1e10
    _add_imports_exports_capacity_constraint(model.imports, model.h)
    add_import_export_binary_variable(model, big_m_constant)
    

    model.imp_net_load_constraint = Constraint(
        model.h,
        rule=lambda m, h: m.imports.variable[h] <= m.aux_imp_exp_binary_variable[h] * big_m_constant
    )

    #TODO How to generalize constraint of net load?
    # model.imports.aux_variable = Var(model.h, domain=NonNegativeReals, initialize=0)
    # model.imports.aux_net_load_constraint = Constraint(
    #     model.h, 
    #     rule=lambda m, h: m.aux_variable[h] >= model.net_load[h])
    return


def add_exports_constraints( model, data: dict ):
    big_m_constant = 1e10
    _add_imports_exports_capacity_constraint(model.exports, model.h)
    #TODO How to generalize constraint of net load? - > for thermal generation
    add_import_export_binary_variable(model, big_m_constant)

    model.exp_net_load_constraint = Constraint(
        model.h,
        rule=lambda m, h: m.exports.variable[h] <= ( 1 - m.aux_imp_exp_binary_variable[h] ) * big_m_constant
    )

    return


####################################################################################|
# -----------------------------------= Add_costs -----------------------------------|
####################################################################################|
def add_imports_exports_cost(model):
    return model.imports.total_cost_expr - model.exports.total_cost_expr