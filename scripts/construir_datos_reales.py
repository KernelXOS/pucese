"""
construir_datos_reales.py
Construye los archivos encuesta_facultad_*.xlsx 100% desde datos reales.
Fuentes: eval_detalladas_2025_02/, HETEROEVALUACION 202456/202466, CSVs, CONSOLIDADO DATOS
"""

import pandas as pd
import numpy as np
import os
import warnings
from datetime import datetime
import math

warnings.filterwarnings('ignore')

DATOS_DIR = 'C:/Users/KernelXos/Desktop/DATOS_DOCENTE/'
EVAL_DIR  = DATOS_DIR + 'eval_detalladas_2025_02/'
ENC_DIR   = 'C:/Users/KernelXos/evaluacion-docente-ia/encuestas/'
HOY       = datetime(2026, 5, 7)

# ─────────────────────────────────────────────────────────────────────────────
# 1. CARGAR EVAL_DETALLADAS (fuente principal de KPIs)
# ─────────────────────────────────────────────────────────────────────────────
print("1. Cargando eval_detalladas...")
all_dfs = []
for f in os.listdir(EVAL_DIR):
    df = pd.ExcelFile(EVAL_DIR + f).parse(0)
    all_dfs.append(df)
df_eval = pd.concat(all_dfs, ignore_index=True)
df_eval['usuario_evaluado'] = df_eval['usuario_evaluado'].astype(str).str.strip()
df_eval['score_w'] = df_eval['calificacion'] * df_eval['peso']
print(f"   {len(df_eval)} filas | {df_eval['usuario_evaluado'].nunique()} docentes")

# Normalizar competencias
COMP_MAP = {
    'Planificar y  organizar':                              'Planificar y organizar',
    'Planificar y Organizar':                               'Planificar y organizar',
    ' Autonomía':                                           'Autonomía',
    'Pensamiento estratégico (Transferencia de resultados)':'Pensamiento estratégico',
    'Adaptabilidad y cambio':                               'Adaptabilidad al cambio',
}
df_eval['comp_norm'] = df_eval['competencia'].str.strip().replace(COMP_MAP)

# ─────────────────────────────────────────────────────────────────────────────
# 2. KPI POR COMPETENCIA (escala 0-5)
# ─────────────────────────────────────────────────────────────────────────────
print("2. Calculando KPIs reales por competencia...")

# Mapeo competencia → columna ETL (escala 0-5)
COMP_TO_COL = {
    'Aprendizaje continuo bidireccional':   'metodologia',
    'Planificar y organizar':               'puntualidad',
    'Pensamiento estratégico':              'dominio_tematico',
    'Manejo de relaciones interpersonales': 'interaccion',
    'Tratamiento de la información y medios': 'uso_tic',
}

prof_comp = df_eval.groupby(
    ['usuario_evaluado', 'apellidos_evaluado', 'nombres_evaluado', 'comp_norm']
).agg(
    total_sw=('score_w', 'sum'),
    total_p=('peso', 'sum')
).reset_index()
prof_comp['kpi_5'] = (prof_comp['total_sw'] / prof_comp['total_p'] / 4 * 5).round(2)

# Pivot: una fila por docente
kpi_pivot = prof_comp.pivot_table(
    index=['usuario_evaluado', 'apellidos_evaluado', 'nombres_evaluado'],
    columns='comp_norm',
    values='kpi_5',
    aggfunc='mean'
).reset_index()
kpi_pivot.columns.name = None

# Renombrar a columnas ETL
rename_kpi = {v: k for k, v in COMP_TO_COL.items()}  # reverse for column names
# Apply direct mapping
for comp_name, col_name in COMP_TO_COL.items():
    if comp_name in kpi_pivot.columns:
        kpi_pivot = kpi_pivot.rename(columns={comp_name: col_name})

# Puntaje global (promedio ponderado real)
prof_global = df_eval.groupby(
    ['usuario_evaluado', 'apellidos_evaluado', 'nombres_evaluado']
).agg(
    total_sw=('score_w', 'sum'),
    total_p=('peso', 'sum'),
    periodo=('periodo_evaluacion', lambda x: str(x.mode().iloc[0]) if len(x) > 0 else '202502'),
    programa=('programa', lambda x: x.mode().iloc[0] if len(x) > 0 else ''),
).reset_index()
prof_global['promedio'] = (prof_global['total_sw'] / prof_global['total_p'] / 4 * 5).round(2)

# Merge
master = prof_global.merge(kpi_pivot, on=['usuario_evaluado', 'apellidos_evaluado', 'nombres_evaluado'], how='left')
master['cedula'] = master['usuario_evaluado'].str.lstrip('0')

