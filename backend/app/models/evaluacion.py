from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Evaluacion(Base):
    __tablename__ = "evaluaciones"

    id = Column(Integer, primary_key=True, index=True)
    docente_nombre = Column(String, index=True)
    facultad = Column(String, index=True)
    periodo = Column(String, index=True)
    sexo = Column(String)  # Masculino / Femenino
    edad = Column(Integer)
    metodologia = Column(Float)
    puntualidad = Column(Float)
    dominio_tematico = Column(Float)
    interaccion = Column(Float)
    uso_tic = Column(Float)
    satisfaccion = Column(Float)
    promedio = Column(Float)
    observaciones = Column(Text)
    fecha_proceso = Column(DateTime, default=datetime.utcnow)
    archivo_fuente = Column(String)

    # Componentes reales de evaluación (sobre 100)
    het_estudiantil = Column(Float)   # Heteroevaluación estudiantil (max 50)
    eval_pares      = Column(Float)   # Evaluación de pares (max 20)
    aula_virtual    = Column(Float)   # Aula virtual / TIC (max 20)
    autoevaluacion  = Column(Float)   # Autoevaluación docente (max 10)
    puntaje_100     = Column(Float)   # Resultado final sobre 100

    # Variables demográficas adicionales
    carrera         = Column(String)
    tiempo_servicio = Column(String)
    nivel_estudio   = Column(String)
    grado           = Column(String)
    modalidad       = Column(String)
    nivel_desempeno = Column(String)
    cedula          = Column(String)

    # Clasificación por modelo de evaluación y año
    modelo          = Column(String, index=True, default='docencia')
    anio            = Column(Integer, index=True)

    # Componentes adicionales para otros modelos (escala 0-100 normalizados)
    comp_auto       = Column(Float)   # Autoevaluación (cualquier modelo)
    comp_pares      = Column(Float)   # Evaluación de pares / Coevaluación
    comp_hetero_dir = Column(Float)   # Hetero directivo / superior / investigación
    comp_hetero_est = Column(Float)   # Hetero estudiantes (para vinculación/ABP/gestión)

    # ── Sistema de evaluación ────────────────────────────────────────────────────
    sistema         = Column(String, index=True)   # 'meipa' o '360'
    antiguedad_anos = Column(Float)                # Antigüedad en años (float)
    funcion_docente = Column(String)               # 'DOCENCIA', 'COORDINACIÓN', 'OPERATIVO', etc.

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
