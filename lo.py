import pandas as pd
from datetime import datetime

def convert_date_str(date_str):
    """
    Convert a date string from the format '2024-04-15T09:04:24Z'
    to '2024-04-15 09:04:24+00:00'. If the date string is already in
    the target format, return it as-is.
    """
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
        return dt.strftime('%Y-%m-%d %H:%M:%S+00:00')
    except ValueError:
        # If conversion fails (e.g. the date is already converted), return it unchanged.
        return date_str

# Load the CSV file
df = pd.read_csv('data/videos.csv')

# Apply the conversion to the 'published_at' column
df['published_at'] = df['published_at'].apply(convert_date_str)

# Display the first few rows to verify changes
print(df['published_at'])
