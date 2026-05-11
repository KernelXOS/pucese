"""
ETL multi-modelo para evaluación docente PUCESE.
Procesa todas las fuentes disponibles y genera registros por:
  - sistema: 'meipa' | '360'
  - modelo: docencia / abp / vinculacion / gestion / investigacion
  - año: 2023, 2024, 2025
"""
import sys, os, re, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.evaluacion import Base, Evaluacion

BASE     = r'C:\Users\KernelXos\Desktop\DATOS_DOCENTE'
EVAL_DIR = os.path.join(BASE, 'eval_detalladas_2025_02')
DB_PATH  = os.path.join(os.path.dirname(__file__), '..', 'backend', 'evaluacion.db')

engine = create_engine(f'sqlite:///{os.path.abspath(DB_PATH)}')
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# ── Helpers ────────────────────────────────────────────────────────────────────

FACULTAD_MAP = {
    'CONTABILIDAD':      'Ciencias Administrativas',
    'ADMINISTRACION':    'Ciencias Administrativas',
    'ADMINISTRACI':      'Ciencias Administrativas',
    'TURISMO':           'Turismo y Hotelería',
    'HOTELERIA':         'Turismo y Hotelería',
    'MEDICINA':          'Medicina',
    'LABORATORIO CLINICO':'Medicina',
    'LABORATORIO CL':    'Medicina',
    'ENFERMERIA':        'Salud',
    'ENFERMERÍA':        'Salud',
    'NUTRICION':         'Salud',
    'NUTRICIÓN':         'Salud',
    'PSICOLOGIA':        'Psicología',
    'PSICOLOGÍA':        'Psicología',
    'DERECHO':           'Derecho',
    'INGENIERIA':        'Ingeniería',
    'INGENIERÍA':        'Ingeniería',
    'SISTEMAS':          'Ingeniería',
    'COMPUTACION':       'Ingeniería',
    'COMPUTACIÓN':       'Ingeniería',
    'EDUCACION':         'Educación',
    'EDUCACIÓN':         'Educación',
    'AGRO':              'Agroindustria',
    'MENTOR':            'Otras Ciencias',
    'NO DEFINIDA':       'Otras Ciencias',
    'PUCETEC':           'Otras Ciencias',
}

def map_facultad(text: str) -> str:
    if not text or pd.isna(text):
        return 'Otras Ciencias'
    t = str(text).upper().strip()
    for k, v in FACULTAD_MAP.items():
        if k in t:
            return v
    return 'Otras Ciencias'

def nivel_from_puntaje(p: float) -> str:
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return 'Sin datos'
    if p >= 90: return 'Excelente'
    if p >= 75: return 'Bueno'
    if p >= 60: return 'Regular'
    return 'Deficiente'

def clean_cedula(v) -> str:
    return str(v).strip().lstrip('0') if v and str(v).strip() not in ('', 'nan', 'NaN') else ''

def clean_nombre(v) -> str:
    s = str(v).strip() if v else ''
    return '' if s.lower() in ('nan', 'none', '') else s

def safe_float(v) -> float:
    try:
        f = float(v)
        return None if np.isnan(f) else f
    except:
        return None

def parse_antiguedad_str(s) -> float:
    """Parse strings like '9 AÑOS 1 MESES' or '9 AÑOS' → float years."""
    if not s or pd.isna(s):
        return None
    s = str(s).upper()
    anios = re.search(r'(\d+)\s*A[ÑN]OS?', s)
    meses = re.search(r'(\d+)\s*MESES?', s)
    years = int(anios.group(1)) if anios else 0
    months = int(meses.group(1)) if meses else 0
    result = years + months / 12.0
    return round(result, 2) if result > 0 else None

def norm_str(s) -> str:
    import unicodedata
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower().strip()

# ══════════════════════════════════════════════════════════════════════════════
# 0. STAFF LOOKUP from REPORTE DE PERSONAL 2025 (1).XLSX
# ══════════════════════════════════════════════════════════════════════════════
print("=== 0. Cargando tabla de personal 2025 ===")
STAFF_REF_DATE = datetime(2025, 1, 1)
staff_lookup = {}  # key: cedula → {nombre_completo, antiguedad_anos, funcion, unidad_org, genero}

try:
    df_staff = pd.read_excel(
        os.path.join(BASE, 'REPORTE DE PERSONAL 2025 (1).XLSX'),
        sheet_name='Sheet1', dtype=str
    )
    df_staff.columns = [c.strip() for c in df_staff.columns]

    # Find relevant columns (robust match)
    def find_staff_col(df, keys):
        for c in df.columns:
            cl = norm_str(c)
            if any(norm_str(k) in cl for k in keys):
                return c
        return None

    col_ced_s  = find_staff_col(df_staff, ['cedula', 'pasaporte'])
    col_ap1_s  = find_staff_col(df_staff, ['1° apellido', 'primer apellido', 'apellido1'])
    col_ap2_s  = find_staff_col(df_staff, ['segundo apellido', 'apellido2'])
    col_n1_s   = find_staff_col(df_staff, ['primer nombre', 'nombre1'])
    col_n2_s   = find_staff_col(df_staff, ['segundo nombre', 'nombre2'])
    col_gen_s  = find_staff_col(df_staff, ['genero', 'género', 'sexo'])
    col_edad_s = find_staff_col(df_staff, ['edad'])
    col_uni_s  = find_staff_col(df_staff, ['unidad organizativa', 'unidad org'])
    col_fec_s  = find_staff_col(df_staff, ['fecha antig', 'primer ingreso', 'antiguedad'])
    col_rel_s  = find_staff_col(df_staff, ['texto rel', 'rel.laboral'])
    col_fun_s  = find_staff_col(df_staff, ['funcion', 'función'])

    print(f"  Columnas staff: {list(df_staff.columns[:12])}")

    for _, row in df_staff.iterrows():
        ced = clean_cedula(row.get(col_ced_s, '')) if col_ced_s else ''
        if not ced:
            continue

        ap1 = clean_nombre(row.get(col_ap1_s)) if col_ap1_s else ''
        ap2 = clean_nombre(row.get(col_ap2_s)) if col_ap2_s else ''
        n1  = clean_nombre(row.get(col_n1_s))  if col_n1_s  else ''
        n2  = clean_nombre(row.get(col_n2_s))  if col_n2_s  else ''
        nombre = f"{ap1} {ap2} {n1} {n2}".strip()
        nombre = ' '.join(nombre.split())

        genero  = clean_nombre(row.get(col_gen_s))  if col_gen_s  else ''
        unidad  = clean_nombre(row.get(col_uni_s))  if col_uni_s  else ''
        funcion = clean_nombre(row.get(col_fun_s))  if col_fun_s  else ''

        antiguedad_anos = None
        if col_fec_s:
            fec_raw = row.get(col_fec_s)
            if fec_raw and str(fec_raw).strip() not in ('', 'nan', 'NaN'):
                try:
                    # Excel stores dates as datetime already (dtype=str → parse)
                    fec_dt = pd.to_datetime(fec_raw, errors='coerce', dayfirst=True)
                    if pd.notna(fec_dt):
                        delta = STAFF_REF_DATE - fec_dt.to_pydatetime().replace(tzinfo=None)
                        antiguedad_anos = round(delta.days / 365.25, 2)
                except:
                    pass

        staff_lookup[ced] = {
            'nombre_completo': nombre,
            'antiguedad_anos': antiguedad_anos,
            'funcion':         funcion.upper() if funcion else '',
            'unidad_org':      unidad,
            'genero':          genero,
        }

    print(f"  Personal cargado: {len(staff_lookup)} registros")
