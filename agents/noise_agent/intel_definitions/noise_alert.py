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