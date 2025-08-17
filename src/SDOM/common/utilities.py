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

def compare_lists(list1, list2, text_comp='', list_names=['','']):
    """Compare two lists for length and element equality. Log warnings if they differ."""
    if len(list1) != len(list2):
        logging.warning(f"Lists {text_comp} have different lengths ({list_names[0]} vs {list_names[1]}): {len(list1)} vs {len(list2)}")
        return False
    if set(list1) != set(list2):
        logging.warning(f"Lists {text_comp} have different elements ({list_names[0]} vs {list_names[1]}): {set(list1)} vs {set(list2)}")
        return False
    return True