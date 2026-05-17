from sqlalchemy import Column, String, Float, Integer, BigInteger, DateTime, ForeignKey, Text
from app.models.base import Base


class RespuestaRaw(Base):
    """Respuesta individual a nivel de pregunta — dato más granular del sistema."""
    __tablename__ = "respuestas_raw"

    id              = Column(Integer, primary_key=True, autoincrement=True)

    # Contexto de evaluación
    nrc             = Column(String(20))        # código de sección/asignatura
    periodo_codigo  = Column(String(6),  ForeignKey("periodos.codigo"), index=True)
    cedula_evaluado = Column(String(15), ForeignKey("docentes.cedula"), index=True)
    cod_instrumento = Column(String(10), ForeignKey("instrumentos.cod"), index=True)

    # Evaluador (hasheado para anonimato)
    evaluador_hash  = Column(String(100))

    # Contexto académico
    programa        = Column(String(200))

    # Pregunta y respuesta
    num_pregunta    = Column(Integer)
    pregunta        = Column(Text)
    competencia     = Column(String(200))   # disponible desde 202501
    calificacion    = Column(Float)
    peso            = Column(Float)         # peso de esta pregunta en el instrumento
    fecha_registro  = Column(DateTime)

    # Trazabilidad
    archivo_fuente  = Column(String(200))