except Exception as e:
    print(f"  AVISO: No se pudo leer personal 2025: {e}")

records = []

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS for name / enrichment
# ══════════════════════════════════════════════════════════════════════════════

def enrich_from_staff(ced, rec):
    """Fill missing fields from staff_lookup."""
    s = staff_lookup.get(ced)
    if not s:
        return rec
    if not rec.get('docente_nombre') or rec['docente_nombre'].startswith('CED-'):
        rec['docente_nombre'] = s['nombre_completo'] or f'CED-{ced}'
    if not rec.get('antiguedad_anos') and s['antiguedad_anos']:
        rec['antiguedad_anos'] = s['antiguedad_anos']
    if not rec.get('funcion_docente') and s['funcion']:
        rec['funcion_docente'] = s['funcion']
    if not rec.get('sexo') and s['genero']:
        rec['sexo'] = s['genero']
    if not rec.get('facultad') or rec['facultad'] == 'Otras Ciencias':
        fac = map_facultad(s['unidad_org'])
        if fac != 'Otras Ciencias':
            rec['facultad'] = fac
    return rec

def build_nombre(ced, fallback=''):
    s = staff_lookup.get(ced)
    if s and s['nombre_completo']:
        return s['nombre_completo']
    if fallback and clean_nombre(fallback):
        return clean_nombre(fallback)
    return f'CED-{ced}' if ced else 'Sin nombre'

# ══════════════════════════════════════════════════════════════════════════════
# 1A. MEIPA — CONSOLIDADO HETEROEVALUACIÓN.xlsx (DATOS sheet)
# ══════════════════════════════════════════════════════════════════════════════
print("=== 1A. MEIPA — CONSOLIDADO Heteroevaluación ===")

def extract_period_code(s):
    m = re.search(r'(20\d{4})', str(s))
    return m.group(1) if m else '202300'

try:
    xl_c = pd.ExcelFile(os.path.join(BASE, 'CONSOLIDADO HETEROEVALUACIÓN.xlsx'), engine='openpyxl')
    df_datos = pd.read_excel(xl_c, sheet_name='DATOS', dtype=str)
    df_datos.columns = [c.strip() for c in df_datos.columns]

    # Normalize col names for lookup
    col_map = {}
    for c in df_datos.columns:
        cl = norm_str(c)
        col_map[cl] = c

    def gc_datos(keys):
        for k in keys:
            nk = norm_str(k)
            if nk in col_map:
                return col_map[nk]
        # partial match
        for k in keys:
            nk = norm_str(k)
            for ck, cv in col_map.items():
                if nk in ck:
                    return cv
        return None

    col_ced_d   = gc_datos(['cedula'])
    col_nom_d   = gc_datos(['apellidos y nombres', 'apellidos'])
    col_per_d   = gc_datos(['periodo evaluado', 'periodo'])
    col_pun_d   = gc_datos(['promedio de puntaje', 'puntaje'])
    col_gen_d   = gc_datos(['genero', 'género'])
    col_eda_d   = gc_datos(['edad'])
    col_tse_d   = gc_datos(['tiempo de servicio'])
    col_niv_d   = gc_datos(['nivel de estudio'])
    col_gra_d   = gc_datos(['grado'])
    col_mod_d   = gc_datos(['modalidad de trabajo', 'modalidad'])
    col_car_d   = gc_datos(['carrera'])

    # Use positional fallbacks if column names not found
    if not col_ced_d: col_ced_d = df_datos.columns[1]
    if not col_nom_d: col_nom_d = df_datos.columns[2]
    if not col_per_d: col_per_d = df_datos.columns[0]
    if not col_pun_d: col_pun_d = df_datos.columns[-1]

    df_datos['_cedula']  = df_datos[col_ced_d].apply(clean_cedula)
    df_datos['_nombre']  = df_datos[col_nom_d].apply(clean_nombre)
    df_datos['_periodo'] = df_datos[col_per_d].apply(extract_period_code)
    df_datos['_anio']    = df_datos['_periodo'].apply(lambda p: int(p[:4]) if p[:4].isdigit() else 2023)
    df_datos['_puntaje'] = pd.to_numeric(df_datos[col_pun_d], errors='coerce')

    # Demog lookup per cedula
    demog_consol = {}
    for _, row in df_datos.iterrows():
        ced = row['_cedula']
        if ced and ced not in demog_consol:
            demog_consol[ced] = {
                'sexo':    clean_nombre(row.get(col_gen_d)) if col_gen_d else '',
                'carrera': clean_nombre(row.get(col_car_d)) if col_car_d else '',
                'tserv':   clean_nombre(row.get(col_tse_d)) if col_tse_d else '',
                'nivel':   clean_nombre(row.get(col_niv_d)) if col_niv_d else '',
                'grado':   clean_nombre(row.get(col_gra_d)) if col_gra_d else '',
                'modal':   clean_nombre(row.get(col_mod_d)) if col_mod_d else '',
                'edad':    None,
            }
            try:
                ed = row.get(col_eda_d) if col_eda_d else None
                demog_consol[ced]['edad'] = int(float(ed)) if ed and str(ed) not in ('nan','') else None
            except:
                pass

    # Aggregate by cedula + periodo
    agg_consol = df_datos[df_datos['_cedula'] != ''].groupby(['_cedula', '_periodo', '_anio']).agg(
        nombre=('_nombre', lambda x: x.mode().iloc[0] if len(x) > 0 else ''),
        puntaje=('_puntaje', 'mean'),
    ).reset_index()

    # Track periods covered
    meipa_periods_consol = set()

    n_consol = 0
    for _, row in agg_consol.iterrows():
        ced     = str(row['_cedula']).strip()
        periodo = str(row['_periodo'])
        anio    = int(row['_anio'])
        puntaje = float(row['puntaje']) if not pd.isna(row['puntaje']) else 0.0
        nombre  = build_nombre(ced, row['nombre'])
        dm      = demog_consol.get(ced, {})
        carr    = dm.get('carrera', '')
        fac     = map_facultad(carr)

        s = staff_lookup.get(ced, {})
        antig = s.get('antiguedad_anos') if s else None
        funcion = s.get('funcion', '') if s else ''

        rec = {
            'docente_nombre': nombre,
            'facultad':       fac,
            'carrera':        carr,
            'periodo':        periodo,
            'anio':           anio,
            'modelo':         'docencia',
            'sistema':        'meipa',
            'sexo':           dm.get('sexo', '') or (s.get('genero','') if s else ''),
            'edad':           dm.get('edad'),
            'tiempo_servicio': dm.get('tserv', ''),
            'nivel_estudio':   dm.get('nivel', ''),
            'grado':           dm.get('grado', ''),
            'modalidad':       dm.get('modal', ''),
            'cedula':          ced,
            'het_estudiantil': round(puntaje / 100 * 50, 2),
            'puntaje_100':     round(puntaje, 2),
            'promedio':        round(puntaje / 100 * 5, 2),
            'nivel_desempeno': nivel_from_puntaje(puntaje),
            'comp_hetero_est': round(puntaje, 2),
            'antiguedad_anos': antig,
            'funcion_docente': funcion or 'DOCENCIA',
            'archivo_fuente':  'CONSOLIDADO HETEROEVALUACIÓN.xlsx',
        }
        records.append(rec)
        meipa_periods_consol.add((ced, periodo))
        n_consol += 1

    print(f"  CONSOLIDADO MEIPA: {n_consol} registros")
