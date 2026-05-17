"""
Carga datos de personal desde edades.xlsx y reportes de personal anuales.
Upsert en tablas: docentes, personal_periodo.
"""
import os
import hashlib
import warnings
from datetime import datetime, date
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import text

from app.models.docente import Docente, PersonalPeriodo
from app.etl.registry import map_facultad

warnings.filterwarnings("ignore")

# Columnas que esperamos en edades.xlsx / reportes de personal
_COL_CEDULA   = "Cédula o Pasaporte"
_COL_AP1      = "1° Apellido"
_COL_AP2      = "Segundo apellido"
_COL_NOM1     = "Primer Nombre"
_COL_NOM2     = "Segundo Nombre"
_COL_GENERO   = "Género"
_COL_FNAC     = "Fecha de nacimiento"
_COL_ETNIA    = "Etnia"
_COL_NACION   = "Nacionalidad"
_COL_EMAIL_I  = "Email institucional"
_COL_EMAIL_P  = "Email personal"
_COL_UNIDAD   = "Unidad organizativa"
_COL_FUNCION  = "Función"
_COL_DEDIC    = "Tiempo de dedicación"
_COL_CONTRATO = "Texto clase contrato"
_COL_POSICION = "Posición"
_COL_INICIO   = "Fecha del último Ingreso a la PUCE"
_COL_FIN      = "fecha fin ultimo ingreso"
_COL_EDAD     = "Edad"
_COL_NIV_INS  = "Nivel de Instrucción"
_COL_GRADO_INS= "Grado de Instrucción"
_COL_TITULO   = "Nombre del Titulo"
_COL_SENESCYT = "Número SENESCYT"
_COL_INST_TIT = "Nombre Institución"


def _safe_date(val) -> Optional[date]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (datetime, date)):
        return val if isinstance(val, date) else val.date()
    try:
        return pd.to_datetime(val).date()
    except Exception:
        return None


