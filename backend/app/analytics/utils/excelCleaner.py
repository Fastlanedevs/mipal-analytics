import pandas as pd
from typing import Union, Any

async def clean_excel_sheet_to_df(file_path: str, sheet_name: Union[str, int] = 0, **kwargs) -> pd.DataFrame:
    """
    Detect the header row in an Excel sheet and clean it by removing unnamed columns.
    Returns the cleaned data as a pandas DataFrame.
    
    Args:
        file_path (str): Path to the Excel file to clean
        sheet_name (Union[str, int], optional): Name or index of the sheet to clean. Defaults to 0 (the first sheet).
        **kwargs: Additional arguments to pass to pd.read_excel (e.g., nrows, usecols, etc.)
    
    Returns:
        pd.DataFrame: Cleaned DataFrame with header row and unnamed columns removed
    """
    # Read the file without a header to inspect the content first
    df_raw = pd.read_excel(file_path, header=None, sheet_name=sheet_name, **kwargs)

    header_row_index = None
    # Iterate over rows to find the first one that looks like a header
    for i, row in df_raw.iterrows():
        # A common heuristic: a header row has multiple text values.
        # We're looking for the first row with 2 or more string cells.
        string_cells = [cell for cell in row if isinstance(cell, str)]
        if len(string_cells) >= 2:
            header_row_index = i
            break

    if header_row_index is None:
        # If no header is found, we can't proceed.
        raise ValueError("Could not automatically detect a suitable header row.")

    # Reread the file, this time using the detected header row
    df = pd.read_excel(file_path, header=header_row_index, sheet_name=sheet_name, **kwargs)
    
    # Drop columns that are unnamed
    df = df.loc[:, ~df.columns.str.contains('^Unnamed', na=False)]

    return df

