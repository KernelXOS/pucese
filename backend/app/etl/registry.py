"""
Tabla de verdad del sistema: mapeo completo de instrumentos y períodos.
Cualquier cambio en la estructura de evaluación se refleja aquí, no en el código.
"""

# ── PERÍODOS ──────────────────────────────────────────────────────────────────
PERIODOS = [
    {"codigo": "202301", "nombre": "MEIPA 2023 - I Período",  "sistema": "meipa", "anio": "2023", "numero": "01", "label_corto": "2023-I"},
    {"codigo": "202302", "nombre": "MEIPA 2023 - II Período", "sistema": "meipa", "anio": "2023", "numero": "02", "label_corto": "2023-II"},
    {"codigo": "202401", "nombre": "MEIPA 2024 - I Período",  "sistema": "meipa", "anio": "2024", "numero": "01", "label_corto": "2024-I"},
    {"codigo": "202402", "nombre": "360  2024 - II Período",  "sistema": "360",   "anio": "2024", "numero": "02", "label_corto": "2024-II"},
    {"codigo": "202501", "nombre": "360  2025 - I Período",   "sistema": "360",   "anio": "2025", "numero": "01", "label_corto": "2025-I"},
    {"codigo": "202502", "nombre": "360  2025 - II Período",  "sistema": "360",   "anio": "2025", "numero": "02", "label_corto": "2025-II"},
]

# ── INSTRUMENTOS ──────────────────────────────────────────────────────────────
# cod_instrumento → modelo, tipo_evaluador, peso_en_modelo, descripción
INSTRUMENTOS = [
    {
        "cod": "01",
        "descripcion": "Autoevaluación docente grado-tec",
        "modelo": "docencia",
        "tipo_evaluador": "auto",
        "peso_en_modelo": "20",
        "pesos_componentes": {"auto": 20},
    },
    {
        "cod": "02",
        "descripcion": "Evaluación de pares docente",
        "modelo": "docencia",
        "tipo_evaluador": "pares",
        "peso_en_modelo": "20",
        "pesos_componentes": {"pares": 20},
    },
    {
        "cod": "03",
        "descripcion": "Evaluación entorno virtual / aula",
        "modelo": "docencia",
        "tipo_evaluador": "hetero_dir",
        "peso_en_modelo": "10",
        "pesos_componentes": {"cev": 10},
    },
    {
        "cod": "05",
        "descripcion": "Autoevaluación docente ABP / IDIS / DocServ",
        "modelo": "abp",
        "tipo_evaluador": "auto",
        "peso_en_modelo": "20",
        "pesos_componentes": {"auto": 20},
    },
    {
        "cod": "08",
        "descripcion": "Autoevaluación docente posgrado",
        "modelo": "posgrado",
        "tipo_evaluador": "auto",
        "peso_en_modelo": "30",
        "pesos_componentes": {"auto": 30},
    },
    {
        "cod": "10",
        "descripcion": "Autoevaluación docente investigación",
        "modelo": "investigacion",
        "tipo_evaluador": "auto",
        "peso_en_modelo": "20",
        "pesos_componentes": {"auto": 20},
    },
    {
        "cod": "11",
        "descripcion": "Director investigación → docente investigación",
        "modelo": "investigacion",
        "tipo_evaluador": "hetero_dir",
        "peso_en_modelo": "50",
        "pesos_componentes": {"het_dir": 50},
    },
    {
        "cod": "12",
        "descripcion": "Par docente investigación",
        "modelo": "investigacion",
        "tipo_evaluador": "pares",
        "peso_en_modelo": "15",
        "pesos_componentes": {"pares": 15},
    },
    {
        "cod": "13",
        "descripcion": "Coordinador investigación → docente",
        "modelo": "investigacion",
        "tipo_evaluador": "hetero_dir",
        "peso_en_modelo": "15",
        "pesos_componentes": {"het_dir_coord": 15},
    },
    {
        "cod": "14",
        "descripcion": "Autoevaluación docente vinculación",
        "modelo": "vinculacion",
        "tipo_evaluador": "auto",
        "peso_en_modelo": "20",
        "pesos_componentes": {"auto": 20},
    },
    {
        "cod": "15",
        "descripcion": "Coordinador → docente vinculación",
        "modelo": "vinculacion",
        "tipo_evaluador": "hetero_dir",
        "peso_en_modelo": "30",
        "pesos_componentes": {"het_dir": 30},
    },
    {
        "cod": "16",
        "descripcion": "Autoevaluación docente gestión",
        "modelo": "gestion",
        "tipo_evaluador": "auto",
        "peso_en_modelo": "20",
        "pesos_componentes": {"auto": 20},
    },
    {
        "cod": "17",
        "descripcion": "Director → docente gestión",
        "modelo": "gestion",
        "tipo_evaluador": "hetero_dir",
        "peso_en_modelo": "50",
        "pesos_componentes": {"het_dir": 50},
    },
    {
        "cod": "018",
        "descripcion": "Docentes → evaluación al coordinador",
        "modelo": "gestion",
        "tipo_evaluador": "hetero_est",
        "peso_en_modelo": "30",
        "pesos_componentes": {"het_est": 30},
    },
]

