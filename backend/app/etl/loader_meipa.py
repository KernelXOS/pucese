"""
Carga el archivo MEIPA consolidado que contiene los 3 períodos históricos:
202301, 202302 y 202401 en una sola hoja de Excel.

Columnas clave:
  PERÍODO ACADÉMICO | APELLIDOS Y NOMBRES | CEDULA | CARRERA | EDAD | ANTIGÜEDAD
  GENERO | NIVEL DE ESTUDIO | MODALIDAD DE SERVICIO
  Estud a Doc | Autoeval | Coord a Docente | Eval pares | Total | PROMEDIO GENERAL
"""
import re
import warnings
from datetime import date
from typing import Optional

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.models.docente import Docente, PersonalPeriodo
from app.models.puntaje import PuntajeFinal
from app.etl.registry import map_facultad, nivel_from_puntaje

warnings.filterwarnings("ignore")

# Pesos MEIPA: Estud→Doc (40%), Autoeval (20%), Coord→Doc (20%), Pares (20%)
# El Excel ya trae el Total sobre 5 → PROMEDIO_GENERAL sobre 100
MEIPA_SHEET = "RESUL.GENE 202401 202302 202301"

# Columna → campo modelo
_COL_ALIASES = {
    "PERÍODO ACADÉMICO":   "periodo",
    "PERIODO ACADÉMICO":   "periodo",
    "PERÍODO ACADEMICO":   "periodo",
    "PERIODO ACADEMICO":   "periodo",
    "PER ODO ACAD MICO":   "periodo",
    "APELLIDOS Y NOMBRES": "nombre",
    "CEDULA":              "cedula",
    "CARRERA":             "carrera",
    "EDAD":                "edad",
    "ANTIGÜEDAD":          "antiguedad",
    "ANTIGUEDAD":          "antiguedad",
    "ANTIG EDAD":          "antiguedad",
    "GENERO":              "genero",
    "GÉNERO":              "genero",
    "G NERO":              "genero",
    "NIVEL DE ESTUDIO":    "nivel_estudio",
    "MODALIDAD DE SERVICIO": "modalidad",
    "TOTAL":               "total",
    "PROMEDIO GENERAL":    "promedio_100",
}

_COL_COMP_ALIASES = {
    "ESTUD A DOC":     "het_est",
    "AUTOEVAL":        "auto",
    "COORD A DOCENTE": "coord",
    "EVAL PARES":      "pares",
}


def _norm_col(col: str) -> str:
    return re.sub(r"\s+", " ", str(col).strip().upper().replace("\n", " "))


def _parse_antiguedad(texto: str) -> Optional[float]:
    """'10 AÑOS 1 MESES' → 10.08"""
    if not texto:
        return None
    t = str(texto).upper()
    m_a = re.search(r"(\d+)\s*A", t)
    m_m = re.search(r"(\d+)\s*M", t)
    anos = int(m_a.group(1)) if m_a else 0
    meses = int(m_m.group(1)) if m_m else 0
    return round(anos + meses / 12, 2)


def _safe_float(val) -> Optional[float]:
    try:
        f = float(val)
        return None if (isinstance(f, float) and np.isnan(f)) else f
    except Exception:
        return None


