from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.kpi_service import kpi_service
from app.services.gemini_service import gemini_service
from app.services.etl_service import etl_service


class ConsultaRequest(BaseModel):
    pregunta: str
    anio: Optional[int] = None

router = APIRouter()


@router.post("/etl/process")
def process_evaluaciones(db: Session = Depends(get_db)):
    try:
        count = etl_service.process_all_files(db)
        return {"message": f"Procesamiento completado. {count} registros nuevos."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kpis/institucionales")
def get_kpis(
    db: Session = Depends(get_db),
    modelo: Optional[str] = None,
    anio: Optional[int] = None,
    sistema: Optional[str] = None,
):
    kpis = kpi_service.get_institutional_kpis(db, modelo=modelo, anio=anio, sistema=sistema)
    if not kpis:
        raise HTTPException(status_code=404, detail="No hay datos disponibles")
    return kpis


@router.get("/ranking")
def get_ranking(
    db: Session = Depends(get_db),
    limit: int = 1000,
    modelo: Optional[str] = None,
    anio: Optional[int] = None,
    sistema: Optional[str] = None,
):
    return kpi_service.get_ranking_docentes(db, modelo=modelo, anio=anio, limit=limit, sistema=sistema)


@router.get("/criticos")
def get_criticos(
    db: Session = Depends(get_db),
    threshold: float = 3.5,
    modelo: Optional[str] = None,
    anio: Optional[int] = None,
    sistema: Optional[str] = None,
):
    return kpi_service.get_docentes_criticos(db, modelo=modelo, anio=anio, threshold=threshold, sistema=sistema)


@router.get("/tendencias")
def get_tendencias(
    db: Session = Depends(get_db),
    modelo: Optional[str] = None,
    sistema: Optional[str] = None,
):
    return kpi_service.get_tendencias(db, modelo=modelo, sistema=sistema)


@router.get("/variables")
def get_variables(
    db: Session = Depends(get_db),
    modelo: Optional[str] = None,
    anio: Optional[int] = None,
    sistema: Optional[str] = None,
):
    return kpi_service.get_variables_kpis(db, modelo=modelo, anio=anio, sistema=sistema)


@router.get("/demograficos")
def get_demograficos(
    db: Session = Depends(get_db),
    modelo: Optional[str] = None,
    anio: Optional[int] = None,
    sistema: Optional[str] = None,
):
    return kpi_service.get_demograficos(db, modelo=modelo, anio=anio, sistema=sistema)


@router.get("/analisis-ia")
def get_ai_analysis(
    db: Session = Depends(get_db),
    modelo: Optional[str] = None,
    anio: Optional[int] = None,
    sistema: Optional[str] = None,
):
    kpis = kpi_service.get_institutional_kpis(db, modelo=modelo, anio=anio, sistema=sistema)
    if not kpis:
        raise HTTPException(status_code=404, detail="No hay datos para analizar")
    variables = kpi_service.get_variables_kpis(db, modelo=modelo, anio=anio, sistema=sistema)
    kpis['variables'] = {k: v['promedio'] for k, v in variables.get('componentes', {}).items()}
    analysis = gemini_service.generate_executive_analysis(kpis)
    return {"analysis": analysis}


@router.get("/analytics")
def get_analytics(
    db: Session = Depends(get_db),
    sistema: Optional[str] = None,
    modelo: Optional[str] = None,
    anio: Optional[int] = None,
):
    """Return gender/age/seniority/function breakdown for any filter combination."""
    return kpi_service.get_analytics(db, sistema=sistema, modelo=modelo, anio=anio)


@router.get("/comparativo")
def get_comparativo(
    db: Session = Depends(get_db),
    anio: Optional[int] = None,
):
    """Side-by-side MEIPA vs 360 metrics + per-model breakdown + yearly trends."""
    return kpi_service.get_comparativo(db, anio=anio)


@router.get("/todos-docentes")
def get_todos_docentes(
    db: Session = Depends(get_db),
    anio: Optional[int] = None,
    modelo: Optional[str] = None,
    sistema: Optional[str] = None,
):
    """All teachers with per-component breakdown, optionally filtered by modelo and sistema."""
    return kpi_service.get_todos_docentes(db, anio=anio, modelo=modelo, sistema=sistema)


@router.get("/competencias/{cedula}")
def get_competencias_docente(cedula: str, db: Session = Depends(get_db)):
    """Per-competency breakdown for a teacher from RespuestaRaw (360°) and PuntajeFinal (MEIPA)."""
    return kpi_service.get_competencias_docente(db, cedula=cedula)


@router.post("/consulta-ia")
def consulta_ia(body: ConsultaRequest, db: Session = Depends(get_db)):
    """Answer a free-form question about teacher evaluation using real data + Gemini."""
    comparativo = kpi_service.get_comparativo(db, anio=body.anio)
    ranking_top = kpi_service.get_ranking_docentes(db, limit=50)
    criticos    = kpi_service.get_docentes_criticos(db, threshold=3.5)

    context = {
        'comparativo': comparativo,
        'ranking_top': ranking_top,
        'criticos':    criticos,
    }

    answer = gemini_service.answer_question(body.pregunta, context)
    return {'respuesta': answer, 'pregunta': body.pregunta}
