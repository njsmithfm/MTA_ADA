import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
from dotenv import load_dotenv

load_dotenv()
DATAWRAPPER_TOKEN = os.environ.get('DATAWRAPPER_TOKEN')

# 6 chart IDs for 6 months
CHART_IDS = {
    0: 'CHART_ID_MONTH_1',  # Most recent month
    1: 'CHART_ID_MONTH_2',
    2: 'CHART_ID_MONTH_3',
    3: 'CHART_ID_MONTH_4',
    4: 'CHART_ID_MONTH_5',
    5: 'CHART_ID_MONTH_6'   # 6 months ago
}

DATAWRAPPER_TOKEN = os.environ.get('DATAWRAPPER_TOKEN')

def get_last_6_months():
    """Get list of last 6 month start dates"""
    today = datetime.now()
    months = []
    for i in range(6):
        month_date = today - relativedelta(months=i)
        # Format as YYYY-MM-01 for the API filter
        months.append(month_date.strftime('%Y-%m-01T00:00:00.000'))
    return months

def get_mta_monthly_data(month):
    """Fetch MTA data for a specific month"""
    url = "https://data.ny.gov/resource/thh2-syn7.json"
    params = {
        "$where": f"month='{month}'",
        "$limit": 5000
    }
    response = requests.get(url, params=params)
    return pd.DataFrame(response.json())

def calculate_availability_by_borough(df):
    """Format data for chart: Borough and Availability %"""
    df['availability_pct'] = (df['availability'].astype(float) * 100).round(1)
    
    result = df[['borough', 'availability_pct']].copy()
    result.columns = ['Borough', 'Availability %']
    
    return result

def update_datawrapper_chart(chart_id, data, title):
    """Update a Datawrapper chart"""
    headers = {"Authorization": f"Bearer {DATAWRAPPER_TOKEN}"}
    
    # Upload data
    requests.put(
        f"https://api.datawrapper.de/v3/charts/{chart_id}/data",
        headers=headers,
        data=data.to_csv(index=False)
    )
    
    # Update title
    requests.patch(
        f"https://api.datawrapper.de/v3/charts/{chart_id}",
        headers=headers,
        json={"title": title}
    )
    
    # Publish
    requests.post(
        f"https://api.datawrapper.de/v3/charts/{chart_id}/publish",
        headers=headers
    )

# Main execution
months = get_last_6_months()

for i, month in enumerate(months):
    # Get data
    mta_data = get_mta_monthly_data(month)
    
    if mta_data.empty:
        print(f"No data for {month}")
        continue
    
    # Prepare chart data
    chart_data = calculate_availability_by_borough(mta_data)
    
    # Format month for title (e.g., "November 2024")
    month_name = datetime.strptime(month, '%Y-%m-%dT00:00:00.000').strftime('%B %Y')
    
    # Update chart
    chart_id = CHART_IDS[i]
    update_datawrapper_chart(chart_id, chart_data, month_name)
    
    print(f"Updated chart {i+1}: {month_name}")

print("All 6 monthly charts updated!")