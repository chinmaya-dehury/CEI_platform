def calculate_average_co2(co2_data):

    if not co2_data:

        return {
            "status": "error",
            "message": "No CO2 data available"
        }

    average = sum(co2_data) / len(co2_data)

    return {
        "average_co2": round(average, 2)
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "CO2 Average Analysis",

    "description": "Calculates average CO2 levels from collected data",

    "category": "statistics",

    "function_name": "calculate_average_co2",

    "sample_data": [400, 420, 450, 480, 500]
}