print(f"   {len(master)} docentes con KPIs calculados")

# ─────────────────────────────────────────────────────────────────────────────
# 3. FACULTAD REAL desde HETEROEVALUACION
# ─────────────────────────────────────────────────────────────────────────────
print("3. Obteniendo facultad real desde HETEROEVALUACION...")

def _first_mode(x):
    m = x.dropna().mode()
    return m.iloc[0] if len(m) > 0 else np.nan

df_h56 = pd.ExcelFile(DATOS_DIR + 'HETEROEVALUACION 202456.xlsx').parse(0)
df_h66 = pd.ExcelFile(DATOS_DIR + 'HETEROEVALUACION 202466.xlsx').parse(0)
df_hetero = pd.concat([df_h56, df_h66], ignore_index=True)
df_hetero['cedula'] = df_hetero['NUM_DOCU'].astype(str).str.strip().str.split('.').str[0].str.lstrip('0')
df_hetero['puntaje_hetero'] = pd.to_numeric(df_hetero['PUNTAJE'], errors='coerce')

hetero_info = df_hetero.groupby('cedula').agg(
    dept=('STVDEPT_DESC', _first_mode),
    puntaje_hetero=('puntaje_hetero', 'mean'),
    periodo_hetero=('STVTERM_DESC', _first_mode),
).reset_index()

# Mapeo de departamento → facultad legible
DEPT_FACULTAD = {
    'Medicina Repotenciada - ESM': 'Medicina',
    'Escuela Enfermería':          'Salud',
    'Esc.Hotel. Y Turismo':        'Turismo y Hotelería',
    'C. Educación Inicial':        'Educación',
    'C. Psicología':               'Psicología',
    'C.Sist.Y Computación':        'Ingeniería',
    'M. Tec de la Información':    'Ingeniería',
    'Fac De Ingeniería':           'Ingeniería',
    'SMTI':                        'Ingeniería',
}

def map_facultad(dept, programa):
    if pd.notna(dept):
        for k, v in DEPT_FACULTAD.items():
            if k.lower() in str(dept).lower():
                return v
    prog = str(programa).lower()
    if any(p in prog for p in ['enferm', 'salud', 'fisio', 'laborat', 'bioquim', 'morfo', 'farmac']):
        return 'Salud'
    if any(p in prog for p in ['medic', 'anatom', 'clinic']):
        return 'Medicina'
    if any(p in prog for p in ['derecho', 'legal', 'jurid']):
        return 'Derecho'
    if any(p in prog for p in ['psicolog', 'social']):
        return 'Psicología'
    if any(p in prog for p in ['sistem', 'inform', 'computa', 'software', 'tecnolog', 'cloud', 'dato']):
        return 'Ingeniería'
    if any(p in prog for p in ['contab', 'admin', 'negoc', 'finanz', 'audit', 'comerci']):
        return 'Ciencias Administrativas'
    if any(p in prog for p in ['educ', 'pedagog', 'idiom']):
        return 'Educación'
    if any(p in prog for p in ['agro', 'aliment', 'culinari']):
        return 'Agroindustria'
    if any(p in prog for p in ['turism', 'hotel']):
        return 'Turismo y Hotelería'
    return 'Otras Ciencias'

master = master.merge(hetero_info, on='cedula', how='left')
master['facultad'] = master.apply(
    lambda r: map_facultad(r.get('dept'), r.get('programa', '')), axis=1
)

# ─────────────────────────────────────────────────────────────────────────────
# 4. DATOS DEMOGRÁFICOS REALES (sexo, edad)
# ─────────────────────────────────────────────────────────────────────────────
print("4. Obteniendo datos demográficos reales...")

def parse_sex(s):
    s = str(s).strip().upper()
    if 'MUJ' in s or s == 'F': return 'Femenino'
    if 'HOM' in s or s == 'M': return 'Masculino'
    return np.nan

