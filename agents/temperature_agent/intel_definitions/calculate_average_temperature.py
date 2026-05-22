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