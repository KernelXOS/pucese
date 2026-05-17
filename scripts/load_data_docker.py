"""
Script para cargar datos a PostgreSQL en Docker.
Adapta construir_multi_modelo.py para conectarse a la BD dockerizada.
"""
import os
import sys
import re
import warnings
warnings.filterwarnings('ignore')

# Agregar backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.evaluacion import Base, Evaluacion

# ════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN DE BD — PostgreSQL en Docker
# ════════════════════════════════════════════════════════════════════════════
DB_URL = "postgresql://postgres:postgres@localhost:5433/evaluacion_docente"

try:
    engine = create_engine(DB_URL)
    engine.connect()
    print("✓ Conexión a PostgreSQL exitosa")
except Exception as e:
    print(f"✗ Error conectando a PostgreSQL: {e}")
    print("Asegúrate que docker-compose está corriendo")
    sys.exit(1)

# Crear tablas si no existen
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

BASE = r'C:\Users\KernelXos\Desktop\DATOS_DOCENTE'

# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

FACULTAD_MAP = {
    'CONTABILIDAD': 'Ciencias Administrativas',
    'ADMINISTRACION': 'Ciencias Administrativas',
    'ADMINISTRACI': 'Ciencias Administrativas',
    'TURISMO': 'Turismo y Hotelería',
    'HOTELERIA': 'Turismo y Hotelería',
    'MEDICINA': 'Medicina',
    'LABORATORIO CLINICO': 'Medicina',
    'LABORATORIO CL': 'Medicina',
    'ENFERMERIA': 'Salud',
    'ENFERMERÍA': 'Salud',
    'NUTRICION': 'Salud',
    'NUTRICIÓN': 'Salud',
    'PSICOLOGIA': 'Psicología',
    'PSICOLOGÍA': 'Psicología',
    'DERECHO': 'Derecho',
    'INGENIERIA': 'Ingeniería',
    'INGENIERÍA': 'Ingeniería',
    'SISTEMAS': 'Ingeniería',
    'COMPUTACION': 'Ingeniería',
    'COMPUTACIÓN': 'Ingeniería',
    'EDUCACION': 'Educación',
    'EDUCACIÓN': 'Educación',
    'AGRO': 'Agroindustria',
    'MENTOR': 'Otras Ciencias',
    'NO DEFINIDA': 'Otras Ciencias',
    'PUCETEC': 'Otras Ciencias',
}

def map_facultad(text: str) -> str:
    if not text or pd.isna(text):
        return 'Otras Ciencias'
    t = str(text).upper().strip()
    for k, v in FACULTAD_MAP.items():
        if k in t:
            return v
    return 'Otras Ciencias'

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

def nivel_from_puntaje(p: float) -> str:
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return 'Sin datos'
    if p >= 90: return 'Excelente'
    if p >= 75: return 'Bueno'
    if p >= 60: return 'Regular'
    return 'Deficiente'

def norm_str(s) -> str:
    import unicodedata
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower().strip()

# ════════════════════════════════════════════════════════════════════════════
# CARGAR DATOS
# ════════════════════════════════════════════════════════════════════════════

print("\n=== INICIANDO CARGA DE DATOS ===\n")

records = []

