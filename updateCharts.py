import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
from dotenv import load_dotenv

load_dotenv()
DATAWRAPPER_TOKEN = os.environ.get('DATAWRAPPER_TOKEN') or os.environ.get('Datawrapper_API')

# 5 chart IDs - one per borough + systemwide
CHART_IDS = {
    'Manhattan': '3wJkX',
    'Brooklyn': 'gcDaE',
    'Queens': 'cec6j',
    'Bronx': 'IJXO5',
    'Systemwide': 'aveGu'
}

def get_last_12_months_data():
    """Fetch last 12 months of data for all boroughs"""
    url = "https://data.ny.gov/resource/thh2-syn7.json"
    
    # Get available months
    params = {
        "$select": "month",
        "$group": "month",
        "$order": "month DESC",
        "$limit": 12
    }
    months_response = requests.get(url, params=params, timeout=30)
    months_response.raise_for_status()
    months = [item['month'] for item in months_response.json()]
    
    # Fetch data for all those months
    all_data = []
    for month in months:
        params = {
            "$where": f"month='{month}'",
            "$limit": 500
        }
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        all_data.extend(response.json())
    
    return pd.DataFrame(all_data)

def prepare_borough_timeseries(df, borough):
    """Prepare time series data for a specific borough"""
    borough_data = df[df['borough'] == borough].copy()
    borough_data['availability_pct'] = (borough_data['availability'].astype(float) * 100).round(1)
    borough_data['month_date'] = pd.to_datetime(borough_data['month'])
    borough_data = borough_data.sort_values('month_date')
    
    result = borough_data[['month_date', 'availability_pct']].copy()
    result['month_date'] = result['month_date'].dt.strftime('%B %Y')
    result.columns = ['Month', 'Availability %']
    
    return result

def prepare_systemwide_timeseries(df):
    """Prepare the systemwide series from the source's systemwide rows"""
    systemwide = df[df['borough'] == 'Systemwide'].copy()
    systemwide['availability_pct'] = systemwide['availability'].astype(float) * 100
    systemwide['month_date'] = pd.to_datetime(systemwide['month'])
    systemwide = systemwide.sort_values('month_date')
    systemwide['availability_pct'] = systemwide['availability_pct'].round(1)
    
    systemwide['month_date'] = systemwide['month_date'].dt.strftime('%B %Y')
    systemwide.columns = ['Month', 'Availability %']
    
    return systemwide

def update_datawrapper_chart(chart_id, data, title):
    """Update a Datawrapper chart"""
    if not DATAWRAPPER_TOKEN:
        raise RuntimeError("DATAWRAPPER_TOKEN is not set")

    headers = {"Authorization": f"Bearer {DATAWRAPPER_TOKEN}"}
    put_response = requests.put(
        f"https://api.datawrapper.de/v3/charts/{chart_id}/data",
        headers=headers,
        data=data.to_csv(index=False),
        timeout=30,
    )
    put_response.raise_for_status()

    patch_response = requests.patch(
        f"https://api.datawrapper.de/v3/charts/{chart_id}",
        headers=headers,
        json={"title": title},
        timeout=30,
    )
    patch_response.raise_for_status()

    publish_response = requests.post(
        f"https://api.datawrapper.de/v3/charts/{chart_id}/publish",
        headers=headers
        ,timeout=30
    )
    publish_response.raise_for_status()

# Main execution
print("Fetching last 12 months of MTA data...")
full_data = get_last_12_months_data()

boroughs = ['Manhattan', 'Brooklyn', 'Queens', 'Bronx']

# Update borough charts
for borough in boroughs:
    chart_data = prepare_borough_timeseries(full_data, borough)
    chart_id = CHART_IDS[borough]
    title = f"{borough}"
    update_datawrapper_chart(chart_id, chart_data, title)
    print(f"Updated {borough} chart")

# Update systemwide chart
systemwide_data = prepare_systemwide_timeseries(full_data)
chart_id = CHART_IDS['Systemwide']
title = "Systemwide"
update_datawrapper_chart(chart_id, systemwide_data, title)
print("Updated Systemwide chart")

print("All 5 line charts updated!")