from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EvaluacionBase(BaseModel):
    docente_nombre: str
    facultad: str
    periodo: Optional[str] = None
    sexo: Optional[str] = None
    edad: Optional[int] = None
    metodologia: float
    puntualidad: float
    dominio_tematico: float
    interaccion: float
    uso_tic: float
    satisfaccion: float
    promedio: float
    observaciones: Optional[str] = None
    archivo_fuente: Optional[str] = None

class EvaluacionCreate(EvaluacionBase):
    pass

class Evaluacion(EvaluacionBase):
    id: int
    fecha_proceso: datetime

    class Config:
        from_attributes = True

class KPIInstitucionales(BaseModel):
    promedio_general: float
    mejor_docente: str
    peor_docente: str
    total_evaluaciones: int
    promedio_por_facultad: dict[str, float]

class TendenciaAcademica(BaseModel):
    periodo: str
    promedio: float
