import json
import pandas as pd
from typing import List, Dict, Any

def generate_dataframe_content(columns: List[Dict[str, Any]], data: pd.DataFrame) -> str:
    """
    Generate a formatted content string from columns metadata and DataFrame data.
    
    Args:
        columns (List[Dict[str, Any]]): List of column metadata dictionaries
        data (pd.DataFrame): DataFrame containing the actual data
        
    Returns:
        str: Formatted content string in the required JSON format
    """
    # Convert DataFrame to list of dictionaries
    records = data.to_dict(orient='records')
    
    # Convert each record to the required format
    formatted_records = []
    for record in records:
        formatted_record = {}
        for col in columns:
            col_name = col['name']
            # display_name = col.get('display_name', col_name)  # Fallback to name if display_name not present
            if col_name in record:
                # Convert values to strings to match the example format
                formatted_record[col_name] = str(record[col_name])
        formatted_records.append(formatted_record)
    
    # Convert to JSON string as expected by the client
    content = json.dumps(formatted_records)
    
    return content