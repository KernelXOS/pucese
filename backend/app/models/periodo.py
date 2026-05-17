from sqlalchemy import Column, String, Date, Boolean
from app.models.base import Base


class Periodo(Base):
    __tablename__ = "periodos"

    # '202301' | '202302' | '202401' | '202402' | '202501' | '202502'
    codigo      = Column(String(6), primary_key=True)
    nombre      = Column(String(100))      # 'MEIPA 2023 - I Período'
    sistema     = Column(String(10))       # 'meipa' | '360'
    anio        = Column(String(4))        # '2023'
    numero      = Column(String(2))        # '01' | '02'
    label_corto = Column(String(30))       # '2023-I' | '2024-II'
    fecha_inicio= Column(Date)
    fecha_fin   = Column(Date)
    activo      = Column(Boolean, default=True)
