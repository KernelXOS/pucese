"""
Carga archivos del sistema 360 (raw question-level) para un período.
Inserta en respuestas_raw y calcula puntajes_instrumento y puntajes_finales.
"""
import os
import hashlib
import warnings
from datetime import datetime
from typing import Optional

import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.docente import Docente, PersonalPeriodo
from app.models.respuesta import RespuestaRaw
from app.models.puntaje import PuntajeInstrumento, PuntajeFinal
from app.etl.registry import (
    ARCHIVO_INSTRUMENTO_360, PESOS_MODELO, map_facultad, nivel_from_puntaje
)

warnings.filterwarnings("ignore")


def _hash_evaluador(evaluador: str) -> str:
    """Anonimiza el ID del evaluador con SHA-256 truncado."""
    if not evaluador:
        return ""
    return hashlib.sha256(str(evaluador).encode()).hexdigest()[:16]


def _safe_float(val) -> Optional[float]:
    try:
        f = float(val)
        return None if (isinstance(f, float) and np.isnan(f)) else f
    except Exception:
        return None


def _safe_date(val) -> Optional[datetime]:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    try:
        return pd.to_datetime(val)
    except Exception:
        return None


def _detectar_instrumento(nombre_archivo: str) -> Optional[str]:
    """Detecta cod_instrumento a partir del nombre del archivo."""
    base = os.path.splitext(os.path.basename(nombre_archivo))[0]
    # Búsqueda exacta
    if base in ARCHIVO_INSTRUMENTO_360:
        return ARCHIVO_INSTRUMENTO_360[base]
    # Búsqueda por prefijo normalizado
    base_lower = base.lower()
    for key, cod in ARCHIVO_INSTRUMENTO_360.items():
        if key.lower() == base_lower:
            return cod
        # Ej: "Eval_doc_202501_01_detallada" → match con "Eval_doc_202502_01_detallada"
        # Reemplazar período en el nombre para normalizar
        key_norm = key.lower()
        for p in ["202401", "202402", "202501", "202502"]:
            key_norm = key_norm.replace(p.lower(), "PPERIODO")
        base_norm = base_lower
        for p in ["202401", "202402", "202501", "202502"]:
            base_norm = base_norm.replace(p.lower(), "PPERIODO")
        if key_norm == base_norm:
            return cod
    return None


def load_periodo_360(carpeta: str, periodo_codigo: str, db: Session) -> dict:
    """
    Carga todos los archivos xlsx de una carpeta de período 360.
    Hace upsert de docentes (si no existen), inserta respuestas_raw,
    y calcula puntajes_instrumento y puntajes_finales.
    """
    print(f"[360] Procesando período {periodo_codigo} desde {carpeta}")

    archivos = [f for f in os.listdir(carpeta) if f.endswith(".xlsx")]
    total_respuestas = 0
    archivos_procesados = 0

    for archivo in sorted(archivos):
        ruta = os.path.join(carpeta, archivo)
        cod_instrumento = _detectar_instrumento(archivo)

        if not cod_instrumento:
            print(f"  [360] WARN  No se reconoce instrumento para: {archivo}")
            continue

        try:
            df = pd.read_excel(ruta, dtype=str)
        except Exception as e:
            print(f"  [360] ERROR Error leyendo {archivo}: {e}")
            continue

        df.columns = [str(c).strip() for c in df.columns]

        # Eliminar respuestas previas de este archivo para este período (re-proceso limpio)
        db.query(RespuestaRaw).filter(
            RespuestaRaw.periodo_codigo  == periodo_codigo,
            RespuestaRaw.cod_instrumento == cod_instrumento,
            RespuestaRaw.archivo_fuente  == archivo,
        ).delete(synchronize_session=False)

        respuestas_lote = []

        for _, row in df.iterrows():
            cedula = str(row.get("usuario_evaluado", "") or "").strip()
            if not cedula or cedula in ("nan", ""):
                continue

            # Asegurar que el docente existe (mínimo)
            if not db.query(Docente).filter_by(cedula=cedula).first():
                ap = str(row.get("apellidos_evaluado", "") or "").strip()
                nom = str(row.get("nombres_evaluado", "") or "").strip()
                db.add(Docente(
                    cedula          = cedula,
                    apellidos       = ap,
                    nombres         = nom,
                    nombre_completo = f"{ap} {nom}".strip(),
                ))
                try:
                    db.flush()
                except Exception:
                    db.rollback()
                    continue

            calificacion = _safe_float(row.get("calificacion"))
            peso         = _safe_float(row.get("peso"))

            respuestas_lote.append(RespuestaRaw(
                nrc             = str(row.get("nrc", "") or "").strip(),
                periodo_codigo  = periodo_codigo,
                cedula_evaluado = cedula,
                cod_instrumento = cod_instrumento,
                evaluador_hash  = _hash_evaluador(row.get("evaluador")),
                programa        = str(row.get("programa", "") or "").strip()[:200],
                num_pregunta    = int(float(row["num_pregunta"])) if str(row.get("num_pregunta","")).replace(".","").isdigit() else None,
                pregunta        = str(row.get("pregunta", "") or "")[:2000],
                competencia     = str(row.get("competencia", "") or "").strip()[:200] or None,
                calificacion    = calificacion,
                peso            = peso,
                fecha_registro  = _safe_date(row.get("fecha_registro")),
                archivo_fuente  = archivo,
            ))

        if respuestas_lote:
            db.add_all(respuestas_lote)
            db.flush()
            total_respuestas += len(respuestas_lote)
            archivos_procesados += 1
            print(f"  [360] OK {archivo} ({cod_instrumento}): {len(respuestas_lote)} respuestas")

    db.commit()

    # ── Calcular puntajes por instrumento ────────────────────────────────────
    _calcular_puntajes_instrumento(periodo_codigo, db)
    _calcular_puntajes_finales(periodo_codigo, db)

    return {
        "periodo": periodo_codigo,
        "archivos": archivos_procesados,
        "respuestas": total_respuestas,
    }


