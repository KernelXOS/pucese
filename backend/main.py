import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router
from app.db.session import engine, SessionLocal
from app.core.config import settings

# Importar todos los modelos para que SQLAlchemy los registre en la metadata
from app.models.base import Base
import app.models.evaluacion   # modelo legacy (mantiene compatibilidad)
import app.models.user
import app.models.periodo
import app.models.instrumento
import app.models.docente
import app.models.respuesta
import app.models.puntaje

# Crear todas las tablas (legacy + nuevas)
Base.metadata.create_all(bind=engine)

# Migración: agregar columnas nuevas a tablas existentes (safe — falla silencioso si ya existen)
from sqlalchemy import text as _text
_MIGRATIONS = [
    "ALTER TABLE personal_periodo ADD COLUMN fecha_ingreso DATE",
]
with engine.connect() as _conn:
    for _sql in _MIGRATIONS:
        try:
            _conn.execute(_text(_sql))
            _conn.commit()
        except Exception:
            pass  # columna ya existe

app = FastAPI(title=settings.PROJECT_NAME, version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def auto_seed():
    """Al iniciar: seed catálogos + ETL si la BD está vacía."""
    try:
        from app.etl.pipeline import seed_catalogs, run_full_etl, get_estado
        from app.models.evaluacion import Evaluacion

        db = SessionLocal()

        # Seed catálogos de períodos e instrumentos siempre
        seed_catalogs(db)

        estado = get_estado(db)
        periodos_con_datos = [p for p in estado["periodos"] if p["puntajes"] > 0]

        # Compatibilidad legacy: si la tabla evaluaciones tiene datos, el sistema sigue funcionando
        legacy_count = db.query(Evaluacion).count()

        print(f"[Startup] BD: {estado['total_docentes']} docentes, "
              f"{len(periodos_con_datos)}/6 períodos v2, "
              f"{legacy_count} registros legacy")

        if not periodos_con_datos:
            print("[Startup] Sin datos v2 — iniciando ETL completo...")
            run_full_etl(db)
        else:
            for p in estado["periodos"]:
                status = f"{p['puntajes']} puntajes" if p["puntajes"] > 0 else "sin datos"
                print(f"  {p['codigo']} ({p['label']}): {status}")

        db.close()
    except Exception as e:
        print(f"[Startup] ⚠️  {e}")
        traceback.print_exc()


@app.get("/")
def read_root():
    return {"status": "ok", "version": "2.0.0",
            "message": "PUCESE Evaluación Docente API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(__import__("os").environ.get("PORT", 8000)))