def load_meipa(ruta_excel: str, db: Session) -> dict:
    """
    Lee el archivo MEIPA y carga puntajes_finales para los 3 períodos.
    Hace upsert en docentes y personal_periodo con los datos disponibles.
    """
    import os
    print(f"[MEIPA] Cargando {os.path.basename(ruta_excel)}")

    # Leer la hoja de resultados generales
    try:
        df_raw = pd.read_excel(ruta_excel, sheet_name=MEIPA_SHEET, header=None, dtype=str)
    except Exception as e:
        print(f"[MEIPA] ERROR Error leyendo Excel: {e}")
        return {"error": str(e)}

    # Encontrar fila de encabezados (la que contiene "CEDULA")
    header_row = None
    for i, row in df_raw.iterrows():
        row_vals = [str(v).upper().strip() if v else "" for v in row]
        if "CEDULA" in row_vals:
            header_row = i
            break

    if header_row is None:
        print("[MEIPA] ERROR No se encontró la fila de encabezados")
        return {"error": "header_not_found"}

    df = pd.read_excel(ruta_excel, sheet_name=MEIPA_SHEET, header=header_row, dtype=str)
    df.columns = [_norm_col(c) for c in df.columns]

    # Mapear columnas normalizadas a nombres internos
    col_map = {}
    for col in df.columns:
        alias = _COL_ALIASES.get(col)
        if alias:
            col_map[col] = alias
            continue
        for alias_key, alias_val in _COL_COMP_ALIASES.items():
            if alias_key in col:
                col_map[col] = alias_val
                break

    df.rename(columns=col_map, inplace=True)

    # Filtrar solo filas con período válido (6 dígitos numéricos)
    df = df[df.get("periodo", pd.Series(dtype=str)).apply(
        lambda x: bool(re.match(r"^\d{6}$", str(x).strip()))
    )].copy()

    if df.empty:
        print("[MEIPA] ERROR No se encontraron datos con período válido")
        return {"rows": 0}

    total_cargados = 0
    total_docentes = 0

    for _, row in df.iterrows():
        periodo_codigo = str(row.get("periodo", "")).strip()
        cedula         = str(row.get("cedula", "")).strip()
        nombre         = str(row.get("nombre", "")).strip()

        if not cedula or not periodo_codigo or cedula == "nan":
            continue

        # ── Docente ──────────────────────────────────────────────────────────
        if not db.query(Docente).filter_by(cedula=cedula).first():
            # Partir nombre en apellidos + nombres (formato: APELLIDO APELLIDO NOMBRE NOMBRE)
            partes = nombre.split()
            if len(partes) >= 2:
                apellidos = " ".join(partes[:2])
                nombres   = " ".join(partes[2:]) if len(partes) > 2 else ""
            else:
                apellidos = nombre
                nombres   = ""

            genero = str(row.get("genero", "") or "").strip()

            db.add(Docente(
                cedula          = cedula,
                apellidos       = apellidos,
                nombres         = nombres,
                nombre_completo = nombre,
                genero          = genero,
            ))
            try:
                db.flush()
                total_docentes += 1
            except Exception:
                db.rollback()
                continue

        # ── PersonalPeriodo ───────────────────────────────────────────────────
        carrera    = str(row.get("carrera", "") or "").strip()
        antiguedad = _parse_antiguedad(row.get("antiguedad"))
        try:
            edad = int(float(row.get("edad", 0) or 0))
        except (ValueError, TypeError):
            edad = None

        snap = db.query(PersonalPeriodo).filter_by(
            cedula=cedula, periodo_codigo=periodo_codigo
        ).first()

        if not snap:
            db.add(PersonalPeriodo(
                cedula              = cedula,
                periodo_codigo      = periodo_codigo,
                unidad_organizativa = carrera,
                facultad            = map_facultad(carrera),
                carrera             = carrera,
                funcion             = "DOCENCIA",
                dedicacion          = _norm_modalidad(row.get("modalidad")),
                nivel_instruccion   = str(row.get("nivel_estudio", "") or "").strip() or None,
                antiguedad_anos     = antiguedad,
                edad_en_periodo     = edad,
            ))

        # ── Puntaje final ─────────────────────────────────────────────────────
        promedio_100 = _safe_float(row.get("promedio_100"))
        if promedio_100 is None:
            total_raw = _safe_float(row.get("total"))
            if total_raw is not None:
                promedio_100 = round(total_raw * 20, 2)  # escala 5 → 100

        # Componentes individuales (escala 0-2 max por componente en MEIPA)
        het_est = _safe_float(row.get("het_est"))   # Estud a Doc (peso 40 → max ~2)
        auto    = _safe_float(row.get("auto"))       # Autoeval    (peso 20 → max ~1)
        coord   = _safe_float(row.get("coord"))      # Coord a Doc (peso 20 → max ~1)
        pares   = _safe_float(row.get("pares"))      # Eval pares  (peso 20 → max ~1)

        # Normalizar componentes a 0-100 (cada uno sobre su peso máximo)
        def comp_a_100(val, peso_max):
            if val is None:
                return None
            return round(min((val / (peso_max / 100)) * 100, 100), 2)

        comp_json = {}
        if het_est is not None: comp_json["het_est"] = round(het_est, 4)
        if auto    is not None: comp_json["auto"]    = round(auto, 4)
        if coord   is not None: comp_json["coord"]   = round(coord, 4)
        if pares   is not None: comp_json["pares"]   = round(pares, 4)

        existing = db.query(PuntajeFinal).filter_by(
            cedula=cedula, periodo_codigo=periodo_codigo, modelo="docencia"
        ).first()

        data = dict(
            cedula           = cedula,
            periodo_codigo   = periodo_codigo,
            modelo           = "docencia",
            sistema          = "meipa",
            comp_het_est     = comp_a_100(het_est, 40),
            comp_auto        = comp_a_100(auto, 20),
            comp_het_dir     = comp_a_100(coord, 20),
            comp_pares       = comp_a_100(pares, 20),
            puntaje_100      = promedio_100,
            nivel_desempeno  = nivel_from_puntaje(promedio_100),
            componentes_json = comp_json,
        )

        if existing:
            for k, v in data.items():
                if v is not None:
                    setattr(existing, k, v)
        else:
            db.add(PuntajeFinal(**data))

        total_cargados += 1

    db.commit()
    print(f"[MEIPA] OK {total_cargados} registros cargados, {total_docentes} docentes nuevos")
    return {"registros": total_cargados, "docentes_nuevos": total_docentes}


def _norm_modalidad(val) -> Optional[str]:
    if not val:
        return None
    v = str(val).upper()
    if "COMPLETO" in v: return "TC"
    if "MEDIO"    in v: return "MT"
    if "PARCIAL"  in v: return "TP"
    return str(val).strip()[:20]
