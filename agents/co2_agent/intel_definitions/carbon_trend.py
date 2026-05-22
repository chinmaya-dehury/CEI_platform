def analyze_carbon_trend(co2_data):

    if len(co2_data) < 2:

        return {
            "status": "insufficient data"
        }

    if co2_data[-1] > co2_data[0]:

        trend = "Increasing"

    elif co2_data[-1] < co2_data[0]:

        trend = "Decreasing"

    else:

        trend = "Stable"

    return {
        "trend": trend
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Carbon Trend Intelligence",

    "description": "Analyzes long term CO2 trends",

    "category": "analytics",

    "function_name": "analyze_carbon_trend",

    "sample_data": [400, 420, 450, 480, 500]
}