def analyze_temperature_trend(temperature_data):

    if len(temperature_data) < 2:

        return {
            "status": "insufficient data"
        }

    if temperature_data[-1] > temperature_data[0]:

        trend = "Increasing"

    elif temperature_data[-1] < temperature_data[0]:

        trend = "Decreasing"

    else:

        trend = "Stable"

    return {
        "trend": trend
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Temperature Trend Intelligence",

    "description": "Analyzes temperature trends",

    "category": "analytics",

    "function_name": "analyze_temperature_trend",

    "sample_data": [25, 28, 30, 35]
}