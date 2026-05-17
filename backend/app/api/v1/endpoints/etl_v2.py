"""
Endpoints ETL v2: procesamiento por período, estado del sistema, catálogos.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.etl.pipeline import run_full_etl, run_periodo, get_estado, seed_catalogs
from app.models.periodo import Periodo
from app.etl.registry import PERIODOS

router = APIRouter()


# Mapa período → (sistema, anio) para resolver datos del legacy
_PERIODO_LEGACY = {
    "202301": ("meipa", 2023),
    "202302": ("meipa", 2023),
    "202401": ("meipa", 2024),
    "202402": ("360",   2024),
    "202501": ("360",   2025),
    "202502": ("360",   2025),
}


@router.get("/periodos")
def listar_periodos(db: Session = Depends(get_db)):
    """Lista todos los períodos del sistema con su estado de carga."""
    # ── Conteos en tablas nuevas (ETL v2) ────────────────────────────────────
    puntajes_nuevos: dict = {}
    try:
        estado = get_estado(db)
        for p in estado.get("periodos", []):
            puntajes_nuevos[p["codigo"]] = p.get("puntajes", 0)
    except Exception:
        db.rollback()

    # ── Conteos en tabla legacy evaluaciones ─────────────────────────────────
    legacy_por_sis_anio: dict = {}
    try:
        from app.models.evaluacion import Evaluacion
        from sqlalchemy import func
        rows = (
            db.query(Evaluacion.sistema, Evaluacion.anio, func.count(Evaluacion.id))
            .group_by(Evaluacion.sistema, Evaluacion.anio)
            .all()
        )
        for sistema, anio, cnt in rows:
            legacy_por_sis_anio[(sistema, anio)] = cnt
    except Exception:
        db.rollback()

    result = []
    for p in PERIODOS:
        cod = p["codigo"]
        n_nuevo  = puntajes_nuevos.get(cod, 0)
        sis_anio = _PERIODO_LEGACY.get(cod, (p["sistema"], int(p["anio"])))
        n_legacy = legacy_por_sis_anio.get(sis_anio, 0)
        result.append({
            "codigo":   cod,
            "label":    p["label_corto"],
            "nombre":   p["nombre"],
            "sistema":  p["sistema"],
            "anio":     p["anio"],
            "puntajes": n_nuevo,
            "puntajes_legacy": n_legacy,
            "cargado":  n_nuevo > 0 or n_legacy > 0,
        })
    return result


@router.get("/estado")
def estado_sistema(db: Session = Depends(get_db)):
    """Diagnóstico completo del estado de carga de datos."""
    return get_estado(db)


@router.post("/procesar-todo")
def procesar_todo(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Lanza el ETL completo en background para todos los períodos.
    Incremental: no borra datos existentes.
    """
    background_tasks.add_task(_run_etl_background, db)
    return {"mensaje": "ETL iniciado en background. Consulta /estado para ver el progreso."}


@router.post("/procesar-periodo/{periodo_codigo}")
def procesar_periodo(
    periodo_codigo: str,
    db: Session = Depends(get_db),
):
    """
    Procesa (o re-procesa) un único período específico.
    No afecta los demás períodos.
    """
    validos = [p["codigo"] for p in PERIODOS]
    if periodo_codigo not in validos:
        raise HTTPException(400, f"Período inválido. Válidos: {validos}")

    try:
        resultado = run_periodo(periodo_codigo, db)
        return {"periodo": periodo_codigo, "resultado": resultado}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/seed-catalogos")
def seed_cat(db: Session = Depends(get_db)):
    """Inserta/actualiza catálogos de períodos e instrumentos."""
    seed_catalogs(db)
    return {"mensaje": "Catálogos actualizados"}


def _run_etl_background(db: Session):
    try:
        run_full_etl(db)
    except Exception as e:
        print(f"[ETL Background] Error: {e}")
        import traceback
        traceback.print_exc()
