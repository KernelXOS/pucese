"""
Endpoints de docentes: listado, perfil completo histórico, descarga de PDF.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.docente import Docente, PersonalPeriodo
from app.models.puntaje import PuntajeFinal
from app.etl.registry import PERIODOS
from app.services.pdf_service import generar_pdf_docente, generar_pdf_directorio, generar_pdf_bulk_docentes

router = APIRouter()

MODELO_LABELS = {
    "docencia":      "Docencia",
    "abp":           "Salud / ABP",
    "posgrado":      "Posgrado",
    "tecnologado":   "Tecnologado",
    "investigacion": "Investigación",
    "vinculacion":   "Vinculación",
    "gestion":       "Gestión",
}


@router.get("/")
def listar_docentes(
    periodo: Optional[str]  = Query(None, description="Código de período ej. 202502"),
    facultad: Optional[str] = Query(None),
    modelo:   Optional[str] = Query(None),
    q:        Optional[str] = Query(None, description="Búsqueda por nombre o cédula"),
    limit:    int           = Query(200, le=1000),
    db: Session = Depends(get_db),
):
    """Lista docentes con su puntaje en el período indicado."""
    query = db.query(
        Docente.cedula,
        Docente.nombre_completo,
        Docente.genero,
        PersonalPeriodo.facultad,
        PersonalPeriodo.funcion,
        PersonalPeriodo.dedicacion,
        PuntajeFinal.puntaje_100,
        PuntajeFinal.nivel_desempeno,
        PuntajeFinal.modelo,
        PuntajeFinal.sistema,
        PuntajeFinal.periodo_codigo,
    ).join(
        PuntajeFinal, PuntajeFinal.cedula == Docente.cedula
    ).outerjoin(
        PersonalPeriodo,
        (PersonalPeriodo.cedula == Docente.cedula) &
        (PersonalPeriodo.periodo_codigo == PuntajeFinal.periodo_codigo)
    )

    if periodo:
        query = query.filter(PuntajeFinal.periodo_codigo == periodo)
    if facultad:
        query = query.filter(PersonalPeriodo.facultad == facultad)
    if modelo:
        query = query.filter(PuntajeFinal.modelo == modelo)
    if q:
        like = f"%{q.upper()}%"
        query = query.filter(
            (Docente.nombre_completo.ilike(f"%{q}%")) |
            (Docente.cedula.ilike(f"%{q}%"))
        )

    query = query.order_by(PuntajeFinal.puntaje_100.desc()).limit(limit)
    rows = query.all()

    return [
        {
            "cedula":         r.cedula,
            "nombre":         r.nombre_completo,
            "genero":         r.genero,
            "facultad":       r.facultad,
            "funcion":        r.funcion,
            "dedicacion":     r.dedicacion,
            "puntaje_100":    round(r.puntaje_100, 1) if r.puntaje_100 else None,
            "nivel":          r.nivel_desempeno,
            "modelo":         r.modelo,
            "modelo_label":   MODELO_LABELS.get(r.modelo, r.modelo),
            "sistema":        r.sistema,
            "periodo":        r.periodo_codigo,
        }
        for r in rows
    ]


@router.get("/{cedula}/perfil")
def perfil_docente(cedula: str, db: Session = Depends(get_db)):
    """Perfil completo del docente con historial en todos los períodos."""
    docente = db.query(Docente).filter_by(cedula=cedula).first()
    if not docente:
        raise HTTPException(404, f"Docente {cedula} no encontrado")

    # Snapshots por período
    snapshots = db.query(PersonalPeriodo).filter_by(cedula=cedula).all()
    snapshots_dict = {s.periodo_codigo: s for s in snapshots}

    # Puntajes por período
    puntajes = db.query(PuntajeFinal).filter_by(cedula=cedula).all()

    historico = []
    for p in PERIODOS:
        cod = p["codigo"]
        snap = snapshots_dict.get(cod)
        pfs = [pf for pf in puntajes if pf.periodo_codigo == cod]

        if not pfs and not snap:
            continue

        historico.append({
            "periodo_codigo": cod,
            "periodo_label":  p["label_corto"],
            "sistema":        p["sistema"],
            "facultad":       snap.facultad if snap else None,
            "funcion":        snap.funcion if snap else None,
            "dedicacion":     snap.dedicacion if snap else None,
            "antiguedad_anos": snap.antiguedad_anos if snap else None,
            "puntajes": [
                {
                    "modelo":        pf.modelo,
                    "modelo_label":  MODELO_LABELS.get(pf.modelo, pf.modelo),
                    "sistema":       pf.sistema,
                    "puntaje_100":   round(pf.puntaje_100, 1) if pf.puntaje_100 else None,
                    "nivel":         pf.nivel_desempeno,
                    "comp_het_est":  round(pf.comp_het_est, 1) if pf.comp_het_est else None,
                    "comp_auto":     round(pf.comp_auto, 1) if pf.comp_auto else None,
                    "comp_pares":    round(pf.comp_pares, 1) if pf.comp_pares else None,
                    "comp_het_dir":  round(pf.comp_het_dir, 1) if pf.comp_het_dir else None,
                    "comp_cev":      round(pf.comp_cev, 1) if pf.comp_cev else None,
                }
                for pf in pfs
            ],
        })

    return {
        "cedula":             docente.cedula,
        "nombre_completo":    docente.nombre_completo,
        "apellidos":          docente.apellidos,
        "nombres":            docente.nombres,
        "genero":             docente.genero,
        "email_institucional":docente.email_institucional,
        "historico":          historico,
    }


@router.get("/{cedula}/reporte.pdf")
def descargar_reporte_pdf(
    cedula: str,
    periodo: Optional[str] = Query(None, description="Período específico, ej. 202502. Por defecto: último disponible."),
    db: Session = Depends(get_db),
):
    """
    Genera y descarga el reporte PDF individual del docente.
    Contiene: datos personales, puntaje del período, desglose de componentes,
    posición en ranking, y evolución histórica por períodos.
    """
    try:
        pdf_bytes = generar_pdf_docente(cedula=cedula, db=db, periodo_codigo=periodo)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))

    # Nombre de archivo legible
    docente = db.query(Docente).filter_by(cedula=cedula).first()
    nombre_safe = (docente.apellidos or cedula).replace(" ", "_").upper()[:30] if docente else cedula
    periodo_safe = periodo or "ultimo"
    filename = f"Reporte_{nombre_safe}_{periodo_safe}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class DocenteItem(BaseModel):
    nombre:   str = ""
    cedula:   str = ""
    facultad: str = ""
    sistema:  str = ""
    modelo:   str = ""
    puntaje:  float = 0.0
    nivel:    str = ""

class DirectorioReportePayload(BaseModel):
    titulo:   str = "Todos los Docentes"
    docentes: List[DocenteItem] = []


@router.post("/reporte-directorio.pdf")
def descargar_reporte_directorio(
    payload: DirectorioReportePayload,
):
    """
    Genera un PDF de reporte del directorio de docentes con el mismo diseño
    profesional que el reporte individual (WeasyPrint/HTML).
    El frontend envía la lista de docentes ya filtrada.
    """
    try:
        docentes_raw = [d.dict() for d in payload.docentes]
        pdf_bytes = generar_pdf_directorio(
            titulo=payload.titulo,
            docentes_data=docentes_raw,
        )
    except RuntimeError as e:
        raise HTTPException(500, str(e))

    from datetime import datetime as _dt
    fecha_safe = _dt.now().strftime("%Y-%m-%d")
    filename = f"Reporte_Directorio_{fecha_safe}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class BulkReportePayload(BaseModel):
    cedulas: List[str] = []


@router.post("/reporte-bulk.pdf")
def descargar_reporte_bulk(
    payload: BulkReportePayload,
    db: Session = Depends(get_db),
):
    """
    Genera un PDF con una página completa por docente (igual que el reporte individual)
    para todos los docentes de la lista enviada.
    """
    if not payload.cedulas:
        raise HTTPException(400, "Se requiere al menos una cédula")
    if len(payload.cedulas) > 500:
        raise HTTPException(400, "Máximo 500 docentes por reporte")

    try:
        pdf_bytes = generar_pdf_bulk_docentes(cedulas=payload.cedulas, db=db)
    except ValueError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))

    from datetime import datetime as _dt
    fecha_safe = _dt.now().strftime("%Y-%m-%d")
    filename = f"Reportes_Docentes_{fecha_safe}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
