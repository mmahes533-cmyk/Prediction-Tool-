from flask import Flask, render_template, request

app = Flask(__name__)

CLAY_DATA = {
    "kaolin": {
        "drying_range": (3, 5),
        "firing_low": (2, 4),
        "firing_high": (4, 7),
    },
    "ball_clay": {
        "drying_range": (6, 10),
        "firing_low": (3, 6),
        "firing_high": (6, 9),
    },
    "stoneware": {
        "drying_range": (4, 7),
        "firing_low": (2, 4),
        "firing_high": (6, 8),
    },
}

CLAY_NAMES = {
    "kaolin": "Kaolin (China Clay)",
    "ball_clay": "Ball Clay",
    "stoneware": "Stoneware Clay",
}

HISTORY = []


def predict_shrinkage_and_risk(clay_type, water_content, firing_temp, heating_rate):
    data = CLAY_DATA[clay_type]

    low, high = data["drying_range"]
    water_factor = min(max((water_content - 15) / (30 - 15), 0), 1)
    drying_shrinkage = low + water_factor * (high - low)

    fl_low, fl_high = data["firing_low"]
    fh_low, fh_high = data["firing_high"]
    firing_low_avg = (fl_low + fl_high) / 2
    firing_high_avg = (fh_low + fh_high) / 2

    if firing_temp <= 1050:
        firing_shrinkage = firing_low_avg
    elif firing_temp >= 1250:
        firing_shrinkage = firing_high_avg
    else:
        temp_factor = (firing_temp - 1050) / (1250 - 1050)
        firing_shrinkage = firing_low_avg + temp_factor * (firing_high_avg - firing_low_avg)

    total_shrinkage = round(drying_shrinkage + firing_shrinkage, 2)

    risk_factors = []
    warnings = []

    if heating_rate > 5:
        risk_factors.append("fast heating rate may trap steam and cause cracking")
    elif heating_rate > 4:
        warnings.append("heating rate is approaching the 5°C/min danger threshold")

    if 550 <= firing_temp <= 600 and heating_rate > 3:
        risk_factors.append("passing through quartz inversion (573°C) too fast risks dunting")
    elif 500 <= firing_temp < 550 and heating_rate > 3:
        warnings.append("approaching quartz inversion point (573°C) — slow down heating rate soon")

    if 200 <= firing_temp <= 250 and heating_rate > 3:
        risk_factors.append("passing through cristobalite inversion (~226°C) too fast risks cracking")
    elif 150 <= firing_temp < 200 and heating_rate > 3:
        warnings.append("approaching cristobalite inversion point (~226°C) — slow down heating rate soon")

    if water_content > 25:
        risk_factors.append("high moisture content increases risk of steam explosion cracks")
    elif water_content > 20:
        warnings.append("moisture content is getting high (above 20%)")

    if risk_factors:
        risk = "High risk: " + "; ".join(risk_factors)
    elif warnings:
        risk = "Low risk, but caution: " + "; ".join(warnings)
    else:
        risk = "Low risk"

    return total_shrinkage, risk


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/predict', methods=['POST'])
def predict():
    clay_type = request.form['clay_type']
    compare_type = request.form.get('clay_type_compare', 'none')
    water_content = float(request.form['water_content'])
    firing_temp = float(request.form['firing_temp'])
    heating_rate = float(request.form['heating_rate'])

    errors = []
    if not (0 <= water_content <= 100):
        errors.append("Water content must be between 0 and 100%.")
    if not (0 <= firing_temp <= 1400):
        errors.append("Firing temperature should be between 0°C and 1400°C.")
    if not (0 < heating_rate <= 50):
        errors.append("Heating rate should be a positive number, typically under 50°C/min.")

    if errors:
        return render_template('error.html', errors=errors)

    shrinkage, risk = predict_shrinkage_and_risk(clay_type, water_content, firing_temp, heating_rate)

    compare_shrinkage = None
    compare_risk = None
    if compare_type != "none" and compare_type != clay_type:
        compare_shrinkage, compare_risk = predict_shrinkage_and_risk(
            compare_type, water_content, firing_temp, heating_rate
        )

    chart_temps = sorted(set(list(range(800, 1401, 50)) + [int(firing_temp)]))
    chart_shrinkages = [
        predict_shrinkage_and_risk(clay_type, water_content, t, heating_rate)[0]
        for t in chart_temps
    ]
    user_index = chart_temps.index(int(firing_temp))

    compare_chart_shrinkages = None
    if compare_shrinkage is not None:
        compare_chart_shrinkages = [
            predict_shrinkage_and_risk(compare_type, water_content, t, heating_rate)[0]
            for t in chart_temps
        ]

    HISTORY.append({
        "clay_type": CLAY_NAMES[clay_type],
        "water_content": water_content,
        "firing_temp": firing_temp,
        "heating_rate": heating_rate,
        "shrinkage": shrinkage,
        "risk": risk,
    })

    return render_template(
        'result.html',
        clay_name=CLAY_NAMES[clay_type],
        shrinkage=shrinkage,
        risk=risk,
        compare_name=CLAY_NAMES.get(compare_type) if compare_shrinkage is not None else None,
        compare_shrinkage=compare_shrinkage,
        compare_risk=compare_risk,
        chart_temps=chart_temps,
        chart_shrinkages=chart_shrinkages,
        compare_chart_shrinkages=compare_chart_shrinkages,
        user_index=user_index,
    )


@app.route('/history')
def history():
    return render_template('history.html', history=HISTORY)


if __name__ == '__main__':
    app.run(debug=True)