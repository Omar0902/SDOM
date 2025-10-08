from pyomo.core import Var, Constraint
from pyomo.environ import *
from .models_utils import get_filtered_ts_parameter_dict

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
    elif key_ts in ["price_imports", "cost_exports"]:
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
def add_generic_import_export_variables(block, *sets, domain=NonNegativeReals, initialize=0):
    block.variable = Var(*sets, domain=domain, initialize=initialize)
    return

def add_imports_variables(model):
    add_generic_import_export_variables(model.imports, model.h, domain=NonNegativeReals, initialize=0)
    return


def add_exports_variables(model):
    add_generic_import_export_variables(model.exports, model.h, domain=NonNegativeReals, initialize=0)
    return

####################################################################################|
# ----------------------------------- Expressions ----------------------------------|
####################################################################################|



####################################################################################|
# ----------------------------------- Constraints ----------------------------------|
####################################################################################|
def add_imports_constraints( model, data: dict ):
    return


def add_exports_constraints( model, data: dict ):
    return


####################################################################################|
# -----------------------------------= Add_costs -----------------------------------|
####################################################################################|