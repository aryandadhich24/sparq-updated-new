import csv
import io
from typing import List, Dict, Any

def generate_csv_response(data: List[Dict[str, Any]], fieldnames: List[str]) -> str:
    """
    Converts a list of dictionaries to a CSV formatted string.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in data:
        # Filter row to only include specified fieldnames and handle None
        filtered_row = {k: (row.get(k) if row.get(k) is not None else "") for k in fieldnames}
        writer.writerow(filtered_row)
    return output.getvalue()
