from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

if settings.DATABASE_URL:
    engine = create_engine(settings.DATABASE_URL)
else:
    # Placeholder for local development if no URL is provided
    engine = create_engine("sqlite:///./test.db")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
