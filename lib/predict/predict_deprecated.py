import sys
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as mp
import math
import os


ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

# Convert command-line arguments to floats, skipping the script name
input_values = [float(val) for val in sys.argv[1:]]

# Sanity check: ensure we have exactly 30 values
if len(input_values) != 28:
    raise ValueError("Expected 28 input values (14 pairs).")

# Extract 14 points (each consisting of 2 values)
points = [(input_values[i], input_values[i + 1]) for i in range(0, 28, 2)]

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
point_k = points[10]
point_l = points[11]
point_m = points[12]
point_n = points[13]


#'rel_laranja_verde',
#'tam_roxo_laranja',
#'tam_rosa_branco',
#'tam_branco_azul',
#'tam_branco_laranja',

declive_laranja = (point_j[1] - point_i[1] )/(point_j[0] - point_i[0] )
declive_verde = (point_n[1] - point_m[1] )/(point_n[0] - point_m[0] )

rel_laranja_verde = declive_laranja / declive_verde

tamanho_roxo = math.sqrt((point_b[0] - point_a[0])**2 + (point_b[1] - point_a[1])**2)
tamanho_rosa = math.sqrt((point_d[0] - point_c[0])**2 + (point_d[1] - point_c[1])**2)
tamanho_branco = math.sqrt((point_f[0] - point_e[0])**2 +(point_f[1] - point_e[1])**2)
tamanho_azul = math.sqrt((point_h[0] - point_g[0])**2 + (point_h[1] - point_g[1])**2)
tamanho_laranja = math.sqrt((point_j[0] - point_i[0])**2 + (point_j[1] - point_i[1])**2)

tam_roxo_laranja = tamanho_roxo / tamanho_laranja
tam_rosa_branco = tamanho_rosa / tamanho_branco
tam_branco_azul = tamanho_branco / tamanho_azul
tam_branco_laranja = tamanho_branco / tamanho_laranja

result = []

result.append([rel_laranja_verde, tam_roxo_laranja, tam_rosa_branco, tam_branco_azul, tam_branco_laranja])

df_result = pd.DataFrame(result, columns=['rel_laranja_verde', 'tam_roxo_laranja',
                                          'tam_rosa_branco',
                                          'tam_branco_azul', 'tam_branco_laranja'])

# Load model and scaler
with open(os.path.join(ROOT_DIR, 'model.pkl'), 'rb') as f:
    model = pickle.load(f)

with open(os.path.join(ROOT_DIR, 'scaler.pkl'), 'rb') as f:
    scaler = pickle.load(f)


# Scale input and predict
input_scaled = scaler.transform(df_result.to_numpy())
prediction = model.predict(input_scaled)

# Output result
print("Body Score:", prediction[0])
