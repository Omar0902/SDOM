from pyomo.environ import value
import pandas as pd
import os
import logging

def safe_pyomo_value(var):
    """Return the value of a variable or expression if it is initialized, else return None."""
    try:
        return value(var) if var is not None else None
    except ValueError:
        return None
# Normalize base_name and file name for comparison: ignore spaces, "-", "_", and case
def normalize_string(name:str) -> str:
    return name.replace(' ', '').replace('-', '').replace('_', '').lower()

def get_complete_path(filepath, file_name):

    base_name, ext = os.path.splitext(file_name)
    if ext.lower() == '.csv':
        for f in os.listdir(filepath):
            normalized_f = normalize_string(f.split('.csv')[0])
            if normalized_f.startswith( normalize_string( base_name) ) and f.lower().endswith('.csv'):
                logging.debug(f"Found matching file: {f}")
                return os.path.join(filepath, f)
    
    return ""

def check_file_exists(filepath, file_name, file_description = ""):
    """Check if the expected file exists. Raise FileNotFoundError if not."""
    
    input_file_path = get_complete_path(filepath, file_name)#os.path.join(filepath, file_name)

    if not os.path.isfile(input_file_path):
        logging.error(f"Expected {file_description} file not found: {filepath}{file_name}")
        raise FileNotFoundError(f"Expected {file_description} file not found: {filepath}{file_name}")

    return input_file_path

def compare_lists(list1, list2, text_comp='', list_names=['','']):
    """Compare two lists for length and element equality. Log warnings if they differ."""
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