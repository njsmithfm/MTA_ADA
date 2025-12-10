import requests
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
from dotenv import load_dotenv

load_dotenv()
DATAWRAPPER_TOKEN = os.environ.get("DATAWRAPPER_TOKEN")

CHART_IDS = {0: "q0KSY", 1: "2Lebz", 2: "t7mwT", 3: "Ber6f", 4: "vaXUw", 5: "bYfxF"}


def get_available_months():
    """Fetch all available months and return the 6 most recent"""
    url = "https://data.ny.gov/resource/thh2-syn7.json"
    params = {
        "$select": "month",
        "$group": "month",
        "$order": "month DESC",
        "$limit": 6,
    }
    response = requests.get(url, params=params)
    months = [item["month"] for item in response.json()]
    return months


def get_mta_monthly_data(month):
    """Fetch MTA data for a specific month"""
    url = "https://data.ny.gov/resource/thh2-syn7.json"
    params = {"$where": f"month='{month}'", "$limit": 50}
    response = requests.get(url, params=params)
    return pd.DataFrame(response.json())


def calculate_availability_by_borough(df):
    """Format data for chart: Borough and Availability %"""
    df["availability_pct"] = (df["availability"].astype(float) * 100).round(1)

    result = df[["borough", "availability_pct"]].copy()
    result.columns = ["Borough", "Availability %"]

    return result


def update_datawrapper_chart(chart_id, data, title):
    """Update a Datawrapper chart"""
    headers = {"Authorization": f"Bearer {DATAWRAPPER_TOKEN}"}

    requests.put(
        f"https://api.datawrapper.de/v3/charts/{chart_id}/data",
        headers=headers,
        data=data.to_csv(index=False),
    )

    requests.patch(
        f"https://api.datawrapper.de/v3/charts/{chart_id}",
        headers=headers,
        json={"title": title},
    )

    requests.post(
        f"https://api.datawrapper.de/v3/charts/{chart_id}/publish", headers=headers
    )


# Main execution - get actual available months
months = get_available_months()
print(f"Found {len(months)} available months")

for i, month in enumerate(months):
    # Get data
    mta_data = get_mta_monthly_data(month)

    if mta_data.empty:
        print(f"No data for {month}")
        continue

    # Prepare chart data
    chart_data = calculate_availability_by_borough(mta_data)

    # Format month for title
    month_name = datetime.strptime(month, "%Y-%m-%dT00:00:00.000").strftime("%B %Y")

    # Update chart
    chart_id = CHART_IDS[i]
    update_datawrapper_chart(chart_id, chart_data, month_name)

    print(f"Updated chart {i+1}: {month_name}")

print("All 6 monthly charts updated!")
