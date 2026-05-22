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