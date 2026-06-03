def detect_temperature_anomaly(temperature):

    THRESHOLD = 45

    if temperature > THRESHOLD:

        return {
            "status": "alert",
            "message": "High temperature detected"
        }

    return {
        "status": "normal",
        "message": "Temperature is within safe range"
    }
if __name__ == "__main__":

    sample_temperature = 52

    result = detect_temperature_anomaly(sample_temperature)

    print(result)