def _calcular_puntajes_instrumento(periodo_codigo: str, db: Session):
    """
    Agrega respuestas_raw → puntajes_instrumento para un período.
    Fórmula: suma(calificacion * peso) / suma(peso_max_por_pregunta) * 100
    """
    print(f"  [Calc] Calculando puntajes por instrumento para {periodo_codigo}...")

    # Obtener combinaciones únicas docente × instrumento
    combos = db.execute(text("""
        SELECT DISTINCT cedula_evaluado, cod_instrumento
        FROM respuestas_raw
        WHERE periodo_codigo = :p
        """),
        {"p": periodo_codigo}
    ).fetchall()

    for cedula, cod_inst in combos:
        filas = db.execute(text("""
            SELECT calificacion, peso, evaluador_hash
            FROM respuestas_raw
            WHERE periodo_codigo = :p
              AND cedula_evaluado = :c
              AND cod_instrumento = :i
              AND calificacion IS NOT NULL
              AND peso IS NOT NULL
            """),
            {"p": periodo_codigo, "c": cedula, "i": cod_inst}
        ).fetchall()

        if not filas:
            continue

        df = pd.DataFrame(filas, columns=["calificacion", "peso", "evaluador_hash"])

        # Calcular puntaje ponderado: por cada pregunta, calificación × peso
        # Normalización: la suma de pesos por instrumento debería sumar 100
        suma_pond = (df["calificacion"] * df["peso"]).sum()
        suma_pesos = df["peso"].sum()
        puntaje_bruto = suma_pond / suma_pesos if suma_pesos > 0 else 0

        # Normalizar a 0-100 (escala Likert 1-4 o 1-5 según instrumento)
        # La calificación máxima suele ser 4 (escala 1-4)
        cal_max = df["calificacion"].max()
        if cal_max <= 4:
            puntaje_100 = round((puntaje_bruto / 4) * 100, 2)
        elif cal_max <= 5:
            puntaje_100 = round((puntaje_bruto / 5) * 100, 2)
        else:
            puntaje_100 = round(puntaje_bruto, 2)

        puntaje_100 = min(puntaje_100, 100.0)

        n_evaluadores = df["evaluador_hash"].nunique()
        n_preguntas   = len(df) // max(n_evaluadores, 1)

        # Upsert
        existing = db.query(PuntajeInstrumento).filter_by(
            cedula=cedula, periodo_codigo=periodo_codigo, cod_instrumento=cod_inst
        ).first()

        if existing:
            existing.puntaje_bruto     = round(puntaje_bruto, 4)
            existing.puntaje_sobre_100 = puntaje_100
            existing.n_preguntas       = n_preguntas
            existing.n_evaluadores     = n_evaluadores
        else:
            db.add(PuntajeInstrumento(
                cedula          = cedula,
                periodo_codigo  = periodo_codigo,
                cod_instrumento = cod_inst,
                puntaje_bruto   = round(puntaje_bruto, 4),
                puntaje_sobre_100 = puntaje_100,
                n_preguntas     = n_preguntas,
                n_evaluadores   = n_evaluadores,
            ))

    db.commit()
    print(f"  [Calc] OK Puntajes por instrumento calculados para {periodo_codigo}")