except Exception as e:
    print(f"  ERROR CONSOLIDADO: {e}")
    import traceback; traceback.print_exc()

# ══════════════════════════════════════════════════════════════════════════════
# 1B. MEIPA — RESULTADOS GENERALES CONSOLIDADO 202301 al 202401 1.xlsx
# ══════════════════════════════════════════════════════════════════════════════
print("=== 1B. MEIPA — RESULTADOS GENERALES CONSOLIDADO ===")

try:
    rg_path = os.path.join(BASE, 'RESULTADOS GENERALES CONSOLIDADO 202301 al 202401 1.xlsx')
    df_rg = pd.read_excel(rg_path, sheet_name='REPORTE GENERAL', header=0, dtype=str)
    df_rg.columns = [str(c).strip() for c in df_rg.columns]

    # Expected cols: PERÍODO ACADEMICO, Apellidos y Nombres, CEDULA, EDAD,
    #                UNIDAD ACADEMICA, ANTIGÜEDAD, GENERO, NIVEL DE ESTUDIO,
    #                TIEMPO DE SERVICIO, Estud a Doc, Autoeval,
    #                Coord a Docente, Eval pares, Total, TOTAL SOBRE 100

    def fc_rg(keys):
        for k in keys:
            nk = norm_str(k)
            for c in df_rg.columns:
                if nk in norm_str(c):
                    return c
        return None

    col_per_rg  = fc_rg(['periodo academico', 'período', 'periodo'])
    col_nom_rg  = fc_rg(['apellidos y nombres', 'apellidos'])
    col_ced_rg  = fc_rg(['cedula'])
    col_eda_rg  = fc_rg(['edad'])
    col_uni_rg  = fc_rg(['unidad academica', 'unidad'])
    col_ant_rg  = fc_rg(['antiguedad', 'antigüedad'])
    col_gen_rg  = fc_rg(['genero', 'género'])
    col_niv_rg  = fc_rg(['nivel de estudio', 'nivel estudio'])
    col_tse_rg  = fc_rg(['tiempo de servicio'])
    col_est_rg  = fc_rg(['estud a doc'])
    col_aut_rg  = fc_rg(['autoeval'])
    col_coo_rg  = fc_rg(['coord a docente', 'coord'])
    col_par_rg  = fc_rg(['eval pares'])
    col_tot_rg  = fc_rg(['total sobre 100', 'total_100'])

    # Fallback positional if names differ
    cols = list(df_rg.columns)
    if not col_per_rg and len(cols) > 0:  col_per_rg  = cols[0]
    if not col_nom_rg and len(cols) > 1:  col_nom_rg  = cols[1]
    if not col_ced_rg and len(cols) > 2:  col_ced_rg  = cols[2]
    if not col_eda_rg and len(cols) > 3:  col_eda_rg  = cols[3]
    if not col_uni_rg and len(cols) > 4:  col_uni_rg  = cols[4]
    if not col_ant_rg and len(cols) > 5:  col_ant_rg  = cols[5]
    if not col_gen_rg and len(cols) > 6:  col_gen_rg  = cols[6]
    if not col_niv_rg and len(cols) > 7:  col_niv_rg  = cols[7]
    if not col_tse_rg and len(cols) > 8:  col_tse_rg  = cols[8]
    if not col_est_rg and len(cols) > 9:  col_est_rg  = cols[9]
    if not col_aut_rg and len(cols) > 10: col_aut_rg  = cols[10]
    if not col_coo_rg and len(cols) > 11: col_coo_rg  = cols[11]
    if not col_par_rg and len(cols) > 12: col_par_rg  = cols[12]
    if not col_tot_rg and len(cols) > 14: col_tot_rg  = cols[14]

    # Drop header-repeat rows (where cedula is literally "CEDULA")
    df_rg = df_rg[df_rg[col_ced_rg].apply(
        lambda v: str(v).strip().upper() not in ('CEDULA', 'NAN', '')
    )].copy()

    n_rg = 0
    for _, row in df_rg.iterrows():
        ced = clean_cedula(row.get(col_ced_rg, ''))
        if not ced:
            continue

        per_raw = str(row.get(col_per_rg, '')).strip()
        periodo = extract_period_code(per_raw) if per_raw else '202301'
        anio    = int(periodo[:4]) if periodo[:4].isdigit() else 2023

        # Skip if already covered by CONSOLIDADO
        if (ced, periodo) in meipa_periods_consol:
            continue

        total_100_raw = row.get(col_tot_rg)
        total_100 = safe_float(total_100_raw)
        if total_100 is None:
            continue

        # Component values (raw scale)
        # Estud a Doc: max 2 → /2*100
        # Autoeval: max 1 → *100
        # Coord a Docente: max 1 → *100
        # Eval pares: max 1 → *100
        est_raw = safe_float(row.get(col_est_rg)) or 0.0
        aut_raw = safe_float(row.get(col_aut_rg)) or 0.0
        coo_raw = safe_float(row.get(col_coo_rg)) or 0.0
        par_raw = safe_float(row.get(col_par_rg)) or 0.0

        c_est = round(est_raw / 2 * 100, 2)
        c_aut = round(aut_raw * 100, 2)
        c_coo = round(coo_raw * 100, 2)
        c_par = round(par_raw * 100, 2)

        nombre = build_nombre(ced, row.get(col_nom_rg, ''))
        unidad = clean_nombre(row.get(col_uni_rg)) if col_uni_rg else ''
        fac    = map_facultad(unidad)

        ant_str = clean_nombre(row.get(col_ant_rg)) if col_ant_rg else ''
        antig   = parse_antiguedad_str(ant_str)
        if not antig:
            antig = (staff_lookup.get(ced) or {}).get('antiguedad_anos')

        gen  = clean_nombre(row.get(col_gen_rg)) if col_gen_rg else ''
        niv  = clean_nombre(row.get(col_niv_rg)) if col_niv_rg else ''
        tse  = clean_nombre(row.get(col_tse_rg)) if col_tse_rg else ''
        edad_v = None
        try:
            ed = row.get(col_eda_rg) if col_eda_rg else None
            edad_v = int(float(ed)) if ed and str(ed).strip() not in ('nan','') else None
        except:
            pass

        s = staff_lookup.get(ced, {})
        funcion = s.get('funcion', 'DOCENCIA') if s else 'DOCENCIA'

        rec = {
            'docente_nombre': nombre,
            'facultad':       fac,
            'carrera':        unidad,
            'periodo':        periodo,
            'anio':           anio,
            'modelo':         'docencia',
            'sistema':        'meipa',
            'sexo':           gen or (s.get('genero','') if s else ''),
            'edad':           edad_v,
            'tiempo_servicio': tse,
            'nivel_estudio':   niv,
            'cedula':          ced,
            'puntaje_100':     round(total_100, 2),
            'promedio':        round(total_100 / 100 * 5, 2),
            'nivel_desempeno': nivel_from_puntaje(total_100),
            'het_estudiantil': round(est_raw / 2 * 50, 2),  # /2 normalized then *50
            'autoevaluacion':  round(aut_raw * 10, 2),       # *10 for /10 scale
            'comp_hetero_est': c_est,
            'comp_auto':       c_aut,
            'comp_hetero_dir': c_coo,
            'comp_pares':      c_par,
            'antiguedad_anos': antig,
            'funcion_docente': funcion,
            'archivo_fuente':  'RESULTADOS GENERALES CONSOLIDADO 202301 al 202401 1.xlsx',
        }
        records.append(rec)
        n_rg += 1

    print(f"  RESULTADOS GENERALES CONSOLIDADO: {n_rg} registros")
