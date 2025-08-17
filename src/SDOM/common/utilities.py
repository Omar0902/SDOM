from pyomo.environ import value
import os
import logging

def safe_pyomo_value(var):
    """Return the value of a variable or expression if it is initialized, else return None."""
    try:
        return value(var) if var is not None else None
    except ValueError:
        return None
    
def check_file_exists(filepath, name_file = ""):
    """Check if the expected file exists. Raise FileNotFoundError if not."""
    if not os.path.isfile(filepath):
        logging.error(f"Expected {name_file} file not found: {filepath}")
        raise FileNotFoundError(f"Expected {name_file} file not found: {filepath}")
        return False
    return True