import requests
import pandas as pd
from datetime import datetime, timedelta

# Configuration
DATAWRAPPER_TOKEN = "your_token"
CHART_IDS = {
    'monday': 'chart_id_1',
    'tuesday': 'chart_id_2',
    'wednesday': 'chart_id_3',
    'thursday': 'chart_id_4',
    'friday': 'chart_id_5',
    'saturday': 'chart_id_6',
    'sunday': 'chart_id_7'
    
    # ... one for each day
}

def get_mta_data(date):
    """Fetch MTA data for a specific date"""
    url = "https://data.ny.gov/resource/thh2-syn7.json"
    params = {
        "$where": f"date='{date}'",
        "$limit": 5000
    }
    return pd.DataFrame(requests.get(url, params=params).json())

def calculate_operability(df):
    """Calculate % of ADA stations operational by borough"""
    results = []
    for borough in df['borough'].unique():
        borough_data = df[df['borough'] == borough]
        
        # Count operational (both directions working)
        operational = ((borough_data['ada_northbound'] == 'Y') & 
                      (borough_data['ada_southbound'] == 'Y')).sum()
        total = len(borough_data)
        
        results.append({
            'Borough': borough,
            'Operability Rate': round(operational / total * 100, 1)
        })
    
    return pd.DataFrame(results)

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
today = datetime.now()
days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

for i in range(7):
    date = (today - timedelta(days=6-i)).strftime('%Y-%m-%d')
    day_name = days[(today.weekday() - 6 + i) % 7]
    
    # Get and process data
    mta_data = get_mta_data(date)
    operability = calculate_operability(mta_data)
    
    # Update chart
    chart_id = CHART_IDS[day_name]
    title = f"{day_name.capitalize()} - {date}"
    update_datawrapper_chart(chart_id, operability, title)

print("All 7 charts updated!")