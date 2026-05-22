def calculate_average_temperature(temperature_data):

    if not temperature_data:

        return {
            "status": "error",
            "message": "No temperature data available"
        }

    average = sum(temperature_data) / len(temperature_data)

    return {
        "average_temperature": round(average, 2)
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Temperature Average Analysis",

    "description": "Calculates average temperature values",

    "category": "statistics",

    "function_name": "calculate_average_temperature",

    "sample_data": [25, 28, 30, 35]
}