except Exception as e:
    print(f"  ERROR RESULTADOS GENERALES: {e}")
    import traceback; traceback.print_exc()

# ══════════════════════════════════════════════════════════════════════════════
# Helper: process a HETEROEVALUACION xlsx (202456 or 202466)
# ══════════════════════════════════════════════════════════════════════════════

INSTR_360_MAP = {
    norm_str('Heteroevaluación Grado Nuevo Docencia Esmeraldas'): ('docencia', 'hetero_est'),
    norm_str('Heteroevaluación Grado Nuevo Docencia Quito'):      ('docencia', 'hetero_est'),
    norm_str('Heteroevaluación Grado Nuevo Docencia Ibarra'):     ('docencia', 'hetero_est'),
    norm_str('Heteroevalauación Grado Nuevo ABP Quito'):          ('abp',      'hetero_est'),
    norm_str('Heteroevaluacion Grado Nuevo Docencia Esmeraldas'): ('docencia', 'hetero_est'),
    norm_str('Heteroevaluacion Grado Nuevo Docencia Quito'):      ('docencia', 'hetero_est'),
    norm_str('Heteroevaluacion Grado Nuevo Docencia Ibarra'):     ('docencia', 'hetero_est'),
    norm_str('Heteroevaluacion Grado Nuevo ABP Quito'):           ('abp',      'hetero_est'),
}

MEIPA_INSTR_KEYWORDS = [
    'inst. heteroevaluacion a la docencia esmeraldas',
    'inst. heteroevaluación a la docencia esmeraldas',
    'heteroevaluacion a la docencia',
    'inst heteroevaluaci',
    'esmeraldas meipa',
]

def is_meipa_instrument(instr_name: str) -> bool:
    n = norm_str(instr_name)
    return any(k in n for k in MEIPA_INSTR_KEYWORDS)