# Mapeo tipo_evaluador → nombre componente en PuntajeFinal
_TIPO_A_COMP = {
    "auto":        "comp_auto",
    "pares":       "comp_pares",
    "hetero_est":  "comp_het_est",
    "hetero_dir":  "comp_het_dir",
    "coordinador": "comp_het_dir",
}

# Mapeo cod_instrumento → tipo para este cálculo
from app.etl.registry import INSTRUMENTOS as _INST_LIST
_COD_A_TIPO = {i["cod"]: i["tipo_evaluador"] for i in _INST_LIST}
_COD_A_MODELO = {i["cod"]: i["modelo"] for i in _INST_LIST}
_COD_A_PESO = {i["cod"]: int(i["peso_en_modelo"]) for i in _INST_LIST}


def _calcular_puntajes_finales(periodo_codigo: str, db: Session):
    """
    Combina puntajes_instrumento → puntajes_finales para un período.
    Agrupa por docente × modelo y aplica PESOS_MODELO.
    """
    print(f"  [Calc] Calculando puntajes finales para {periodo_codigo}...")

    puntajes = db.execute(text("""
        SELECT cedula, cod_instrumento, puntaje_sobre_100
        FROM puntajes_instrumento
        WHERE periodo_codigo = :p
        """),
        {"p": periodo_codigo}
    ).fetchall()

    # Agrupar por docente → modelo
    from collections import defaultdict
    por_docente_modelo = defaultdict(dict)  # {(cedula, modelo): {tipo: puntaje_100}}

    for cedula, cod_inst, puntaje in puntajes:
        modelo = _COD_A_MODELO.get(cod_inst)
        tipo   = _COD_A_TIPO.get(cod_inst)
        if not modelo or not tipo or puntaje is None:
            continue
        key = (cedula, modelo)
        # Si hay múltiples instrumentos del mismo tipo (ej. investigación tiene dos het_dir),
        # promediamos ponderando por peso_en_modelo
        peso = _COD_A_PESO.get(cod_inst, 1)
        if tipo not in por_docente_modelo[key]:
            por_docente_modelo[key][tipo] = {"puntajes": [], "pesos": []}
        por_docente_modelo[key][tipo]["puntajes"].append(puntaje)
        por_docente_modelo[key][tipo]["pesos"].append(peso)

    for (cedula, modelo), componentes in por_docente_modelo.items():
        pesos_modelo = PESOS_MODELO.get(modelo, {})
        if not pesos_modelo:
            continue

        puntaje_total = 0.0
        suma_pesos_disponibles = 0
        comp_json = {}
        comp_values = {
            "comp_het_est": None,
            "comp_auto":    None,
            "comp_pares":   None,
            "comp_het_dir": None,
            "comp_cev":     None,
        }

        for tipo, peso_max in pesos_modelo.items():
            if tipo not in componentes:
                continue
            data = componentes[tipo]
            # Promedio ponderado si hay varios instrumentos del mismo tipo
            total_peso = sum(data["pesos"])
            puntaje_tipo = sum(p * w for p, w in zip(data["puntajes"], data["pesos"])) / total_peso if total_peso > 0 else 0
            # Contribución al puntaje final: puntaje_tipo (0-100) × peso_max / 100
            contribucion = (puntaje_tipo / 100) * peso_max
            puntaje_total += contribucion
            suma_pesos_disponibles += peso_max

            comp_json[tipo] = round(puntaje_tipo, 2)

            # Mapear al campo de columna
            col = _TIPO_A_COMP.get(tipo)
            if col:
                comp_values[col] = round(puntaje_tipo, 2)

        if suma_pesos_disponibles == 0:
            continue

        # Escalar al 100% si no están todos los componentes
        puntaje_100 = round((puntaje_total / suma_pesos_disponibles) * 100, 2)
        puntaje_100 = min(puntaje_100, 100.0)

        existing = db.query(PuntajeFinal).filter_by(
            cedula=cedula, periodo_codigo=periodo_codigo, modelo=modelo
        ).first()

        data = dict(
            cedula          = cedula,
            periodo_codigo  = periodo_codigo,
            modelo          = modelo,
            sistema         = "360",
            puntaje_100     = puntaje_100,
            nivel_desempeno = nivel_from_puntaje(puntaje_100),
            componentes_json = comp_json,
            **comp_values,
        )

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
        else:
            db.add(PuntajeFinal(**data))

    db.commit()
    print(f"  [Calc] OK Puntajes finales calculados para {periodo_codigo}")
