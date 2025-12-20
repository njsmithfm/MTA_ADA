import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
from dotenv import load_dotenv

load_dotenv()
DATAWRAPPER_TOKEN = os.environ.get('DATAWRAPPER_TOKEN')

def get_data_since_2019():
    url = "https://data.ny.gov/resource/rc78-7x78.json"
    
    # Get available months
    params = {
        "$select": "month",
        "$group": "month",
        "$order": "month DESC",
        "$limit": 12
    }
    months_response = requests.get(url, params=params)

    return pd.DataFrame(months_response)

months_response=get_data_since_2019
print(months_response)