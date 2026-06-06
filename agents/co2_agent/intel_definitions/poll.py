def detect_pollution(data):

    co2 = data["co2"]

    if co2 > 1000:
        status = "CRITICAL"
    elif co2 > 700:
        status = "HIGH"
    else:
        status = "NORMAL"

    return {
        "co2_level": co2,
        "status": status,
        "message": "CO2 level analyzed successfully"
    }