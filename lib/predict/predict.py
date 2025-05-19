import pickle
import numpy as np
import pandas as pd
import math
import os

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

# Load model and scaler once when the module is imported
MODEL_PATH = os.path.join(ROOT_DIR, 'model.pkl')
SCALER_PATH = os.path.join(ROOT_DIR, 'scaler.pkl')

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
if not os.path.exists(SCALER_PATH):
    raise FileNotFoundError(f"Scaler file not found: {SCALER_PATH}")

with open(MODEL_PATH, 'rb') as f:
    model = pickle.load(f)

with open(SCALER_PATH, 'rb') as f:
    scaler = pickle.load(f)

def calculate_body_score(input_points_flat):
    """
    Calculates the body score based on 14 input points (28 float values).
    Args:
        input_points_flat (list): A flat list of 28 float values representing 14 (x,y) coordinates.
    Returns:
        float: The predicted body score.
    Raises:
        ValueError: If the input does not contain 28 values or if calculation errors occur.
        FileNotFoundError: If model or scaler files are not found (checked at module load).
    """
    if len(input_points_flat) != 28:
        raise ValueError("Expected 28 input values (14 (x,y) pairs).")

    # Extract 14 points (each consisting of 2 values)
    points = [(input_points_flat[i], input_points_flat[i + 1]) for i in range(0, 28, 2)]

    point_a = points[0]
    point_b = points[1]
    point_c = points[2]
    point_d = points[3]
    point_e = points[4]
    point_f = points[5]
    point_g = points[6]
    point_h = points[7]
    point_i = points[8]
    point_j = points[9]
    point_k = points[10] # Unused in current feature calculations
    point_l = points[11] # Unused in current feature calculations
    point_m = points[12]
    point_n = points[13]

    # Calculate features
    if (point_j[0] - point_i[0]) == 0:
        raise ValueError("Cannot calculate slope for 'laranja' segment: points have same x-coordinate.")
    declive_laranja = (point_j[1] - point_i[1]) / (point_j[0] - point_i[0])

    if (point_n[0] - point_m[0]) == 0:
        raise ValueError("Cannot calculate slope for 'verde' segment: points have same x-coordinate.")
    declive_verde = (point_n[1] - point_m[1]) / (point_n[0] - point_m[0])

    if declive_verde == 0:
        raise ValueError("Slope of 'verde' segment is zero, 'rel_laranja_verde' calculation is problematic.")
    rel_laranja_verde = declive_laranja / declive_verde

    tamanho_roxo = math.sqrt((point_b[0] - point_a[0])**2 + (point_b[1] - point_a[1])**2)
    tamanho_rosa = math.sqrt((point_d[0] - point_c[0])**2 + (point_d[1] - point_c[1])**2)
    tamanho_branco = math.sqrt((point_f[0] - point_e[0])**2 + (point_f[1] - point_e[1])**2)
    tamanho_azul = math.sqrt((point_h[0] - point_g[0])**2 + (point_h[1] - point_g[1])**2)
    tamanho_laranja = math.sqrt((point_j[0] - point_i[0])**2 + (point_j[1] - point_i[1])**2)

    if tamanho_laranja == 0: raise ValueError("'tamanho_laranja' is zero, cannot compute ratios.")
    if tamanho_branco == 0: raise ValueError("'tamanho_branco' is zero, cannot compute ratios.")
    if tamanho_azul == 0: raise ValueError("'tamanho_azul' is zero, cannot compute 'tam_branco_azul'.")

    tam_roxo_laranja = tamanho_roxo / tamanho_laranja
    tam_rosa_branco = tamanho_rosa / tamanho_branco
    tam_branco_azul = tamanho_branco / tamanho_azul
    tam_branco_laranja = tamanho_branco / tamanho_laranja

    result_features = [[rel_laranja_verde, tam_roxo_laranja, tam_rosa_branco, tam_branco_azul, tam_branco_laranja]]
    df_result = pd.DataFrame(result_features, columns=['rel_laranja_verde', 'tam_roxo_laranja',
                                          'tam_rosa_branco',
                                          'tam_branco_azul', 'tam_branco_laranja'])

    # Load model and scaler
    with open(os.path.join(ROOT_DIR, 'model.pkl'), 'rb') as f:
        model = pickle.load(f)

    # Scale input and predict
    input_scaled = scaler.transform(df_result.to_numpy())
    prediction = model.predict(input_scaled)

        # Ensure the prediction is a standard Python float
    return float(prediction[0])
