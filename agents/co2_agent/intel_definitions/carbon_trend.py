def analyze_carbon_trend(values):

    average = sum(values) / len(values)

    return {
        "average_co2": average
    }