def process_hetero_xlsx(fpath: str, periodo_code: str):
    """
    Process a HETEROEVALUACION xlsx file.
    Returns (meipa_records, records_360) as lists of dicts.
    """
    anio = int(periodo_code[:4]) if periodo_code[:4].isdigit() else 2024
    meipa_recs = []
    recs_360   = []

    try:
        # Find correct sheet
        xl = pd.ExcelFile(fpath, engine='openpyxl')
        sheet = None
        for sh in xl.sheet_names:
            if 'hetero' in sh.lower() or 'resultado' in sh.lower():
                sheet = sh
                break
        if sheet is None:
            sheet = xl.sheet_names[0]

        df_h = pd.read_excel(xl, sheet_name=sheet, dtype=str)
        df_h.columns = [str(c).strip() for c in df_h.columns]

        def fch(keys):
            for k in keys:
                nk = norm_str(k)
                for c in df_h.columns:
                    if nk in norm_str(c):
                        return c
            return None

        col_doc   = fch(['num_docu', 'cedula'])
        col_last  = fch(['spriden_last_name', 'apellido'])
        col_first = fch(['spriden_first_name', 'nombre'])
        col_instr = fch(['instrumento'])
        col_punt  = fch(['puntaje'])
        col_dept  = fch(['stvdept_desc', 'dept', 'carrera', 'programa'])

        if not col_doc or not col_instr or not col_punt:
            print(f"  AVISO: Columnas no encontradas en {os.path.basename(fpath)}: doc={col_doc}, instr={col_instr}, punt={col_punt}")
            print(f"  Columnas disponibles: {list(df_h.columns[:20])}")
            return meipa_recs, recs_360

        df_h['_ced']   = df_h[col_doc].apply(clean_cedula)
        df_h['_punt']  = pd.to_numeric(df_h[col_punt], errors='coerce')
        df_h['_instr'] = df_h[col_instr].apply(norm_str)
        df_h['_nombre'] = (
            df_h[col_last].apply(clean_nombre) + ' ' +
            df_h[col_first].apply(clean_nombre)
        ).str.strip() if (col_last and col_first) else df_h['_ced'].apply(lambda c: f'CED-{c}')
        df_h['_dept'] = df_h[col_dept].apply(clean_nombre) if col_dept else ''

        # Separate by instrument type
        df_meipa = df_h[df_h[col_instr].apply(is_meipa_instrument)]
        df_360   = df_h[~df_h[col_instr].apply(is_meipa_instrument)]

        # ─── MEIPA rows ─────────────────────────────────────────────────────
        if not df_meipa.empty:
            agg_meipa = df_meipa.groupby('_ced').agg(
                nombre=('_nombre', lambda x: x.mode().iloc[0] if len(x) > 0 else ''),
                puntaje=('_punt', 'mean'),
                dept=('_dept', lambda x: x.mode().iloc[0] if len(x) > 0 else ''),
            ).reset_index()

            for _, row in agg_meipa.iterrows():
                ced     = str(row['_ced']).strip()
                puntaje = float(row['puntaje']) if not pd.isna(row['puntaje']) else 0.0
                nombre  = build_nombre(ced, row['nombre'])
                carr    = str(row.get('dept', '')).strip()
                fac     = map_facultad(carr)
                s       = staff_lookup.get(ced, {})

                rec = {
                    'docente_nombre': nombre,
                    'facultad':       fac,
                    'carrera':        carr,
                    'periodo':        periodo_code,
                    'anio':           anio,
                    'modelo':         'docencia',
                    'sistema':        'meipa',
                    'cedula':         ced,
                    'puntaje_100':    round(puntaje, 2),
                    'promedio':       round(puntaje / 100 * 5, 2),
                    'nivel_desempeno': nivel_from_puntaje(puntaje),
                    'het_estudiantil': round(puntaje / 100 * 50, 2),
                    'comp_hetero_est': round(puntaje, 2),
                    'sexo':           s.get('genero', '') if s else '',
                    'antiguedad_anos': s.get('antiguedad_anos') if s else None,
                    'funcion_docente': s.get('funcion', 'DOCENCIA') if s else 'DOCENCIA',
                    'archivo_fuente': os.path.basename(fpath),
                }
                meipa_recs.append(rec)

        # ─── 360 rows ───────────────────────────────────────────────────────
        # Group by cedula + instrument, get mean puntaje per instrument
        if not df_360.empty:
            agg_360 = df_360.groupby(['_ced', '_instr']).agg(
                nombre=('_nombre', lambda x: x.mode().iloc[0] if len(x) > 0 else ''),
                puntaje=('_punt', 'mean'),
                dept=('_dept', lambda x: x.mode().iloc[0] if len(x) > 0 else ''),
            ).reset_index()

            # {ced: {modelo: {comp: score}}}
            scores_360 = {}
            nombres_360 = {}
            depts_360   = {}

            for _, row in agg_360.iterrows():
                ced      = str(row['_ced']).strip()
                instr_n  = str(row['_instr']).strip()
                puntaje  = float(row['puntaje']) if not pd.isna(row['puntaje']) else 0.0
                nombre   = build_nombre(ced, row['nombre'])

                if instr_n not in INSTR_360_MAP:
                    # unknown instrument — skip silently
                    continue

                modelo, comp = INSTR_360_MAP[instr_n]
                key = (ced, modelo)
                if key not in scores_360:
                    scores_360[key] = {}
                    nombres_360[key] = nombre
                    depts_360[key]   = str(row.get('dept', '')).strip()
                scores_360[key][comp] = puntaje

            for (ced, modelo), comps in scores_360.items():
                puntaje  = comps.get('hetero_est', 0.0)
                nombre   = nombres_360[(ced, modelo)]
                carr     = depts_360[(ced, modelo)]
                fac      = map_facultad(carr)
                s        = staff_lookup.get(ced, {})

                rec = {
                    'docente_nombre': nombre,
                    'facultad':       fac,
                    'carrera':        carr,
                    'periodo':        periodo_code,
                    'anio':           anio,
                    'modelo':         modelo,
                    'sistema':        '360',
                    'cedula':         ced,
                    'puntaje_100':    round(puntaje, 2),
                    'promedio':       round(puntaje / 100 * 5, 2),
                    'nivel_desempeno': nivel_from_puntaje(puntaje),
                    'het_estudiantil': round(puntaje / 100 * 50, 2),
                    'comp_hetero_est': round(puntaje, 2),
                    'sexo':           s.get('genero', '') if s else '',
                    'antiguedad_anos': s.get('antiguedad_anos') if s else None,
                    'funcion_docente': s.get('funcion', 'DOCENCIA') if s else 'DOCENCIA',
                    'archivo_fuente': os.path.basename(fpath),
                }
                recs_360.append(rec)

    except Exception as e:
        print(f"  ERROR procesando {os.path.basename(fpath)}: {e}")
        import traceback; traceback.print_exc()

    return meipa_recs, recs_360

# ══════════════════════════════════════════════════════════════════════════════
# 2. HETEROEVALUACION 202456.xlsx (period 202456, anio 2024)
# ══════════════════════════════════════════════════════════════════════════════
print("=== 2. HETEROEVALUACION 202456 ===")
fpath_56 = os.path.join(BASE, 'HETEROEVALUACION 202456.xlsx')
m56, r56 = process_hetero_xlsx(fpath_56, '202456')
records.extend(m56)
records.extend(r56)
print(f"  202456 MEIPA: {len(m56)}, 360: {len(r56)}")

# ══════════════════════════════════════════════════════════════════════════════
# 3. HETEROEVALUACION 202466.xlsx (period 202466, anio 2024)
# ══════════════════════════════════════════════════════════════════════════════
print("=== 3. HETEROEVALUACION 202466 ===")
fpath_66 = os.path.join(BASE, 'HETEROEVALUACION 202466.xlsx')
m66, r66 = process_hetero_xlsx(fpath_66, '202466')
records.extend(m66)
records.extend(r66)
print(f"  202466 MEIPA: {len(m66)}, 360: {len(r66)}")

# ══════════════════════════════════════════════════════════════════════════════
# 4. 360 — RESULTADO GENERAL 202402 MECDI
# ══════════════════════════════════════════════════════════════════════════════
print("=== 4. 360 — MECDI 202402 ===")

def find_header_row(df_raw):
    for i, row in df_raw.iterrows():
        vals = [str(v).lower() for v in row.tolist()]
        if any('evaluado' in v or 'apellido' in v or 'nombre' in v for v in vals):
            return i
    return 0

def find_col(df, keywords):
    for c in df.columns:
        cl = str(c).lower()
        if any(k in cl for k in keywords):
            return c
    return None

