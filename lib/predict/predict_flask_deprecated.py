from flask import Flask, request, jsonify
import pickle
import pandas as pd
import math
import os

app = Flask(__name__)

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

# Load model and scaler once at startup
with open(os.path.join(ROOT_DIR, 'model.pkl'), 'rb') as f:
    model = pickle.load(f)

with open(os.path.join(ROOT_DIR, 'scaler.pkl'), 'rb') as f:
    scaler = pickle.load(f)

@app.route("/predict", methods=["POST"])
def predict():
    data = request.json

    # Validate input
    if not data or "points" not in data:
        return jsonify({"error": "Missing 'points' key in JSON payload"}), 400

    input_values = data["points"]

    if not isinstance(input_values, list) or len(input_values) != 28:
        return jsonify({"error": "Expected a list of 28 float values (14 pairs)"}), 400

    try:
        input_values = [float(v) for v in input_values]
    except ValueError:
        return jsonify({"error": "All input values must be floats"}), 400

    # Build 14 (x, y) coordinate pairs
    points = [(input_values[i], input_values[i + 1]) for i in range(0, 28, 2)]
    (
        point_a, point_b, point_c, point_d, point_e, point_f, point_g,
        point_h, point_i, point_j, point_k, point_l, point_m, point_n
    ) = points

    # Compute features
    try:
        declive_laranja = (point_j[1] - point_i[1]) / (point_j[0] - point_i[0])
        declive_verde = (point_n[1] - point_m[1]) / (point_n[0] - point_m[0])
        rel_laranja_verde = declive_laranja / declive_verde

        tamanho_roxo = math.dist(point_a, point_b)
        tamanho_rosa = math.dist(point_c, point_d)
        tamanho_branco = math.dist(point_e, point_f)
        tamanho_azul = math.dist(point_g, point_h)
        tamanho_laranja = math.dist(point_i, point_j)

        tam_roxo_laranja = tamanho_roxo / tamanho_laranja
        tam_rosa_branco = tamanho_rosa / tamanho_branco
        tam_branco_azul = tamanho_branco / tamanho_azul
        tam_branco_laranja = tamanho_branco / tamanho_laranja
    except ZeroDivisionError:
        return jsonify({"error": "Division by zero in feature calculation"}), 400

    features = [[
        rel_laranja_verde, tam_roxo_laranja,
        tam_rosa_branco, tam_branco_azul, tam_branco_laranja
    ]]
    df_result = pd.DataFrame(features, columns=[
        'rel_laranja_verde', 'tam_roxo_laranja',
        'tam_rosa_branco', 'tam_branco_azul', 'tam_branco_laranja'
    ])

    # Scale and predict
    input_scaled = scaler.transform(df_result.to_numpy())
    prediction = model.predict(input_scaled)

    return jsonify({"body_score": float(prediction[0])})

if __name__ == "__main__":
    app.run(debug=True)
