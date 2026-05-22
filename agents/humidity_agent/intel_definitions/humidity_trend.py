def analyze_humidity_trend(humidity_data):

    if humidity_data[-1] > humidity_data[0]:

        trend = "Increasing"

    elif humidity_data[-1] < humidity_data[0]:

        trend = "Decreasing"

    else:

        trend = "Stable"

    return {
        "trend": trend
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Humidity Trend Intelligence",

    "description": "Analyzes humidity trends",

    "category": "analytics",

    "function_name": "analyze_humidity_trend",

    "sample_data": [50, 55, 60, 70]
}