try:
    rg_path = os.path.join(BASE, 'RESULTADO GENERAL 202402 MECDI 1.xlsx')
    xl_rg   = pd.ExcelFile(rg_path, engine='openpyxl')

    sheets_rg = {}
    for sh in xl_rg.sheet_names:
        raw = pd.read_excel(xl_rg, sheet_name=sh, header=None, nrows=15)
        hr  = find_header_row(raw)
        df  = pd.read_excel(xl_rg, sheet_name=sh, header=hr)
        cols = []
        seen = {}
        for c in df.columns:
            cs = str(c).strip()
            if cs in seen:
                seen[cs] += 1; cols.append(f"{cs}_{seen[cs]}")
            else:
                seen[cs] = 0; cols.append(cs)
        df.columns = cols
        sheets_rg[sh] = df

    df_s1     = sheets_rg.get('Sheet 1', sheets_rg[list(sheets_rg.keys())[0]])
    col_ced   = find_col(df_s1, ['evaluado', 'cedula', 'cedula_eval'])
    col_apel  = find_col(df_s1, ['apellido'])
    col_nom   = find_col(df_s1, ['nombre'])
    col_edad  = find_col(df_s1, ['edad'])
    col_gen   = find_col(df_s1, ['genero', 'género', 'sexo'])
    col_carr  = find_col(df_s1, ['carrera'])
    col_tserv = find_col(df_s1, ['servicio'])
    col_nivel = find_col(df_s1, ['estudio'])
    col_grado = find_col(df_s1, ['grado'])
    col_modal = find_col(df_s1, ['modalidad'])

    demog_mecdi = {}
    for _, row in df_s1.iterrows():
        ced_raw = clean_cedula(row.get(col_ced, '')) if col_ced else ''
        if not ced_raw:
            continue
        demog_mecdi[ced_raw] = {
            'apellidos': clean_nombre(row.get(col_apel)) if col_apel else '',
            'nombres':   clean_nombre(row.get(col_nom))  if col_nom  else '',
            'edad':      None,
            'sexo':      clean_nombre(row.get(col_gen))  if col_gen  else '',
            'carrera':   clean_nombre(row.get(col_carr)) if col_carr else '',
            'tserv':     clean_nombre(row.get(col_tserv))if col_tserv else '',
            'nivel_est': clean_nombre(row.get(col_nivel))if col_nivel else '',
            'grado':     clean_nombre(row.get(col_grado))if col_grado else '',
            'modal':     clean_nombre(row.get(col_modal))if col_modal else '',
        }
        try:
            ed = row.get(col_edad) if col_edad else None
            demog_mecdi[ced_raw]['edad'] = int(float(ed)) if ed and str(ed) not in ('nan','') else None
        except:
            pass

    # Component sheets
    sheets_data = {}
    for sh in list(sheets_rg.keys())[1:]:
        df_sh  = sheets_rg[sh]
        c_ced  = find_col(df_sh, ['evaluado', 'cedula'])
        c_het  = find_col(df_sh, ['het_est', 'het est', 'docgrado_het'])
        c_par  = find_col(df_sh, ['evalpar', 'eval_par', 'docgrado_eval'])
        c_aul  = find_col(df_sh, ['aulavir', 'aula_vir', 'docgrado_aula'])
        c_aut  = find_col(df_sh, ['autoeval', 'auto_eval', 'docgrado_auto'])
        c_tot  = find_col(df_sh, ['total', 'total_grado', 'puntaje'])
        c_res  = find_col(df_sh, ['resultado', 'nivel'])
        if c_ced:
            sheets_data[sh] = {'df': df_sh, 'ced': c_ced, 'het': c_het,
                                'par': c_par, 'aul': c_aul, 'aut': c_aut,
                                'tot': c_tot, 'res': c_res}

    comp_data_mecdi = {}
    for sh, info in sheets_data.items():
        df_sh = info['df']
        for _, row in df_sh.iterrows():
            ced = clean_cedula(row.get(info['ced'], '')) if info['ced'] else ''
            if not ced:
                continue
            het = pd.to_numeric(row.get(info['het']), errors='coerce') if info['het'] else np.nan
            par = pd.to_numeric(row.get(info['par']), errors='coerce') if info['par'] else np.nan
            aul = pd.to_numeric(row.get(info['aul']), errors='coerce') if info['aul'] else np.nan
            aut = pd.to_numeric(row.get(info['aut']), errors='coerce') if info['aut'] else np.nan
            tot = pd.to_numeric(row.get(info['tot']), errors='coerce') if info['tot'] else np.nan
            res = clean_nombre(row.get(info['res'])) if info['res'] else ''
            if ced not in comp_data_mecdi:
                comp_data_mecdi[ced] = {'het':[],'par':[],'aul':[],'aut':[],'tot':[],'res': res}
            for k, v in [('het',het),('par',par),('aul',aul),('aut',aut),('tot',tot)]:
                if not pd.isna(v):
                    comp_data_mecdi[ced][k].append(float(v))
            if res:
                comp_data_mecdi[ced]['res'] = res

    n_mecdi = 0
    for ced, scores in comp_data_mecdi.items():
        dm   = demog_mecdi.get(ced, {})
        het  = float(np.mean(scores['het'])) if scores['het'] else 0.0
        par  = float(np.mean(scores['par'])) if scores['par'] else 0.0
        aul  = float(np.mean(scores['aul'])) if scores['aul'] else 0.0
        aut  = float(np.mean(scores['aut'])) if scores['aut'] else 0.0
        tot  = float(np.mean(scores['tot'])) if scores['tot'] else (het + par + aul + aut)
        nivel = scores['res'] or nivel_from_puntaje(tot)
        carr  = dm.get('carrera', '')
        fac   = map_facultad(carr)
        nombre = build_nombre(ced, f"{dm.get('apellidos','')} {dm.get('nombres','')}".strip())
        s = staff_lookup.get(ced, {})

        rec = {
            'docente_nombre': nombre,
            'facultad':       fac,
            'carrera':        carr,
            'periodo':        '202402',
            'anio':           2024,
            'modelo':         'docencia',
            'sistema':        '360',
            'sexo':           dm.get('sexo','') or (s.get('genero','') if s else ''),
            'edad':           dm.get('edad'),
            'tiempo_servicio': dm.get('tserv',''),
            'nivel_estudio':   dm.get('nivel_est',''),
            'grado':           dm.get('grado',''),
            'modalidad':       dm.get('modal',''),
            'cedula':          ced,
            'het_estudiantil': round(het, 2),
            'eval_pares':      round(par, 2),
            'aula_virtual':    round(aul, 2),
            'autoevaluacion':  round(aut, 2),
            'puntaje_100':     round(tot, 2),
            'promedio':        round(tot / 100 * 5, 2),
            'nivel_desempeno': nivel,
            'comp_auto':       round(aut / 10 * 100, 2) if aut else 0,
            'comp_pares':      round(par / 20 * 100, 2) if par else 0,
            'comp_hetero_est': round(het / 50 * 100, 2) if het else 0,
            'antiguedad_anos': s.get('antiguedad_anos') if s else None,
            'funcion_docente': s.get('funcion', 'DOCENCIA') if s else 'DOCENCIA',
            'archivo_fuente':  'RESULTADO GENERAL 202402 MECDI 1.xlsx',
        }
        records.append(rec)
        n_mecdi += 1

    print(f"  MECDI 202402: {n_mecdi} docentes")
except Exception as e:
    print(f"  ERROR MECDI 202402: {e}")
    import traceback; traceback.print_exc()

