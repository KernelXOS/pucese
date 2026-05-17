from sqlalchemy import Column, String, Date, Float, Integer, ForeignKey, UniqueConstraint
from app.models.base import Base


class Docente(Base):
    """Perfil estático del docente — datos que no cambian entre períodos."""
    __tablename__ = "docentes"

    cedula                = Column(String(15), primary_key=True)
    apellidos             = Column(String(100))
    nombres               = Column(String(100))
    nombre_completo       = Column(String(200), index=True)
    email_institucional   = Column(String(150))
    email_personal        = Column(String(150))
    genero                = Column(String(20))
    fecha_nacimiento      = Column(Date)
    etnia                 = Column(String(50))
    nacionalidad          = Column(String(50))


class PersonalPeriodo(Base):
    """Snapshot del docente en cada período — datos que sí cambian (cargo, carrera, antigüedad)."""
    __tablename__ = "personal_periodo"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    cedula              = Column(String(15), ForeignKey("docentes.cedula"), index=True)
    periodo_codigo      = Column(String(6),  ForeignKey("periodos.codigo"), index=True)

    # Ubicación institucional
    unidad_organizativa = Column(String(150))   # valor raw del Excel
    facultad            = Column(String(100))   # mapeada (Ciencias Administrativas, Medicina...)
    carrera             = Column(String(150))

    # Función y contrato
    funcion             = Column(String(80))    # DOCENCIA | COORDINACIÓN | OPERATIVO...
    dedicacion          = Column(String(20))    # TC | MT | TP
    tipo_contrato       = Column(String(80))    # Titular | Ocasional | Por obra cierta...
    posicion            = Column(String(200))   # Docente Titular Auxiliar Nivel 2 Grado 2...

    # Métricas de antigüedad y edad
    fecha_ingreso       = Column(Date, nullable=True)   # Fecha del último Ingreso a la PUCE
    antiguedad_anos     = Column(Float)
    edad_en_periodo     = Column(Integer)

    # Formación académica
    nivel_instruccion   = Column(String(50))    # Tercer Nivel | Cuarto Nivel
    grado_instruccion   = Column(String(80))    # Grado | Maestría | PhD...
    titulo              = Column(String(200))
    senescyt            = Column(String(50))
    institucion_titulo  = Column(String(200))

    __table_args__ = (
        UniqueConstraint("cedula", "periodo_codigo", name="uq_personal_periodo"),
    )
