def detect_abnormal_noise(noise_value):

    THRESHOLD = 85

    if noise_value > THRESHOLD:

        return {
            "status": "alert",
            "message": "Abnormal noise level detected"
        }

    return {
        "status": "normal"
    }


INTELLIGENCE_INFO = {

    "intelligence_name": "Noise Alert Intelligence",

    "description": "Detects abnormal noise levels",

    "category": "environment",

    "function_name": "detect_abnormal_noise",

    "sample_data": 95
}