# ══════════════════════════════════════════════════════════════════════════════
# 5. 360 — Eval detalladas 2025_02
# ══════════════════════════════════════════════════════════════════════════════
print("=== 5. 360 — Eval Detalladas 2025_02 ===")

MAX_CAL_BY_INSTR = {3: 4, 10: 4, 11: 4, 12: 4, 13: 4}

INSTR_MODEL_MAP = {
    1:   ('docencia',     'auto',       20),
    2:   ('docencia',     'pares',      20),
    3:   ('docencia',     'aula',       10),
    5:   ('abp',          'auto',       20),
    10:  ('investigacion','auto',       20),
    11:  ('investigacion','hetero_dir', 50),
    12:  ('investigacion','pares',      15),
    13:  ('investigacion','hetero_dec', 15),
    14:  ('vinculacion',  'auto',       20),
    15:  ('vinculacion',  'hetero_dir', 15),
    16:  ('gestion',      'auto',       20),
    17:  ('gestion',      'hetero_dir', 50),
    4:   ('gestion',      'hetero_est', 30),
    170: ('vinculacion',  'hetero_inv', 15),
}

MODEL_WEIGHTS = {
    'docencia':      {'auto': 20, 'pares': 20, 'aula': 10, 'hetero_est': 50},
    'abp':           {'auto': 20, 'pares': 20, 'aula': 10, 'hetero_est': 50},
    'investigacion': {'auto': 20, 'hetero_dir': 50, 'pares': 15, 'hetero_dec': 15},
    'vinculacion':   {'auto': 20, 'hetero_dir': 15, 'hetero_est': 50, 'hetero_inv': 15},
    'gestion':       {'auto': 20, 'hetero_dir': 50, 'hetero_est': 30},
}

model_scores = {}  # {(ced, modelo): {nombre, programa, scores:{comp:{puntaje, peso}}}}

try:
    eval_frames = []
    for fname in os.listdir(EVAL_DIR):
        if fname.endswith('.xlsx'):
            df_tmp = pd.read_excel(os.path.join(EVAL_DIR, fname), engine='openpyxl')
            eval_frames.append(df_tmp)

    if eval_frames:
        df_eval = pd.concat(eval_frames, ignore_index=True)

        df_eval['cal_norm']  = pd.to_numeric(df_eval['calificacion'], errors='coerce').fillna(0)
        df_eval['peso_num']  = pd.to_numeric(df_eval['peso'], errors='coerce').fillna(0)
        df_eval['max_cal']   = df_eval['cod_instrumento'].apply(
            lambda c: MAX_CAL_BY_INSTR.get(int(c) if str(c).isdigit() else 0, 3))
        df_eval['contrib']   = (df_eval['cal_norm'] / df_eval['max_cal'].replace(0,1)) * df_eval['peso_num']
        df_eval['_cedula']   = df_eval['usuario_evaluado'].astype(str).str.strip().str.lstrip('0')

        by_instr = df_eval.groupby(
            ['_cedula', 'apellidos_evaluado', 'nombres_evaluado', 'programa', 'cod_instrumento']
        ).agg(
            score=('contrib', 'sum'),
            max_score=('peso_num', 'sum'),
        ).reset_index()
        by_instr['puntaje_100'] = (
            by_instr['score'] / by_instr['max_score'].replace(0, 1) * 100
        ).round(2)

        for _, row in by_instr.iterrows():
            ced  = str(row['_cedula']).strip()
            try:
                cod = int(float(row['cod_instrumento']))
            except:
                continue
            if cod not in INSTR_MODEL_MAP:
                continue
            modelo, comp, peso_model = INSTR_MODEL_MAP[cod]
            key = (ced, modelo)
            if key not in model_scores:
                nombre_ev = f"{clean_nombre(row['apellidos_evaluado'])} {clean_nombre(row['nombres_evaluado'])}".strip()
                model_scores[key] = {
                    'nombre':   build_nombre(ced, nombre_ev),
                    'programa': clean_nombre(row['programa']),
                    'scores':   {},
                }
            model_scores[key]['scores'][comp] = {
                'puntaje': float(row['puntaje_100']),
                'peso':    peso_model,
            }

        # Propagate instrument 2 (pares) and 3 (aula) to ABP model
        for _, row in by_instr.iterrows():
            ced = str(row['_cedula']).strip()
            try:
                cod = int(float(row['cod_instrumento']))
            except:
                continue
            key_abp = (ced, 'abp')
            if cod == 2 and key_abp in model_scores:
                model_scores[key_abp]['scores']['pares'] = {
                    'puntaje': float(row['puntaje_100']), 'peso': 20}
            if cod == 3 and key_abp in model_scores:
                model_scores[key_abp]['scores']['aula'] = {
                    'puntaje': float(row['puntaje_100']), 'peso': 10}

    print(f"  Modelos en eval_detalladas: {set(k[1] for k in model_scores.keys())}")
except Exception as e:
    print(f"  ERROR eval_detalladas: {e}")
    import traceback; traceback.print_exc()

# ══════════════════════════════════════════════════════════════════════════════
# 6. 360 — CSV Heteroevaluación 2025 (202556 + 202566)
# ══════════════════════════════════════════════════════════════════════════════
print("=== 6. 360 — CSV Hetero 2025 ===")

INSTR_MODELO_CSV = {
    norm_str('Heteroevaluación Grado Nuevo Docencia Esmeraldas'): ('docencia', 'hetero_est'),
    norm_str('Heteroevaluación Grado Nuevo Docencia Quito'):      ('docencia', 'hetero_est'),
    norm_str('Heteroevalauación Grado Nuevo ABP Quito'):          ('abp',      'hetero_est'),
    norm_str('Heteroevaluación Grado Nuevo Vinculación Quito'):   ('vinculacion','hetero_est'),
    norm_str('Heteroevalauación Grado Nuevo Servicios Quito'):    ('docencia', 'hetero_est'),
    norm_str('Heteroevaluacion Grado Nuevo Docencia Esmeraldas'): ('docencia', 'hetero_est'),
    norm_str('Heteroevaluacion Grado Nuevo Docencia Quito'):      ('docencia', 'hetero_est'),
    norm_str('Heteroevaluacion Grado Nuevo ABP Quito'):           ('abp',      'hetero_est'),
    norm_str('Heteroevaluacion Grado Nuevo Vinculacion Quito'):   ('vinculacion','hetero_est'),
    norm_str('Heteroevaluacion Grado Nuevo Servicios Quito'):     ('docencia', 'hetero_est'),
}