# ── PESOS POR MODELO (cómo combinar instrumentos → puntaje final) ────────────
# Cada modelo define qué tipos de instrumento contribuyen y con qué peso
PESOS_MODELO = {
    "docencia": {
        "het_est": 50,   # instrumento estudiantes (het. estudiantil)
        "pares":   20,
        "cev":     10,
        "auto":    20,
    },
    "abp": {
        "het_est": 50,
        "pares":   20,
        "cev":     10,
        "auto":    20,
    },
    "tecnologado": {
        "het_est": 50,
        "pares":   20,
        "cev":     10,
        "auto":    20,
    },
    "posgrado": {
        "het_est": 60,
        "auto":    30,
        "cev":     10,
    },
    "investigacion": {
        "het_dir": 50,   # director investigación
        "auto":    20,
        "pares":   15,
        "het_dir_coord": 15,   # coordinador
    },
    "vinculacion": {
        "het_est": 50,
        "auto":    20,
        "het_dir": 30,
    },
    "gestion": {
        "het_dir":  50,   # director
        "het_est":  30,   # docentes (instrumento 018)
        "auto":     20,
    },
}

# ── ARCHIVOS POR PERÍODO ──────────────────────────────────────────────────────
# Mapeo de archivo → cod_instrumento para los períodos 360
ARCHIVO_INSTRUMENTO_360 = {
    # Nombre base (sin período) → cod_instrumento
    "01_autoeval_grado":             "01",
    "02_eval_par_doc":               "02",
    "03_eval_aulas_virt":            "03",
    "05_autoeval_doc_abp_idis_docserv": "05",
    "08_autoeval_posgrado":          "08",
    "10_autoeval_invest":            "10",
    "11_dirinv_invest":              "11",
    "12_par_invest":                 "12",
    "13_coordInv_invest":            "13",
    "14_autoeval_vinc":              "14",
    "15_coord_al_docvinc":           "15",
    "16_autoeval_docgest":           "16",
    "17_direc_al_docgest":           "17",
    "018_eval_docen_al_cordinador":  "018",
    # Variante detallada (202501, 202502)
    "Eval_doc_202501_01_detallada":  "01",
    "Eval_doc_202501_02_detallada":  "02",
    "Eval_doc_202501_03_detallada":  "03",
    "Eval_doc_202501_05_detallada":  "05",
    "Eval_doc_202501_08_detallada":  "08",
    "Eval_doc_202501_10_detallada":  "10",
    "Eval_doc_202501_11_detallada":  "11",
    "Eval_doc_202501_12_detallada":  "12",
    "Eval_doc_202501_13_detallada":  "13",
    "Eval_doc_202501_14_detallada":  "14",
    "Eval_doc_202501_15_detallada":  "15",
    "Eval_doc_202501_16_detallada":  "16",
    "Eval_doc_202501_17_detallada":  "17",
    "Eval_doc_202501_170_detallada": "17",
    "Eval_doc_202501_004_detallada": "018",
    "Eval_doc_202502_01_detallada":  "01",
    "Eval_doc_202502_02_detallada":  "02",
    "Eval_doc_202502_03_detallada":  "03",
    "Eval_doc_202502_05_detallada":  "05",
    "Eval_doc_202502_08_detallada":  "08",
    "Eval_doc_202502_10_detallada":  "10",
    "Eval_doc_202502_11_detallada":  "11",
    "Eval_doc_202502_12_detallada":  "12",
    "Eval_doc_202502_13_detallada":  "13",
    "Eval_doc_202502_14_detallada":  "14",
    "Eval_doc_202502_15_detallada":  "15",
    "Eval_doc_202502_16_detallada":  "16",
    "Eval_doc_202502_17_detallada":  "17",
    "Eval_doc_202502_170_detallada": "17",
    "Eval_doc_202502_004_detallada": "018",
}

# Mapeo de unidad organizativa → facultad normalizada
FACULTAD_MAP = {
    "CONTABILIDAD":        "Ciencias Administrativas",
    "ADMINISTRACION":      "Ciencias Administrativas",
    "ADMINISTRACI":        "Ciencias Administrativas",
    "TURISMO":             "Turismo y Hotelería",
    "HOTELERIA":           "Turismo y Hotelería",
    "HOTELERÍA":           "Turismo y Hotelería",
    "MEDICINA":            "Medicina",
    "LABORATORIO CLINICO": "Medicina",
    "LABORATORIO CL":      "Medicina",
    "ENFERMERIA":          "Salud",
    "ENFERMERÍA":          "Salud",
    "NUTRICION":           "Salud",
    "NUTRICIÓN":           "Salud",
    "PSICOLOGIA":          "Psicología",
    "PSICOLOGÍA":          "Psicología",
    "DERECHO":             "Derecho",
    "INGENIERIA":          "Ingeniería",
    "INGENIERÍA":          "Ingeniería",
    "SISTEMAS":            "Ingeniería",
    "COMPUTACION":         "Ingeniería",
    "COMPUTACIÓN":         "Ingeniería",
    "EDUCACION":           "Educación",
    "EDUCACIÓN":           "Educación",
    "AGRO":                "Agroindustria",
    "PUCETEC":             "Tecnologado",
    "TECNOLOGADO":         "Tecnologado",
    "POSGRADO":            "Posgrado",
    "MAESTRIA":            "Posgrado",
    "MAESTRÍA":            "Posgrado",
}


def map_facultad(texto: str) -> str:
    if not texto:
        return "Otras Ciencias"
    t = str(texto).upper().strip()
    for k, v in FACULTAD_MAP.items():
        if k in t:
            return v
    return "Otras Ciencias"


def nivel_from_puntaje(p) -> str:
    if p is None:
        return "Sin datos"
    if p >= 90:
        return "Excelente"
    if p >= 75:
        return "Bueno"
    if p >= 60:
        return "Regular"
    return "Deficiente"
