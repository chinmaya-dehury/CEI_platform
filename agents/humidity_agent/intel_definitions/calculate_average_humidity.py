def calculate_average_humidity(humidity_data):

    average = sum(humidity_data) / len(humidity_data)

    return {
        "average_humidity": round(average, 2)
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Humidity Average Analysis",

    "description": "Calculates average humidity",

    "category": "statistics",

    "function_name": "calculate_average_humidity",

    "sample_data": [50, 55, 60, 70]
}