# 1. MEIPA — CONSOLIDADO HETEROEVALUACIÓN
print("1. Cargando MEIPA Consolidado...")
try:
    excel_file = os.path.join(BASE, 'CONSOLIDADO HETEROEVALUACIÓN.xlsx')
    if os.path.exists(excel_file):
        xl_c = pd.ExcelFile(excel_file, engine='openpyxl')
        df_datos = pd.read_excel(xl_c, sheet_name='DATOS', dtype=str)
        df_datos.columns = [c.strip() for c in df_datos.columns]

        col_map = {norm_str(c): c for c in df_datos.columns}

        def gc(keys):
            for k in keys:
                nk = norm_str(k)
                if nk in col_map:
                    return col_map[nk]
            for k in keys:
                nk = norm_str(k)
                for ck, cv in col_map.items():
                    if nk in ck:
                        return cv
            return None

        col_ced = gc(['cedula'])
        col_nom = gc(['apellidos y nombres', 'apellidos'])
        col_per = gc(['periodo evaluado', 'periodo'])
        col_pun = gc(['promedio de puntaje', 'puntaje'])

        if not col_ced: col_ced = df_datos.columns[1]
        if not col_nom: col_nom = df_datos.columns[2]
        if not col_pun: col_pun = df_datos.columns[-1]

        for _, row in df_datos.iterrows():
            ced = clean_cedula(row[col_ced])
            if not ced:
                continue

            nom = clean_nombre(row[col_nom])
            per = str(row[col_per])
            pun = safe_float(row[col_pun])

            if not pun:
                continue

            anio = int(per[:4]) if len(per) >= 4 and per[:4].isdigit() else 2024

            records.append({
                'cedula': ced,
                'docente_nombre': nom,
                'periodo': per,
                'anio': anio,
                'puntaje_100': pun,
                'het_estudiantil': pun * 0.5,
                'eval_pares': pun * 0.2,
                'aula_virtual': pun * 0.1,
                'autoevaluacion': pun * 0.2,
                'modelo': 'docencia',
                'sistema': 'meipa',
                'facultad': 'Ciencias Administrativas',
                'nivel_desempeno': nivel_from_puntaje(pun),
            })

        print(f"   ✓ {len(records)} registros cargados")
    else:
        print(f"   ! Archivo no encontrado: {excel_file}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# 2. RESULTADO GENERAL 360 MECDI
print("2. Cargando 360 MECDI...")
try:
    excel_file = os.path.join(BASE, 'RESULTADO GENERAL 202402 MECDI 1.xlsx')
    if os.path.exists(excel_file):
        df_360 = pd.read_excel(excel_file, dtype=str)
        df_360.columns = [c.strip() for c in df_360.columns]

        col_map = {norm_str(c): c for c in df_360.columns}

        def gc(keys):
            for k in keys:
                nk = norm_str(k)
                if nk in col_map:
                    return col_map[nk]
            return None

        col_ced = gc(['cedula', 'identificación'])
        col_nom = gc(['docente', 'nombre'])
        col_pun = gc(['puntaje', 'promedio', 'puntuación'])
        col_fac = gc(['facultad', 'facultad'])

        if col_ced and col_nom and col_pun:
            for _, row in df_360.iterrows():
                ced = clean_cedula(row[col_ced]) if col_ced in row else ''
                if not ced:
                    continue

                nom = clean_nombre(row[col_nom]) if col_nom in row else ''
                pun = safe_float(row[col_pun])
                fac = map_facultad(row[col_fac]) if col_fac and col_fac in row else 'Otras Ciencias'

                if not pun:
                    continue

                records.append({
                    'cedula': ced,
                    'docente_nombre': nom,
                    'periodo': '202402',
                    'anio': 2024,
                    'puntaje_100': pun,
                    'het_estudiantil': pun * 0.5,
                    'eval_pares': pun * 0.2,
                    'aula_virtual': pun * 0.1,
                    'autoevaluacion': pun * 0.2,
                    'modelo': 'docencia',
                    'sistema': '360',
                    'facultad': fac,
                    'nivel_desempeno': nivel_from_puntaje(pun),
                })

        print(f"   ✓ {len([r for r in records if r['sistema'] == '360'])} registros del 360")
    else:
        print(f"   ! Archivo no encontrado: {excel_file}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# ════════════════════════════════════════════════════════════════════════════
# GUARDAR EN BD
# ════════════════════════════════════════════════════════════════════════════

if records:
    print(f"\n3. Guardando {len(records)} registros en PostgreSQL...")
    
    session = Session()
    try:
        # Limpiar tabla anterior
        session.query(Evaluacion).delete()
        session.commit()
        print("   Tabla limpiada")

        # Agregar nuevos registros
        for rec in records:
            evaluacion = Evaluacion(
                cedula=rec.get('cedula'),
                docente_nombre=rec.get('docente_nombre'),
                periodo=rec.get('periodo'),
                anio=rec.get('anio'),
                puntaje_100=rec.get('puntaje_100'),
                het_estudiantil=rec.get('het_estudiantil'),
                eval_pares=rec.get('eval_pares'),
                aula_virtual=rec.get('aula_virtual'),
                autoevaluacion=rec.get('autoevaluacion'),
                modelo=rec.get('modelo'),
                sistema=rec.get('sistema'),
                facultad=rec.get('facultad'),
                nivel_desempeno=rec.get('nivel_desempeno'),
                promedio=rec.get('puntaje_100'),
                fecha_proceso=datetime.now(),
                carrera=rec.get('facultad'),
            )
            session.add(evaluacion)

        session.commit()
        print(f"   ✓ {len(records)} registros guardados exitosamente")
        
        # Verificar datos
        count = session.query(Evaluacion).count()
        print(f"\n✓ TOTAL de registros en BD: {count}")
        
    except Exception as e:
        session.rollback()
        print(f"   ✗ Error al guardar: {e}")
    finally:
        session.close()
else:
    print("\n✗ No se cargaron registros")

print("\n=== CARGA COMPLETADA ===\n")
