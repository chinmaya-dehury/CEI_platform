def calculate_average_humidity(humidity_data):

    if not humidity_data:

        return {
            "status": "error",
            "message": "No humidity data available"
        }

    average = sum(humidity_data) / len(humidity_data)

    return {
        "average_humidity": round(average, 2)
    }