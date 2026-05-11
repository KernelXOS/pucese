"""
construir_datos_reales_v2.py
Construye encuesta_facultad_0..4.xlsx desde RESULTADO GENERAL 202402 MECDI 1.xlsx
y RESULTADOS GENERALES CONSOLIDADO 202301 al 202401 1.xlsx con TODOS los campos reales.
"""

import pandas as pd
import numpy as np
import os
import math
import warnings
warnings.filterwarnings('ignore')

DATOS_DIR = 'C:/Users/KernelXos/Desktop/DATOS_DOCENTE/'
ENC_DIR   = 'C:/Users/KernelXos/evaluacion-docente-ia/encuestas/'
MECDI_FILE = DATOS_DIR + 'RESULTADO GENERAL 202402 MECDI 1.xlsx'
CONSOL_FILE = DATOS_DIR + 'RESULTADOS GENERALES CONSOLIDADO 202301 al 202401 1.xlsx'

os.makedirs(ENC_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def parse_sex(s):
    s = str(s).strip().upper()
    if 'MUJ' in s or s in ('F', 'FEMENINO'): return 'Femenino'
    if 'HOM' in s or s in ('M', 'MASCULINO'): return 'Masculino'
    return None

def nivel_desempeno(p):
    """Nivel sobre 100 puntos."""
    if pd.isna(p): return 'Sin datos'
    if p >= 90: return 'Excelente'
    if p >= 75: return 'Bueno'
    if p >= 60: return 'Regular'
    return 'Deficiente'

CARRERA_FACULTAD = {
    # Ciencias Administrativas
    'CONTABILIDAD Y AUDITORIA CPA':         'Ciencias Administrativas',
    'ADMINISTRACION DE EMPRESAS':           'Ciencias Administrativas',
    'ADMINISTRACIÓN DE EMPRESAS':      'Ciencias Administrativas',
    'FINANZAS':                             'Ciencias Administrativas',
    # Salud
    'LABORATORIO CLINICO':                  'Salud',
    'LABORATORIO CLÍNICO':             'Salud',
    'LABORATORIO CLÍNICO.':            'Salud',
    'ENFERMERIA':                           'Salud',
    'ENFERMERÍA':                      'Salud',
    'FISIOTERAPIA':                         'Salud',
    'BIOQUIMICA Y FARMACIA':                'Salud',
    'BIOQUÍMICA Y FARMACIA':           'Salud',
    # Medicina
    'MEDICINA':                             'Medicina',
    'ODONTOLOGIA':                          'Medicina',
    'ODONTOLOGÍA':                     'Medicina',
    # Ingeniería
    'SISTEMAS Y COMPUTACION':              'Ingeniería',
    'SISTEMAS Y COMPUTACIÓN':         'Ingeniería',
    'SOFTWARE':                            'Ingeniería',
    'TECNOLOGIAS DE LA INFORMACION':       'Ingeniería',
    'TECNOLOGÍAS DE LA INFORMACIÓN': 'Ingeniería',
    'INGENIERIA EN SOFTWARE':              'Ingeniería',
    'INGENIERÍA EN SOFTWARE':         'Ingeniería',
    # Educación
    'EDUCACION INICIAL':                    'Educación',
    'EDUCACIÓN INICIAL':               'Educación',
    'EDUCACION BASICA':                     'Educación',
    'IDIOMAS':                              'Educación',
    # Psicología
    'PSICOLOGIA':                           'Psicología',
    'PSICOLOGÍA':                      'Psicología',
    'TRABAJO SOCIAL':                       'Psicología',
    # Turismo
    'HOTELERIA Y TURISMO':                  'Turismo y Hotelería',
    'HOTELERÍA Y TURISMO':             'Turismo y Hotelería',
    'TURISMO':                              'Turismo y Hotelería',
    # Derecho
    'DERECHO':                              'Derecho',
    # Agroindustria
    'AGROINDUSTRIA':                        'Agroindustria',
    'GASTRONOMIA':                          'Agroindustria',
    'GASTRONOMÍA':                     'Agroindustria',
}

def map_facultad(carrera):
    if pd.isna(carrera):
        return 'Sin Facultad'
    c = str(carrera).strip().upper()
    for k, v in CARRERA_FACULTAD.items():
        if k.upper() in c:
            return v
    # Fuzzy fallback
    if any(x in c for x in ['CONTAB', 'ADMIN', 'EMPR', 'FINANZ', 'AUDIT']):
        return 'Ciencias Administrativas'
    if any(x in c for x in ['LAB', 'ENFER', 'FISIO', 'BIOQU', 'FARMAC']):
        return 'Salud'
    if any(x in c for x in ['MEDIC', 'ODONT']):
        return 'Medicina'
    if any(x in c for x in ['SISTEM', 'SOFTW', 'TECNO', 'COMPUT', 'INFORM']):
        return 'Ingeniería'
    if any(x in c for x in ['EDUC', 'PEDAGO', 'IDIOM', 'BSICA']):
        return 'Educación'
    if any(x in c for x in ['PSICO', 'SOCIAL']):
        return 'Psicología'
    if any(x in c for x in ['HOTEL', 'TURIS']):
        return 'Turismo y Hotelería'
    if any(x in c for x in ['DERECH', 'JURID', 'LEGAL']):
        return 'Derecho'
    if any(x in c for x in ['AGRO', 'ALIMENT', 'GASTRO', 'CULIN']):
        return 'Agroindustria'
    return 'Otras Ciencias'

# ─────────────────────────────────────────────────────────────────────────────
# 1. LEER MECDI (202402) — FUENTE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
print("1. Leyendo RESULTADO GENERAL 202402 MECDI...")

xl = pd.ExcelFile(MECDI_FILE)

# Sheet 1 has demographics (Carrera, Edad, Genero...) + some rows without scores
# Sheets 2-4 have the actual component scores but no Carrera
# Strategy: merge Sheet 1 demographics with scores from sheets 2-4

def clean_cedula(s):
    return str(s).strip().split('.')[0].lstrip('0')

# Read demographics from Sheet 1
df_demo = xl.parse('Sheet 1', header=3)
df_demo = df_demo.dropna(axis=1, how='all')
df_demo['cedula'] = df_demo['evaluado'].apply(clean_cedula)
df_demo = df_demo[df_demo['cedula'].notna() & (df_demo['cedula'] != '') & (df_demo['cedula'] != 'nan')]
# Keep only demographic + base columns from sheet1
DEMO_COLS = ['cedula', 'periodo_evaluacion', 'apellidos_eval', 'nombres_eval',
             'Edad', 'Tiempo de Servicio', 'Genero', 'Nivel de estudio', 'Grado',
             'Modalidad de Trabajo', 'Carrera',
             'docgrado_autoeval_docgen', 'docgrado_evalpar_docgen',
             'docgrado_het_est_al_docgen', 'docgrado_aulavir_docgen',
             'total_grado', 'resultado']
df_demo_sel = df_demo[[c for c in DEMO_COLS if c in df_demo.columns]].copy()
print(f"   Sheet 1: {len(df_demo_sel)} filas, {df_demo_sel['cedula'].nunique()} docentes")

# Read score sheets (2-4), keep scores columns
score_sheets_dfs = []
for sheet in ['Sheet 1 (2)', 'Sheet 1 (3)', 'Sheet 1 (4)']:
    if sheet not in xl.sheet_names:
        continue
    df_s = xl.parse(sheet, header=3)
    df_s = df_s.dropna(axis=1, how='all')
    df_s['cedula'] = df_s['evaluado'].apply(clean_cedula)
    df_s = df_s[df_s['cedula'].notna() & (df_s['cedula'] != '') & (df_s['cedula'] != 'nan')]
    # De-duplicate cedula within each sheet
    df_s = df_s.drop_duplicates(subset=['cedula'], keep='last')
    SCORE_COLS = ['cedula', 'periodo_evaluacion', 'apellidos_eval', 'nombres_eval',
                  'docgrado_autoeval_docgen', 'docgrado_evalpar_docgen',
                  'docgrado_het_est_al_docgen', 'docgrado_aulavir_docgen',
                  'total_grado', 'resultado']
    df_s_sel = df_s[[c for c in SCORE_COLS if c in df_s.columns]].copy()
    score_sheets_dfs.append(df_s_sel)
    print(f"   {sheet}: {len(df_s_sel)} filas, {df_s_sel['cedula'].nunique()} docentes")

# Merge: start with demo, then enrich with scores from other sheets
# Sheet 1 already has scores for some docentes (those in docgrado mode)
# The other sheets may have different/overlapping sets
all_scores_dfs = score_sheets_dfs
if all_scores_dfs:
    # Concat all score sheets, de-dup by cedula (keep last = most recent)
    df_scores = pd.concat(all_scores_dfs, ignore_index=True)
    df_scores = df_scores.drop_duplicates(subset=['cedula'], keep='last')
    print(f"   All score sheets combined: {len(df_scores)} docentes")

    # Merge scores INTO demo on cedula (scores override if demo has zeros/NaN for score cols)
    score_only_cols = [c for c in df_scores.columns if c not in ('cedula', 'apellidos_eval', 'nombres_eval', 'periodo_evaluacion')]
    df_mecdi = df_demo_sel.merge(df_scores[['cedula'] + score_only_cols], on='cedula', how='outer', suffixes=('', '_new'))

    # For each score column, if _new exists take it when original is NaN/0
    for col in score_only_cols:
        if col + '_new' in df_mecdi.columns:
            mask = df_mecdi[col].isna() | (df_mecdi[col] == 0)
            df_mecdi.loc[mask, col] = df_mecdi.loc[mask, col + '_new']
            df_mecdi.drop(columns=[col + '_new'], inplace=True)

    # Fill names from scores sheet for docentes not in demo
    for name_col in ['apellidos_eval', 'nombres_eval', 'periodo_evaluacion']:
        if name_col + '_new' in df_mecdi.columns:
            mask = df_mecdi[name_col].isna()
            df_mecdi.loc[mask, name_col] = df_mecdi.loc[mask, name_col + '_new']
            df_mecdi.drop(columns=[name_col + '_new'], inplace=True, errors='ignore')
else:
    df_mecdi = df_demo_sel

df_mecdi = df_mecdi[df_mecdi['cedula'].notna() & (df_mecdi['cedula'] != '') & (df_mecdi['cedula'] != 'nan')]
df_mecdi = df_mecdi.drop_duplicates(subset=['cedula'], keep='last')

print(f"   MECDI TOTAL: {len(df_mecdi)} docentes unicos")

# ─────────────────────────────────────────────────────────────────────────────
# 2. LEER CONSOLIDADO HISTÓRICO (202301-202401)
# ─────────────────────────────────────────────────────────────────────────────
print("2. Leyendo CONSOLIDADO HISTÓRICO 202301-202401...")

df_hist = pd.read_excel(CONSOL_FILE, sheet_name='Worksheet', header=0)
df_hist.columns = [str(c).strip() for c in df_hist.columns]

# Rename columns for compatibility
hist_rename = {
    'Cédula': 'cedula',
    'C\xc3\xa9dula': 'cedula',
    'C?dula': 'cedula',
    'Período Evaluado': 'periodo_evaluacion',
    'Per?odo Evaluado': 'periodo_evaluacion',
    'Apellidos y Nombres': 'apellidos_nombres',
    'Estud a Doc': 'het_est_hist',
    'Autoeval': 'autoeval_hist',
    'Coord a Docente': 'evalpar_hist',
    'Eval pares': 'evalpar2_hist',
    'Total sobre 5': 'total5_hist',
    'TOTAL SOBRE 100': 'total100_hist',
    'Nivel de estudio': 'nivel_estudio',
    'Modalidad de Trabajo': 'modalidad',
}
# Apply renaming only for columns that exist
actual_rename = {k: v for k, v in hist_rename.items() if k in df_hist.columns}
df_hist = df_hist.rename(columns=actual_rename)

# Also handle encoding-garbled column names
for col in df_hist.columns:
    if 'dula' in col.lower() and 'cedula' not in col.lower():
        df_hist = df_hist.rename(columns={col: 'cedula'})
        break

df_hist['cedula'] = df_hist['cedula'].astype(str).str.strip().str.lstrip('0').str.split('.').str[0]
df_hist = df_hist[df_hist['cedula'].notna() & (df_hist['cedula'] != '') & (df_hist['cedula'] != 'nan')]

print(f"   Histórico total filas: {len(df_hist)}, docentes únicos: {df_hist['cedula'].nunique()}")

# ─────────────────────────────────────────────────────────────────────────────
# 3. CONSTRUIR MASTER DESDE MECDI (prioridad) + ENRIQUECER CON HISTÓRICO
# ─────────────────────────────────────────────────────────────────────────────
print("3. Construyendo master dataset...")

# De-duplicate MECDI: keep last (most recent sheet)
df_mecdi_dedup = df_mecdi.drop_duplicates(subset=['cedula'], keep='last').copy()

# ─── Columnas clave de MECDI ──────────────────────────────────────────────
def safe_num(df, col, default=0.0):
    if col in df.columns:
        return pd.to_numeric(df[col], errors='coerce').fillna(default)
    return pd.Series([default] * len(df), index=df.index)

# Componentes reales sobre 100
df_mecdi_dedup['het_estudiantil'] = safe_num(df_mecdi_dedup, 'docgrado_het_est_al_docgen')
df_mecdi_dedup['eval_pares']      = safe_num(df_mecdi_dedup, 'docgrado_evalpar_docgen')
df_mecdi_dedup['aula_virtual']    = safe_num(df_mecdi_dedup, 'docgrado_aulavir_docgen')
df_mecdi_dedup['autoevaluacion_raw'] = safe_num(df_mecdi_dedup, 'docgrado_autoeval_docgen')

# Normalizar autoevaluacion: si max > 10, dividir entre 2 (llega a 20 en algunos casos)
auto_max = df_mecdi_dedup['autoevaluacion_raw'].max()
if auto_max > 10:
    print(f"   Autoevaluacion max={auto_max:.2f} > 10, normalizando /2")
    df_mecdi_dedup['autoevaluacion'] = (df_mecdi_dedup['autoevaluacion_raw'] / 2).round(2)
else:
    df_mecdi_dedup['autoevaluacion'] = df_mecdi_dedup['autoevaluacion_raw'].round(2)

# Puntaje total: usar 'resultado' si existe, sino sumar componentes
if 'resultado' in df_mecdi_dedup.columns:
    df_mecdi_dedup['puntaje_100'] = safe_num(df_mecdi_dedup, 'resultado')
    # Rellenar zeros con suma de componentes
    mask_zero = df_mecdi_dedup['puntaje_100'] == 0
    df_mecdi_dedup.loc[mask_zero, 'puntaje_100'] = (
        df_mecdi_dedup.loc[mask_zero, 'het_estudiantil'] +
        df_mecdi_dedup.loc[mask_zero, 'eval_pares'] +
        df_mecdi_dedup.loc[mask_zero, 'aula_virtual'] +
        df_mecdi_dedup.loc[mask_zero, 'autoevaluacion']
    )
else:
    df_mecdi_dedup['puntaje_100'] = (
        df_mecdi_dedup['het_estudiantil'] +
        df_mecdi_dedup['eval_pares'] +
        df_mecdi_dedup['aula_virtual'] +
        df_mecdi_dedup['autoevaluacion']
    )

df_mecdi_dedup['puntaje_100'] = df_mecdi_dedup['puntaje_100'].round(2)

# Variables derivadas en escala 5 (para compatibilidad)
df_mecdi_dedup['metodologia']      = (df_mecdi_dedup['het_estudiantil'] / 50 * 5).round(2)
df_mecdi_dedup['dominio_tematico'] = (df_mecdi_dedup['autoevaluacion'] / 10 * 5).round(2)
df_mecdi_dedup['interaccion']      = (df_mecdi_dedup['eval_pares'] / 20 * 5).round(2)
df_mecdi_dedup['uso_tic']          = (df_mecdi_dedup['aula_virtual'] / 20 * 5).round(2)
df_mecdi_dedup['puntualidad']      = 0.0  # no hay dato específico
df_mecdi_dedup['satisfaccion']     = df_mecdi_dedup[['metodologia','dominio_tematico','interaccion','uso_tic']].mean(axis=1).round(2)
df_mecdi_dedup['promedio']         = (df_mecdi_dedup['puntaje_100'] / 100 * 5).round(2)

# Nombre docente
df_mecdi_dedup['docente_nombre'] = (
    df_mecdi_dedup['apellidos_eval'].str.title().str.strip() + ' ' +
    df_mecdi_dedup['nombres_eval'].str.title().str.strip()
)

# Sexo
df_mecdi_dedup['sexo'] = df_mecdi_dedup['Genero'].apply(parse_sex)

# Edad, Carrera, Tiempo de Servicio, Nivel de Estudio, Grado, Modalidad
for src, dst in [
    ('Edad',               'edad'),
    ('Carrera',            'carrera'),
    ('Tiempo de Servicio', 'tiempo_servicio'),
    ('Nivel de estudio',   'nivel_estudio'),
    ('Grado',              'grado'),
    ('Modalidad de Trabajo','modalidad'),
    ('periodo_evaluacion', 'periodo'),
]:
    if src in df_mecdi_dedup.columns:
        df_mecdi_dedup[dst] = df_mecdi_dedup[src]
    else:
        df_mecdi_dedup[dst] = None

df_mecdi_dedup['edad'] = pd.to_numeric(df_mecdi_dedup['edad'], errors='coerce')

# Facultad desde carrera
df_mecdi_dedup['facultad'] = df_mecdi_dedup['carrera'].apply(map_facultad)

# Nivel desempeño
df_mecdi_dedup['nivel_desempeno'] = df_mecdi_dedup['puntaje_100'].apply(nivel_desempeno)

# Observaciones
obs_map = {
    'Excelente':  'Excelente desempeño docente — referente de calidad institucional',
    'Bueno':      'Buen desempeño docente — cumple estándares académicos',
    'Regular':    'Desempeño regular — requiere plan de mejora',
    'Deficiente': 'Requiere plan de mejoramiento urgente',
    'Sin datos':  '',
}
df_mecdi_dedup['observaciones'] = df_mecdi_dedup['nivel_desempeno'].map(obs_map).fillna('')

# ─────────────────────────────────────────────────────────────────────────────
# 4. ENRIQUECER CON HISTÓRICO (para docentes que NO están en MECDI 202402)
# ─────────────────────────────────────────────────────────────────────────────
print("4. Enriqueciendo con datos históricos...")

# Docentes en histórico pero NO en MECDI
cedulas_mecdi = set(df_mecdi_dedup['cedula'].astype(str))
df_hist_new = df_hist[~df_hist['cedula'].astype(str).isin(cedulas_mecdi)].copy()

if len(df_hist_new) > 0:
    print(f"   {len(df_hist_new)} docentes históricos adicionales")

    # Construir columnas para df_hist_new
    # Histórico tiene TOTAL SOBRE 100 directamente
    if 'total100_hist' in df_hist_new.columns:
        df_hist_new['puntaje_100'] = pd.to_numeric(df_hist_new['total100_hist'], errors='coerce').fillna(0)
    elif 'total5_hist' in df_hist_new.columns:
        df_hist_new['puntaje_100'] = (pd.to_numeric(df_hist_new['total5_hist'], errors='coerce').fillna(0) / 5 * 100).round(2)
    else:
        df_hist_new['puntaje_100'] = 0.0

    # Histórico no tiene componentes separados sobre 100, usar proporciones
    # het_est_hist: sobre 1.84 max (aprox 2) -> normalizar a 50
    if 'het_est_hist' in df_hist_new.columns:
        h = pd.to_numeric(df_hist_new['het_est_hist'], errors='coerce').fillna(0)
        df_hist_new['het_estudiantil'] = (h / h.max() * 50).round(2) if h.max() > 0 else 0.0
    else:
        df_hist_new['het_estudiantil'] = 0.0

    if 'evalpar_hist' in df_hist_new.columns or 'evalpar2_hist' in df_hist_new.columns:
        ep_col = 'evalpar_hist' if 'evalpar_hist' in df_hist_new.columns else 'evalpar2_hist'
        ep = pd.to_numeric(df_hist_new[ep_col], errors='coerce').fillna(0)
        df_hist_new['eval_pares'] = (ep / ep.max() * 20).round(2) if ep.max() > 0 else 0.0
    else:
        df_hist_new['eval_pares'] = 0.0

    if 'autoeval_hist' in df_hist_new.columns:
        ae = pd.to_numeric(df_hist_new['autoeval_hist'], errors='coerce').fillna(0)
        df_hist_new['autoevaluacion'] = (ae / ae.max() * 10).round(2) if ae.max() > 0 else 0.0
    else:
        df_hist_new['autoevaluacion'] = 0.0

    df_hist_new['aula_virtual'] = 0.0

    # Nombres: histórico tiene columna 'Apellidos y Nombres' o 'apellidos_nombres'
    if 'apellidos_nombres' in df_hist_new.columns:
        df_hist_new['docente_nombre'] = df_hist_new['apellidos_nombres'].str.title().str.strip()
    elif 'Apellidos y Nombres' in df_hist_new.columns:
        df_hist_new['docente_nombre'] = df_hist_new['Apellidos y Nombres'].str.title().str.strip()
    else:
        df_hist_new['docente_nombre'] = 'Docente Histórico'

    df_hist_new['sexo'] = df_hist_new['Genero'].apply(parse_sex) if 'Genero' in df_hist_new.columns else None
    df_hist_new['edad'] = pd.to_numeric(df_hist_new.get('Edad', pd.Series([None]*len(df_hist_new))), errors='coerce')
    df_hist_new['carrera'] = df_hist_new.get('Carrera', pd.Series([None]*len(df_hist_new)))
    df_hist_new['tiempo_servicio'] = df_hist_new.get('Tiempo de Servicio', pd.Series([None]*len(df_hist_new)))
    df_hist_new['nivel_estudio'] = df_hist_new.get('nivel_estudio', df_hist_new.get('Nivel de estudio', pd.Series([None]*len(df_hist_new))))
    df_hist_new['grado'] = df_hist_new.get('Grado', pd.Series([None]*len(df_hist_new)))
    df_hist_new['modalidad'] = df_hist_new.get('modalidad', df_hist_new.get('Modalidad de Trabajo', pd.Series([None]*len(df_hist_new))))
    df_hist_new['periodo'] = df_hist_new.get('periodo_evaluacion', pd.Series(['202301']*len(df_hist_new)))

    df_hist_new['facultad'] = df_hist_new['carrera'].apply(map_facultad)
    df_hist_new['promedio'] = (df_hist_new['puntaje_100'] / 100 * 5).round(2)
    df_hist_new['metodologia'] = (df_hist_new['het_estudiantil'] / 50 * 5).round(2)
    df_hist_new['dominio_tematico'] = (df_hist_new['autoevaluacion'] / 10 * 5).round(2)
    df_hist_new['interaccion'] = (df_hist_new['eval_pares'] / 20 * 5).round(2)
    df_hist_new['uso_tic'] = 0.0
    df_hist_new['puntualidad'] = 0.0
    df_hist_new['satisfaccion'] = df_hist_new[['metodologia','dominio_tematico','interaccion']].mean(axis=1).round(2)
    df_hist_new['nivel_desempeno'] = df_hist_new['puntaje_100'].apply(nivel_desempeno)
    df_hist_new['observaciones'] = df_hist_new['nivel_desempeno'].map(obs_map).fillna('')

# ─────────────────────────────────────────────────────────────────────────────
# 5. COMBINAR Y DE-DUPLICAR
# ─────────────────────────────────────────────────────────────────────────────
FINAL_COLS = [
    'cedula', 'docente_nombre', 'facultad', 'periodo', 'sexo', 'edad',
    'carrera', 'tiempo_servicio', 'nivel_estudio', 'grado', 'modalidad',
    'het_estudiantil', 'eval_pares', 'aula_virtual', 'autoevaluacion', 'puntaje_100',
    'metodologia', 'puntualidad', 'dominio_tematico', 'interaccion', 'uso_tic',
    'satisfaccion', 'promedio', 'nivel_desempeno', 'observaciones',
]

def select_cols(df, cols):
    avail = [c for c in cols if c in df.columns]
    missing = [c for c in cols if c not in df.columns]
    result = df[avail].copy()
    for m in missing:
        result[m] = None
    return result[cols]

df_main = select_cols(df_mecdi_dedup, FINAL_COLS)

if len(df_hist_new) > 0:
    df_hist_sel = select_cols(df_hist_new, FINAL_COLS)
    df_all = pd.concat([df_main, df_hist_sel], ignore_index=True)
else:
    df_all = df_main

# De-duplicar por cedula: keep='last' (los más recientes de MECDI ya están primero)
df_all = df_all.drop_duplicates(subset=['cedula'], keep='last').reset_index(drop=True)

print(f"\n   Master final: {len(df_all)} docentes únicos")
print(f"   Con puntaje_100 > 0: {(df_all['puntaje_100'] > 0).sum()}")
print(f"   Facultades: {sorted(df_all['facultad'].dropna().unique())}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. CONSTRUIR ARCHIVO FINAL CON HEADERS QUE EL ETL RECONOCE
# ─────────────────────────────────────────────────────────────────────────────
print("\n6. Construyendo archivos encuesta_facultad_*.xlsx...")

df_out = pd.DataFrame()
df_out['Docente']                      = df_all['docente_nombre']
df_out['Facultad']                     = df_all['facultad']
df_out['Periodo']                      = df_all['periodo'].astype(str).str.strip()
df_out['Sexo']                         = df_all['sexo'].fillna('No registrado')
df_out['Edad']                         = df_all['edad'].apply(lambda x: int(x) if pd.notna(x) and x > 0 else None)
df_out['Carrera']                      = df_all['carrera'].fillna('')
df_out['Tiempo de Servicio']           = df_all['tiempo_servicio'].fillna('')
df_out['Nivel de Estudio']             = df_all['nivel_estudio'].fillna('')
df_out['Grado']                        = df_all['grado'].fillna('')
df_out['Modalidad']                    = df_all['modalidad'].fillna('')
df_out['Heteroevaluación Estudiantil'] = df_all['het_estudiantil'].round(2)
df_out['Evaluación de Pares']          = df_all['eval_pares'].round(2)
df_out['Aula Virtual']                 = df_all['aula_virtual'].round(2)
df_out['Autoevaluación']               = df_all['autoevaluacion'].round(2)
df_out['Puntaje Total']                = df_all['puntaje_100'].round(2)
df_out['Nivel Desempeño']              = df_all['nivel_desempeno']
df_out['Metodología']                  = df_all['metodologia'].round(2)
df_out['Puntualidad']                  = df_all['puntualidad'].round(2)
df_out['Dominio Temático']             = df_all['dominio_tematico'].round(2)
df_out['Interacción']                  = df_all['interaccion'].round(2)
df_out['Uso de TIC']                   = df_all['uso_tic'].round(2)
df_out['Satisfacción']                 = df_all['satisfaccion'].round(2)
df_out['Promedio']                     = df_all['promedio'].round(2)
df_out['Observaciones']                = df_all['observaciones'].fillna('')
df_out['Cédula']                       = df_all['cedula']

# Sort by facultad then nombre for coherent distribution
df_out = df_out.sort_values(['Facultad', 'Docente']).reset_index(drop=True)

total = len(df_out)
n_files = 5
chunk_size = math.ceil(total / n_files)

print(f"   Total docentes: {total} -> distribuyendo en {n_files} archivos...")

for i in range(n_files):
    start = i * chunk_size
    end   = min(start + chunk_size, total)
    chunk = df_out.iloc[start:end].copy()

    out_path = ENC_DIR + f'encuesta_facultad_{i}.xlsx'
    chunk.to_excel(out_path, index=False, engine='openpyxl')
    facults = chunk['Facultad'].value_counts().to_dict()
    print(f"   encuesta_facultad_{i}.xlsx: {len(chunk)} docentes | {facults}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. RESUMEN FINAL
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== RESUMEN FINAL ===")
print(f"Total docentes evaluados: {len(df_out)}")
print(f"Puntaje promedio institucional: {df_out['Puntaje Total'].mean():.2f}/100")
print(f"Promedio escala 5: {df_out['Promedio'].mean():.2f}/5.0")
print(f"\nComponentes promedio institucional:")
print(f"  Heteroevaluación Estudiantil (max 50): {df_out['Heteroevaluación Estudiantil'].mean():.2f}")
print(f"  Evaluación de Pares (max 20):          {df_out['Evaluación de Pares'].mean():.2f}")
print(f"  Aula Virtual (max 20):                  {df_out['Aula Virtual'].mean():.2f}")
print(f"  Autoevaluación (max 10):               {df_out['Autoevaluación'].mean():.2f}")
print(f"\nDistribución por Nivel de Desempeño:")
print(df_out['Nivel Desempeño'].value_counts().to_string())
print(f"\nDistribución por Facultad:")
print(df_out.groupby('Facultad')['Puntaje Total'].agg(['count','mean']).round(2).sort_values('mean', ascending=False).to_string())
print("\n¡Script completado exitosamente!")