try:
    all_csv_frames = []
    for f in os.listdir(BASE):
        if f.endswith('.csv') and ('202566' in f or '202556' in f):
            periodo_code = '202566' if '202566' in f else '202556'
            fpath = os.path.join(BASE, f)
            try:
                df_tmp = pd.read_csv(fpath, sep=';', encoding='utf-8-sig', decimal=',', on_bad_lines='skip')
                df_tmp['_periodo_code'] = periodo_code
                all_csv_frames.append(df_tmp)
                print(f"  CSV loaded: {f} ({len(df_tmp)} rows)")
            except Exception as e:
                print(f"  Error CSV {f}: {e}")

    if all_csv_frames:
        df_csv_all = pd.concat(all_csv_frames, ignore_index=True)
        df_csv_all['_cedula'] = df_csv_all['NUM_DOCU'].astype(str).str.strip().str.lstrip('0')
        df_csv_all['_nombre'] = (
            df_csv_all['SPRIDEN_LAST_NAME'].astype(str).str.strip() + ' ' +
            df_csv_all['SPRIDEN_FIRST_NAME'].astype(str).str.strip()
        )
        df_csv_all['_puntaje']   = pd.to_numeric(df_csv_all['PUNTAJE'], errors='coerce')
        df_csv_all['_dept']      = df_csv_all.get('STVDEPT_DESC', pd.Series([''] * len(df_csv_all))).astype(str)
        df_csv_all['_instr_norm']= df_csv_all['INSTRUMENTO'].apply(norm_str)

        def first_mode(x):
            m = x.mode()
            return m.iloc[0] if len(m) > 0 else ''

        agg_csv = df_csv_all.groupby(['_cedula', '_instr_norm']).agg(
            nombre=('_nombre', first_mode),
            puntaje=('_puntaje', 'mean'),
            dept=('_dept', first_mode),
        ).reset_index()

        for _, row in agg_csv.iterrows():
            instr_n = str(row['_instr_norm']).strip()
            if instr_n not in INSTR_MODELO_CSV:
                continue
            modelo, comp = INSTR_MODELO_CSV[instr_n]
            ced = str(row['_cedula']).strip()
            key = (ced, modelo)
            nombre_ev = build_nombre(ced, row['nombre'])
            if key not in model_scores:
                model_scores[key] = {
                    'nombre':   nombre_ev,
                    'programa': str(row.get('dept','')).strip(),
                    'scores':   {},
                }
            model_scores[key]['scores']['hetero_est'] = {
                'puntaje': float(row['puntaje']) if not pd.isna(row['puntaje']) else 0.0,
                'peso':    50,
            }
            if not model_scores[key]['nombre']:
                model_scores[key]['nombre'] = nombre_ev

    print(f"  (ced,modelo) pares totales en model_scores: {len(model_scores)}")
except Exception as e:
    print(f"  ERROR CSV hetero: {e}")
    import traceback; traceback.print_exc()

# ══════════════════════════════════════════════════════════════════════════════
# 7. Calcular puntajes finales 2025 (360)
# ══════════════════════════════════════════════════════════════════════════════
print("=== 7. Calculando puntajes finales 360 — 2025 ===")

n_2025 = 0
for (ced, modelo), info in model_scores.items():
    scores  = info['scores']
    weights = MODEL_WEIGHTS.get(modelo, {})
    if not scores:
        continue

    total_peso  = 0
    total_score = 0.0
    comp_vals   = {}
    for comp, w in weights.items():
        if comp in scores:
            total_score += scores[comp]['puntaje'] * w / 100
            total_peso  += w
            comp_vals[comp] = scores[comp]['puntaje']

    if total_peso == 0:
        continue

    puntaje  = round(total_score / total_peso * 100, 2)
    nombre   = info['nombre'] or build_nombre(ced)
    programa = info['programa']
    fac      = map_facultad(programa)
    s        = staff_lookup.get(ced, {})

    rec = {
        'docente_nombre': nombre,
        'facultad':       fac,
        'carrera':        programa,
        'periodo':        '202502',
        'anio':           2025,
        'modelo':         modelo,
        'sistema':        '360',
        'cedula':         ced,
        'puntaje_100':    puntaje,
        'promedio':       round(puntaje / 100 * 5, 2),
        'nivel_desempeno': nivel_from_puntaje(puntaje),
        'comp_auto':       round(comp_vals.get('auto', 0), 2),
        'comp_pares':      round(comp_vals.get('pares', 0), 2),
        'comp_hetero_dir': round(comp_vals.get('hetero_dir', 0), 2),
        'comp_hetero_est': round(comp_vals.get('hetero_est', comp_vals.get('hetero_dec', 0)), 2),
        'antiguedad_anos': s.get('antiguedad_anos') if s else None,
        'funcion_docente': s.get('funcion', 'DOCENCIA') if s else 'DOCENCIA',
        'sexo':            s.get('genero', '') if s else '',
        'archivo_fuente':  'eval_detalladas_2025 + CSV_202566',
    }

    if modelo in ('docencia', 'abp'):
        h_est = comp_vals.get('hetero_est', 0)
        rec['het_estudiantil'] = round(h_est / 100 * 50, 2)
        rec['eval_pares']      = round(comp_vals.get('pares', 0) / 100 * 20, 2)
        rec['aula_virtual']    = round(comp_vals.get('aula', 0) / 100 * 20, 2)
        rec['autoevaluacion']  = round(comp_vals.get('auto', 0) / 100 * 10, 2)

    records.append(rec)
    n_2025 += 1

print(f"  2025 registros 360: {n_2025}")

# ══════════════════════════════════════════════════════════════════════════════
# 8. Guardar en base de datos
# ══════════════════════════════════════════════════════════════════════════════
print("=== 8. Guardando en base de datos ===")

VALID_COLS = {c.name for c in Evaluacion.__table__.columns} - {'id', 'fecha_proceso'}

db = Session()
saved = 0
for rec in records:
    clean = {}
    for k, v in rec.items():
        if k not in VALID_COLS:
            continue
        if v is None:
            clean[k] = None
        elif isinstance(v, float) and np.isnan(v):
            clean[k] = None
        elif hasattr(v, 'item'):
            clean[k] = v.item()
        else:
            clean[k] = v
    try:
        db.add(Evaluacion(**clean))
        saved += 1
    except Exception as e:
        print(f"  Error guardando registro ced={rec.get('cedula')}: {e}")

db.commit()
db.close()

# ── Summary ────────────────────────────────────────────────────────────────────
from collections import Counter
by_sistema = Counter(r.get('sistema','?') for r in records)
by_modelo  = Counter(r.get('modelo', '?') for r in records)
by_anio    = Counter(r.get('anio',   '?') for r in records)

print(f"\n{'='*60}")
print(f"Total registros guardados: {saved}")
print(f"Por sistema: {dict(by_sistema)}")
print(f"Por modelo:  {dict(by_modelo)}")
print(f"Por año:     {dict(by_anio)}")
print(f"{'='*60}")
print("OK — Base de datos actualizada.")
