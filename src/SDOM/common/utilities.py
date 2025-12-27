from pyomo.environ import value
import pandas as pd
import os
import logging

def safe_pyomo_value(var):
    """
    Safely extracts the value from a Pyomo variable or expression.
    
    This function attempts to retrieve the value of a Pyomo variable or expression,
    handling cases where the variable is uninitialized or None. It prevents crashes
    when accessing variables that haven't been assigned values.
    
    Args:
        var: A Pyomo variable, parameter, expression, or numeric value. Can be None.
    
    Returns:
        float or None: The numeric value if the variable is initialized and has a value,
            otherwise None.
    
    Examples:
        >>> capacity = safe_pyomo_value(model.storage.Pcha[j])
        >>> if capacity is not None:
        ...     print(f"Capacity: {capacity} MW")
    """
    try:
        return value(var) if var is not None else None
    except ValueError:
        return None
# Normalize base_name and file name for comparison: ignore spaces, "-", "_", and case
def normalize_string(name:str) -> str:
    """
    Normalizes a string for case-insensitive file name comparison.
    
    Removes spaces, hyphens, and underscores, then converts to lowercase for
    standardized string comparison when matching file names.
    
    Args:
        name (str): The string to normalize.
    
    Returns:
        str: Normalized string with spaces, hyphens, and underscores removed and
            converted to lowercase.
    
    Examples:
        >>> normalize_string("Load_hourly-2025.csv")
        'loadhourly2025.csv'
    """
    return name.replace(' ', '').replace('-', '').replace('_', '').lower()

def get_complete_path(filepath, file_name):
    """
    Searches for a CSV file in a directory using fuzzy name matching.
    
    This function performs case-insensitive, flexible file name matching by normalizing
    both the target filename and files in the directory. This allows matching files
    even when naming conventions vary slightly (e.g., spaces, hyphens, underscores).
    
    Args:
        filepath (str): Directory path where the file should be located.
        file_name (str): Base name of the file to search for (with or without .csv extension).
    
    Returns:
        str: Full path to the matched file if found, empty string otherwise.
    
    Examples:
        >>> path = get_complete_path("./Data/", "Load_hourly.csv")
        >>> if path:
        ...     data = pd.read_csv(path)
    """
    base_name, ext = os.path.splitext(file_name)
    if ext.lower() == '.csv':
        for f in os.listdir(filepath):
            normalized_f = normalize_string(f.split('.csv')[0])
            if normalized_f.startswith( normalize_string( base_name) ) and f.lower().endswith('.csv'):
                logging.debug(f"Found matching file: {f}")
                return os.path.join(filepath, f)
    
    return ""

def check_file_exists(filepath, file_name, file_description = ""):
    """
    Verifies that a required input file exists in the specified directory.
    
    This function searches for a file using fuzzy matching and raises an error if
    the file cannot be found. It's used during data loading to ensure all required
    input files are present before model initialization.
    
    Args:
        filepath (str): Directory path where the file should be located.
        file_name (str): Name of the file to check for.
        file_description (str, optional): Human-readable description of the file's 
            purpose (used in error messages). Defaults to "".
    
    Returns:
        str: Full path to the file if found.
    
    Raises:
        FileNotFoundError: If the specified file cannot be found in the directory.
    
    Examples:
        >>> path = check_file_exists("./Data/", "scalars.csv", "scalar parameters")
        >>> scalars = pd.read_csv(path)
    """
    input_file_path = get_complete_path(filepath, file_name)#os.path.join(filepath, file_name)

    if not os.path.isfile(input_file_path):
        logging.error(f"Expected {file_description} file not found: {filepath}{file_name}")
        raise FileNotFoundError(f"Expected {file_description} file not found: {filepath}{file_name}")

    return input_file_path

def compare_lists(list1, list2, text_comp='', list_names=['','']):
    """
    Compares two lists for length and element equality, logging warnings for differences.
    
    This validation function is used during data loading to ensure consistency between
    related datasets (e.g., capacity factor data and capacity data should reference the
    same set of plant IDs).
    
    Args:
        list1 (list): First list to compare.
        list2 (list): Second list to compare.
        text_comp (str, optional): Description of what's being compared (for logging). 
            Defaults to ''.
        list_names (list, optional): Names of the two lists [name1, name2] for logging. 
            Defaults to ['', ''].
    
    Returns:
        bool: True if lists have same length and elements, False otherwise.
    
    Examples:
        >>> cf_plants = ['plant1', 'plant2', 'plant3']
        >>> cap_plants = ['plant1', 'plant2']
        >>> compare_lists(cf_plants, cap_plants, 'solar plants', ['CF', 'Capacity'])
        False  # Logs warning about length difference
    """
    if len(list1) != len(list2):
        logging.warning(f"Lists {text_comp} have different lengths ({list_names[0]} vs {list_names[1]}): {len(list1)} vs {len(list2)}")
        return False
    if set(list1) != set(list2):
        logging.warning(f"Lists {text_comp} have different elements ({list_names[0]} vs {list_names[1]}): {set(list1)} vs {set(list2)}")
        return False
    return True

def concatenate_dataframes( df: pd.DataFrame, 
                           new_data_dict: dict, 
                           run = 1,
                           unit = '$US',
                           metric = ''
                        ):
    """Concatenates a new row of data to an existing pandas DataFrame.
                        This function takes an existing DataFrame and a dictionary containing new data,
                        adds metadata fields ('Run', 'Unit', 'Metric') to the dictionary, and appends
                        it as a new row to the DataFrame.
                        Parameters
                        ----------
                        df : pd.DataFrame
                            The DataFrame to which the new data will be appended.
                        new_data_dict : dict
                            Dictionary containing the new row data to be added.
                        run : int, optional
                            Identifier for the run; defaults to 1.
                        unit : str, optional
                            Unit of measurement; defaults to '$US'.
                        metric : str, optional
                            Metric name or description; defaults to an empty string.
                        Returns
                        -------
                        pd.DataFrame
                            The updated DataFrame with the new row appended."""
    new_df = pd.DataFrame.from_dict(new_data_dict, orient='index',columns=['Optimal Value'])
    new_df = new_df.reset_index(names=['Technology'])
    new_df['Run'] = run
    new_df['Unit'] = unit
    new_df['Metric'] = metric
    df = pd.concat([df, new_df], ignore_index=True)
    return df

def get_dict_string_void_list_from_keys_in_list(keys: list) -> dict:
    """
    Creates a dictionary with string keys initialized to empty lists.
    
    This utility function is used to initialize result dictionaries where each key
    will accumulate a list of values (e.g., hourly generation values for each plant).
    
    Args:
        keys (list): List of keys to use for the dictionary. Each key is converted to string.
    
    Returns:
        dict: Dictionary where each key from the input list maps to an empty list.
    
    Examples:
        >>> plants = ['plant1', 'plant2', 'plant3']
        >>> results = get_dict_string_void_list_from_keys_in_list(plants)
        >>> results
        {'plant1': [], 'plant2': [], 'plant3': []}
        >>> results['plant1'].append(150.5)  # Add generation value
    """
    generic_dict = {}
    for plant in keys:
        generic_dict[str(plant)] = []
    return generic_dict