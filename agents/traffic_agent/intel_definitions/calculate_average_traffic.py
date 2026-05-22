def calculate_average_traffic(traffic_data):

    if not traffic_data:

        return {
            "status": "error",
            "message": "No traffic data available"
        }

    average = sum(traffic_data) / len(traffic_data)

    return {
        "average_traffic": round(average, 2)
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Traffic Average Analysis",

    "description": "Calculates average traffic density",

    "category": "statistics",

    "function_name": "calculate_average_traffic",

    "sample_data": [20, 35, 50, 70]
}