def calc_age(dob_str):
    for fmt in ('%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            dob = datetime.strptime(str(dob_str).strip(), fmt)
            return HOY.year - dob.year - ((HOY.month, HOY.day) < (dob.month, dob.day))
        except:
            pass
    return np.nan

# Fuente 1: CONSOLIDADO DATOS (mayor cobertura)
df_datos = pd.ExcelFile(DATOS_DIR + 'CONSOLIDADO HETEROEVALUACIÓN.xlsx').parse('DATOS')
df_datos['cedula'] = df_datos['Cédula'].astype(str).str.strip().str.lstrip('0')
df_datos['sexo'] = df_datos['Genero'].apply(parse_sex)
df_datos['edad'] = pd.to_numeric(df_datos['Edad'], errors='coerce')
demo = df_datos[['cedula', 'sexo', 'edad']].dropna(subset=['cedula']).drop_duplicates('cedula')

# Fuente 2: CSVs (tienen fecha de nacimiento)
for csv_f, dob_col in [
    ('Resultados Finales Hetero Evaluación Docente Report - 202556.csv', 'fecha de nacimiento'),
    ('Resultados Finales Hetero Evaluación Docente Report - CSV_202566.csv', 'Fecha de nacimiento'),
]:
    csv = pd.read_csv(DATOS_DIR + csv_f, encoding='latin1', sep=None, engine='python')
    csv['cedula']  = csv['NUM_DOCU'].astype(str).str.strip().str.split('.').str[0].str.lstrip('0')
    csv['sexo']    = csv['Sexo'].apply(parse_sex)
    csv['edad']    = csv[dob_col].apply(calc_age)
    csv_sub = csv[['cedula', 'sexo', 'edad']].dropna(subset=['cedula']).drop_duplicates('cedula')
    demo = pd.concat([demo, csv_sub]).drop_duplicates('cedula', keep='first')

print(f"   {len(demo)} registros demográficos | con sexo: {demo['sexo'].notna().sum()} | con edad: {demo['edad'].notna().sum()}")

master = master.merge(demo, on='cedula', how='left')

# ─────────────────────────────────────────────────────────────────────────────
# 5. NOMBRE COMPLETO Y LIMPIEZA
# ─────────────────────────────────────────────────────────────────────────────
master['docente_nombre'] = (
    master['apellidos_evaluado'].str.title().str.strip() + ' ' +
    master['nombres_evaluado'].str.title().str.strip()
)

# Satisfaccion = promedio de KPIs disponibles
kpi_etl_cols = ['metodologia', 'puntualidad', 'dominio_tematico', 'interaccion', 'uso_tic']
avail_kpi = [c for c in kpi_etl_cols if c in master.columns]
master['satisfaccion'] = master[avail_kpi].mean(axis=1).round(2)

# Promedio final: si hay heteroevaluacion combinar, si no usar solo autoevaluacion
def promedio_final(row):
    vals = [row['promedio']]
    if pd.notna(row.get('puntaje_hetero')):
        vals.append(row['puntaje_hetero'] / 100 * 5)  # convertir de 100 a 5
    return round(float(np.nanmean(vals)), 2)

master['promedio_final'] = master.apply(promedio_final, axis=1)

# Periodo: usar periodo de autoevaluacion
master['periodo'] = master['periodo'].astype(str).str.strip()

print(f"\nResumen master:")
print(f"  Total docentes: {len(master)}")
print(f"  Con sexo conocido: {master['sexo'].notna().sum()}")
print(f"  Con edad conocida: {master['edad'].notna().sum()}")
print(f"  Con puntaje hetero: {master['puntaje_hetero'].notna().sum()}")
print(f"  Facultades: {sorted(master['facultad'].unique())}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. CONSTRUIR ARCHIVOS encuesta_facultad CON DATOS 100% REALES
# ─────────────────────────────────────────────────────────────────────────────
print("\n5. Construyendo archivos encuesta_facultad con datos reales...")

# Agregar nivel de desempeño
def nivel(p):
    if p >= 4.5: return 'Excelente'
    if p >= 3.75: return 'Bueno'
    if p >= 3.0: return 'Regular'
    return 'Deficiente'

master['nivel_desempeno'] = master['promedio_final'].apply(nivel)

# Ordenar por facultad para distribuir coherentemente en archivos
master_sorted = master.sort_values(['facultad', 'docente_nombre']).reset_index(drop=True)

# Columnas en orden que el ETL espera
ETL_COLS = ['docente_nombre', 'facultad', 'periodo', 'sexo', 'edad',
            'metodologia', 'puntualidad', 'dominio_tematico',
            'interaccion', 'uso_tic', 'satisfaccion', 'promedio_final',
            'observaciones', 'nivel_desempeno']

# Preparar DataFrame final con columnas correctas
df_out = pd.DataFrame()
df_out['Docente']           = master_sorted['docente_nombre']
df_out['Facultad']          = master_sorted['facultad']
df_out['Periodo']           = master_sorted['periodo']
df_out['Sexo']              = master_sorted['sexo'].fillna('No registrado')
df_out['Edad']              = master_sorted['edad'].apply(lambda x: int(x) if pd.notna(x) else None)
df_out['Metodología']       = master_sorted['metodologia'].round(2)
df_out['Puntualidad']       = master_sorted['puntualidad'].round(2)
df_out['Dominio Temático']  = master_sorted['dominio_tematico'].round(2)
df_out['Interacción']       = master_sorted['interaccion'].round(2)
df_out['Uso de TIC']        = master_sorted['uso_tic'].round(2)
df_out['Satisfacción']      = master_sorted['satisfaccion'].round(2)
df_out['Promedio']          = master_sorted['promedio_final']
df_out['Observaciones']     = master_sorted['nivel_desempeno'].apply(
    lambda n: {
        'Excelente': 'Excelente desempeño docente',
        'Bueno':     'Buen desempeño docente',
        'Regular':   'Desempeño regular, requiere mejora',
        'Deficiente':'Requiere plan de mejoramiento urgente',
    }.get(n, '')
)
df_out['Cédula']            = master_sorted['cedula']
df_out['Nivel Desempeño']   = master_sorted['nivel_desempeno']

print(f"  Total filas a distribuir: {len(df_out)}")

# Distribuir en 5 archivos por facultad
total = len(df_out)
n_files = 5
chunk_size = math.ceil(total / n_files)

# Delete old synthetic files and write new real ones
for i in range(n_files):
    start = i * chunk_size
    end   = min(start + chunk_size, total)
    chunk = df_out.iloc[start:end].copy()

    out_path = ENC_DIR + f'encuesta_facultad_{i}.xlsx'
    chunk.to_excel(out_path, index=False)
    facults = chunk['Facultad'].value_counts().to_dict()
    print(f"  encuesta_facultad_{i}.xlsx: {len(chunk)} docentes | Facultades: {facults}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. REPORTE COMPLETO REAL
# ─────────────────────────────────────────────────────────────────────────────
print("\n6. Generando reporte consolidado real...")

REPORTE = 'C:/Users/KernelXos/evaluacion-docente-ia/reportes/REPORTE_REAL_DOCENTES_202502.xlsx'

with pd.ExcelWriter(REPORTE, engine='openpyxl') as writer:

    # Hoja 1: Todos los docentes con puntajes reales
    df_reporte = df_out.sort_values('Promedio', ascending=False).reset_index(drop=True)
    df_reporte.to_excel(writer, sheet_name='Docentes_Puntaje_Real', index=False)

    # Hoja 2: Ranking por facultad
    ranking_fac = df_out.groupby('Facultad').agg(
        N_Docentes=('Docente', 'count'),
        Promedio_Facultad=('Promedio', 'mean'),
        Metodologia_Prom=('Metodología', 'mean'),
        Dominio_Prom=('Dominio Temático', 'mean'),
        Interaccion_Prom=('Interacción', 'mean'),
        TIC_Prom=('Uso de TIC', 'mean'),
    ).round(2).reset_index().sort_values('Promedio_Facultad', ascending=False)
    ranking_fac.to_excel(writer, sheet_name='Ranking_por_Facultad', index=False)

    # Hoja 3: Distribución por nivel de desempeño
    dist = df_out['Nivel Desempeño'].value_counts().reset_index()
    dist.columns = ['Nivel', 'N_Docentes']
    dist['Porcentaje'] = (dist['N_Docentes'] / dist['N_Docentes'].sum() * 100).round(1)
    dist.to_excel(writer, sheet_name='Distribucion_Niveles', index=False)

    # Hoja 4: Distribución por sexo
    sexo = df_out.groupby('Sexo').agg(
        N=('Docente', 'count'),
        Promedio=('Promedio', 'mean'),
    ).round(2).reset_index()
    sexo.to_excel(writer, sheet_name='Distribucion_Sexo', index=False)

    # Hoja 5: Top 20 y Bottom 20
    df_out.sort_values('Promedio', ascending=False).head(20).to_excel(
        writer, sheet_name='Top_20_Docentes', index=False)
    df_out.sort_values('Promedio', ascending=True).head(20).to_excel(
        writer, sheet_name='Bottom_20_Docentes', index=False)

print(f"  Reporte guardado: {REPORTE}")

print("\n=== RESUMEN FINAL (DATOS REALES) ===")
print(f"Total docentes evaluados: {len(df_out)}")
print(f"Promedio institucional: {df_out['Promedio'].mean():.2f}/5.0")
print(f"\nDistribucion por nivel:")
print(df_out['Nivel Desempeño'].value_counts().to_string())
print(f"\nDistribucion por facultad:")
print(df_out.groupby('Facultad')['Promedio'].agg(['count','mean']).round(2).sort_values('mean', ascending=False).to_string())
