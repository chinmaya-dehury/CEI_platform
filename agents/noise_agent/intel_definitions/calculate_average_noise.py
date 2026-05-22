def calculate_average_noise(noise_data):

    if not noise_data:

        return {
            "status": "error",
            "message": "No noise data available"
        }

    average = sum(noise_data) / len(noise_data)

    return {
        "status": "success",
        "average_noise": round(average, 2)
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Noise Average Analysis",

    "description": "Calculates average environmental noise levels",

    "category": "statistics",

    "function_name": "calculate_average_noise",

    "sample_data": [40, 50, 65, 80]
}