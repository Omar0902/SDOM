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