def _safe_str(val) -> Optional[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return str(val).strip() or None


def _safe_float(val) -> Optional[float]:
    try:
        f = float(val)
        return None if pd.isna(f) else f
    except Exception:
        return None


def _calc_antiguedad(fecha_inicio, fecha_referencia: date) -> Optional[float]:
    d = _safe_date(fecha_inicio)
    if not d:
        return None
    delta = fecha_referencia - d
    return round(delta.days / 365.25, 2)


def _get_col(df: pd.DataFrame, *names) -> Optional[pd.Series]:
    """Devuelve la primera columna que exista en el DataFrame."""
    for n in names:
        if n in df.columns:
            return df[n]
    return None


def load_personal(ruta_excel: str, periodo_codigo: str, db: Session) -> dict:
    """
    Carga un archivo de personal (edades.xlsx o reporte PUCE) para un período.
    Hace upsert en docentes y personal_periodo.
    Retorna contadores: {docentes_nuevos, docentes_actualizados, snapshots}
    """
    print(f"[Personal] Cargando {os.path.basename(ruta_excel)} para período {periodo_codigo}")

    df = pd.read_excel(ruta_excel, dtype=str)
    df.columns = [str(c).strip() for c in df.columns]

    # Normalizar nombres de columnas con caracteres especiales
    rename = {}
    for col in df.columns:
        clean = col.replace("\xa0", " ").strip()
        if clean != col:
            rename[col] = clean
    if rename:
        df.rename(columns=rename, inplace=True)

    # Fecha de referencia para calcular antigüedad en ese período
    ref_year  = int(periodo_codigo[:4])
    ref_month = int(periodo_codigo[4:]) * 6 - 5  # 01→ enero, 02→ julio
    ref_date  = date(ref_year, ref_month, 1)

    docentes_nuevos = 0
    docentes_act    = 0
    snapshots       = 0
    cedulas_vistas  = set()   # dedup: misma cédula puede aparecer varias veces en el archivo

    for _, row in df.iterrows():
        cedula = _safe_str(row.get("Cédula o Pasaporte") or row.get("Cedula o Pasaporte"))
        if not cedula or cedula.lower() in ("cédula", "cedula", "nan"):
            continue

        ap1   = _safe_str(row.get("1° Apellido") or row.get("1  Apellido") or row.get("Primer Apellido"))
        ap2   = _safe_str(row.get("Segundo apellido") or row.get("Segundo Apellido") or "")
        nom1  = _safe_str(row.get("Primer Nombre") or "")
        nom2  = _safe_str(row.get("Segundo Nombre") or "")
        nombre_completo = " ".join(filter(None, [ap1, ap2, nom1, nom2])).strip()

        # ── Upsert en docentes (merge maneja duplicados de PK) ───────────────
        doc_data = dict(
            cedula              = cedula,
            apellidos           = " ".join(filter(None, [ap1, ap2])).strip(),
            nombres             = " ".join(filter(None, [nom1, nom2])).strip(),
            nombre_completo     = nombre_completo,
            email_institucional = _safe_str(row.get("Email institucional")),
            email_personal      = _safe_str(row.get("Email personal")),
            genero              = _safe_str(row.get("Género") or row.get("Genero")),
            fecha_nacimiento    = _safe_date(row.get("Fecha de nacimiento")),
            etnia               = _safe_str(row.get("Etnia")),
            nacionalidad        = _safe_str(row.get("Nacionalidad")),
        )
        # Dedup: cada cédula se procesa UNA sola vez por llamada
        if cedula in cedulas_vistas:
            continue
        cedulas_vistas.add(cedula)

        # ── Upsert en docentes ────────────────────────────────────────────────
        db.merge(Docente(**doc_data))
        docentes_nuevos += 1

        # ── Upsert en personal_periodo ────────────────────────────────────────
        unidad  = _safe_str(row.get("Unidad organizativa"))
        funcion = _safe_str(row.get("Función") or row.get("Funcion"))
        dedic   = _safe_str(row.get("Tiempo de dedicación") or row.get("Tiempo de dedicacion"))
        if dedic:
            dedic_u = dedic.upper()
            if "COMPLETO" in dedic_u or dedic_u == "TC":
                dedic = "TC"
            elif "MEDIO" in dedic_u or dedic_u == "MT":
                dedic = "MT"
            elif "PARCIAL" in dedic_u or dedic_u == "TP":
                dedic = "TP"

        fecha_inicio = _safe_date(row.get("Fecha del último Ingreso a la PUCE")
                                  or row.get("Fecha del  ltimo Ingreso a la PUCE"))
        antiguedad   = _calc_antiguedad(fecha_inicio, ref_date)

        try:
            edad_raw = row.get("Edad")
            edad_val = int(float(edad_raw)) if edad_raw and str(edad_raw) not in ("nan", "") else None
        except (ValueError, TypeError):
            edad_val = None

        snap_data = dict(
            cedula              = cedula,
            periodo_codigo      = periodo_codigo,
            unidad_organizativa = unidad,
            facultad            = map_facultad(unidad),
            funcion             = funcion,
            dedicacion          = dedic,
            tipo_contrato       = _safe_str(row.get("Texto clase contrato")),
            posicion            = _safe_str(row.get("Posición") or row.get("Posicion")),
            fecha_ingreso       = fecha_inicio,
            antiguedad_anos     = antiguedad,
            edad_en_periodo     = edad_val,
            nivel_instruccion   = _safe_str(row.get("Nivel de Instrucción") or row.get("Nivel de Instruccion")),
            grado_instruccion   = _safe_str(row.get("Grado de Instrucción") or row.get("Grado de Instruccion")),
            titulo              = _safe_str(row.get("Nombre del Titulo")),
            senescyt            = _safe_str(row.get("Número SENESCYT") or row.get("Numero SENESCYT")),
            institucion_titulo  = _safe_str(row.get("Nombre Institución") or row.get("Nombre Institucion")),
        )

        # PersonalPeriodo tiene PK autoincrement → buscar por UNIQUE y actualizar/insertar
        snap = db.query(PersonalPeriodo).filter_by(
            cedula=cedula, periodo_codigo=periodo_codigo
        ).first()
        if snap is None:
            db.add(PersonalPeriodo(**snap_data))
        else:
            for k, v in snap_data.items():
                if v is not None:
                    setattr(snap, k, v)
        snapshots += 1

    db.commit()
    print(f"[Personal] OK: {docentes_nuevos} docentes, {snapshots} snapshots periodo {periodo_codigo}")
    return {"docentes_nuevos": docentes_nuevos, "docentes_actualizados": docentes_act, "snapshots": snapshots}
