import pandas as pd
import os
import random

def generate_dummy_excel(filename, n_records=10):
    docentes = ["Juan Perez", "Maria Garcia", "Carlos Lopez", "Ana Martinez", "Luis Rodriguez"]
    facultades = ["Ingeniería", "Medicina", "Derecho", "Artes", "Ciencias"]
    
    data = {
        "Docente": [random.choice(docentes) for _ in range(n_records)],
        "Facultad": [random.choice(facultades) for _ in range(n_records)],
        "Metodología": [round(random.uniform(3.0, 5.0), 2) for _ in range(n_records)],
        "Puntualidad": [round(random.uniform(3.0, 5.0), 2) for _ in range(n_records)],
        "Dominio Temático": [round(random.uniform(3.0, 5.0), 2) for _ in range(n_records)],
        "Interacción": [round(random.uniform(3.0, 5.0), 2) for _ in range(n_records)],
        "Uso de TIC": [round(random.uniform(3.0, 5.0), 2) for _ in range(n_records)],
        "Satisfacción": [round(random.uniform(3.0, 5.0), 2) for _ in range(n_records)],
        "Promedio": [round(random.uniform(3.0, 5.0), 2) for _ in range(n_records)],
        "Observaciones": ["Excelente profesor" if i % 2 == 0 else "Podría mejorar la interacción" for i in range(n_records)]
    }
    
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(f"Archivo generado: {filename}")

if __name__ == "__main__":
    os.makedirs("encuestas", exist_ok=True)
    for i in range(5):
        generate_dummy_excel(f"encuestas/encuesta_{i+1}.xlsx")
