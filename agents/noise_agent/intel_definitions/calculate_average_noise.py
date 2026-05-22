def calculate_average_noise(noise_data):

    if not noise_data:

        return {
            "status": "error",
            "message": "No noise data available"
        }

    average = sum(noise_data) / len(noise_data)

    return {
        "average_noise": round(average, 2)
    }