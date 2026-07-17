import requests
import pandas as pd
import os
from dotenv import load_dotenv
from dateutil.relativedelta import relativedelta
from datetime import datetime

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

BOROUGH_ALIASES = {
    'M': 'Manhattan',
    'Manhattan': 'Manhattan',
    'Bk': 'Brooklyn',
    'Brooklyn': 'Brooklyn',
    'Q': 'Queens',
    'Queens': 'Queens',
    'Bx': 'Bronx',
    'Bronx': 'Bronx',
    'SI': 'Staten Island',
    'Staten Island': 'Staten Island',
    'Systemwide': 'Systemwide',
}

def get_last_12_months_data():
    """Fetch last 12 months of data for all boroughs"""
    url = "https://data.ny.gov/resource/thh2-syn7.json"

    cutoff_month = (datetime.utcnow().replace(day=1) - relativedelta(months=11)).strftime('%Y-%m-%dT00:00:00')

    params = {
        "$select": "month,borough,minutes_platforms_available,minutes_platforms_in_service,availability,platform_count",
        "$order": "month DESC, borough",
        "$limit": 100,
        "$where": f"month >= '{cutoff_month}'"
    }
    response = requests.get(url, params=params, timeout=60)
    response.raise_for_status()

    df = pd.DataFrame(response.json())
    df['borough'] = df['borough'].map(BOROUGH_ALIASES).fillna(df['borough'])

    return df

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
    """Prepare the systemwide series from all non-systemwide rows"""
    borough_rows = df[df['borough'] != 'Systemwide'].copy()
    borough_rows['month_date'] = pd.to_datetime(borough_rows['month'])
    borough_rows['minutes_platforms_available'] = pd.to_numeric(borough_rows['minutes_platforms_available'])
    borough_rows['minutes_platforms_in_service'] = pd.to_numeric(borough_rows['minutes_platforms_in_service'])

    systemwide = borough_rows.groupby('month_date', as_index=False)[
        ['minutes_platforms_available', 'minutes_platforms_in_service']
    ].sum()
    systemwide['availability_pct'] = (
        systemwide['minutes_platforms_available']
        .div(systemwide['minutes_platforms_in_service'])
        .mul(100)
        .round(1)
    )
    systemwide = systemwide.sort_values('month_date')

    result = systemwide[['month_date', 'availability_pct']].copy()
    result['month_date'] = result['month_date'].dt.strftime('%B %Y')
    result.columns = ['Month', 'Availability %']

    return result

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
        headers=headers,
        timeout=30,
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