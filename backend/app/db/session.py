import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

if settings.DATABASE_URL:
    engine = create_engine(settings.DATABASE_URL)
else:
    # Usar evaluacion.db — el archivo que se incluye en el repo con todos los datos
    _db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "evaluacion.db")
    _db_path = os.path.normpath(_db_path)
    engine = create_engine(f"sqlite:///{_db_path}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
