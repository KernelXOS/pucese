from sqlalchemy import Column, String, JSON
from app.models.base import Base


class Instrumento(Base):
    __tablename__ = "instrumentos"

    # '01' | '02' | '03' | '05' | '08' | '10' | '11' | '12' | '13' | '14' | '15' | '16' | '17' | '018'
    cod             = Column(String(10), primary_key=True)
    descripcion     = Column(String(200))
    # 'docencia' | 'abp' | 'posgrado' | 'tecnologado' | 'investigacion' | 'vinculacion' | 'gestion'
    modelo          = Column(String(30))
    # 'auto' | 'pares' | 'hetero_est' | 'hetero_dir' | 'coordinador'
    tipo_evaluador  = Column(String(30))
    # peso de este instrumento dentro del puntaje final del modelo (0-100)
    peso_en_modelo  = Column(String(10))
    # pesos por componente como JSON: {"het_est": 50, "pares": 20, ...}
    pesos_componentes = Column(JSON)
