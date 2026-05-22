def detect_abnormal_temperature(temperature_value):

    THRESHOLD = 40

    if temperature_value > THRESHOLD:

        return {
            "status": "alert",
            "message": "Abnormal temperature detected"
        }

    return {
        "status": "normal"
    }