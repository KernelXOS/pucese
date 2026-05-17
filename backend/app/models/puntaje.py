from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.sql import func
from app.models.base import Base


class PuntajeInstrumento(Base):
    """Puntaje agregado por docente + período + instrumento."""
    __tablename__ = "puntajes_instrumento"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    cedula          = Column(String(15), ForeignKey("docentes.cedula"), index=True)
    periodo_codigo  = Column(String(6),  ForeignKey("periodos.codigo"), index=True)
    cod_instrumento = Column(String(10), ForeignKey("instrumentos.cod"), index=True)

    puntaje_bruto       = Column(Float)  # promedio ponderado de respuestas (escala original)
    puntaje_sobre_100   = Column(Float)  # normalizado a 0-100
    n_preguntas         = Column(Integer)
    n_evaluadores       = Column(Integer)
    fecha_proceso       = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("cedula", "periodo_codigo", "cod_instrumento",
                         name="uq_puntaje_instrumento"),
    )


class PuntajeFinal(Base):
    """Puntaje final compuesto por docente + período + modelo de evaluación."""
    __tablename__ = "puntajes_finales"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    cedula          = Column(String(15), ForeignKey("docentes.cedula"), index=True)
    periodo_codigo  = Column(String(6),  ForeignKey("periodos.codigo"), index=True)

    # 'docencia' | 'abp' | 'posgrado' | 'tecnologado' | 'investigacion' | 'vinculacion' | 'gestion'
    modelo          = Column(String(30), index=True)
    # 'meipa' | '360'
    sistema         = Column(String(10), index=True)

    # Componentes desglosados (cada uno sobre su peso máximo)
    comp_het_est    = Column(Float)   # heteroevaluación estudiantes
    comp_auto       = Column(Float)   # autoevaluación
    comp_pares      = Column(Float)   # evaluación de pares
    comp_het_dir    = Column(Float)   # heteroevaluación directivo / superior
    comp_cev        = Column(Float)   # entorno virtual / aula virtual

    # Resultado final
    puntaje_100     = Column(Float, index=True)
    nivel_desempeno = Column(String(20))    # Excelente | Bueno | Regular | Deficiente

    # Todos los componentes como JSON flexible (para modelos con estructura distinta)
    componentes_json = Column(JSON)

    fecha_proceso   = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("cedula", "periodo_codigo", "modelo",
                         name="uq_puntaje_final"),
    )
