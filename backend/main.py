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

# Normalizar códigos de período heredados del ETL legacy → etiquetas legibles
_PERIOD_NORM = [
    ("2023-I",  ("202361", "202301")),
    ("2023-II", ("202366", "202302")),
    ("2024-I",  ("202461", "202401")),
    ("2024-II", ("202402", "202456", "202466")),
    ("2025-I",  ("202501",)),
    ("2025-II", ("202502",)),
]
with engine.connect() as _conn:
    for _label, _codes in _PERIOD_NORM:
        _ph = ",".join(f"'{c}'" for c in _codes)
        try:
            _conn.execute(_text(
                f"UPDATE evaluaciones SET periodo = '{_label}' "
                f"WHERE periodo IN ({_ph}) AND periodo != '{_label}'"
            ))
            _conn.commit()
        except Exception:
            pass

app = FastAPI(title=settings.PROJECT_NAME, version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


def _migrate_evaluaciones_from_puntajes(conn):
    """Puebla la tabla evaluaciones desde puntajes_finales si está vacía."""
    from sqlalchemy import text as _t
    cur = conn.execute(_t("SELECT COUNT(*) FROM evaluaciones"))
    count = cur.scalar()
    if count and count > 0:
        return count  # ya tiene datos

    print("[Startup] Migrando puntajes_finales -> evaluaciones...")
    conn.execute(_t("DELETE FROM evaluaciones"))
    conn.execute(_t("""
        INSERT INTO evaluaciones (
            docente_nombre, facultad, periodo, sexo, edad,
            fecha_proceso, archivo_fuente,
            het_estudiantil, eval_pares, aula_virtual, autoevaluacion,
            puntaje_100, carrera, nivel_desempeno, cedula,
            modelo, anio,
            comp_auto, comp_pares, comp_hetero_dir, comp_hetero_est,
            sistema, antiguedad_anos, funcion_docente
        )
        SELECT
            d.nombre_completo,
            pp.facultad,
            p.label_corto,
            d.genero,
            pp.edad_en_periodo,
            CURRENT_TIMESTAMP,
            'puntajes_finales',
            pf.comp_het_est,
            pf.comp_pares,
            pf.comp_cev,
            pf.comp_auto,
            pf.puntaje_100,
            pp.carrera,
            pf.nivel_desempeno,
            pf.cedula,
            pf.modelo,
            CAST(p.anio AS INTEGER),
            pf.comp_auto,
            pf.comp_pares,
            pf.comp_het_dir,
            pf.comp_het_est,
            pf.sistema,
            pp.antiguedad_anos,
            pp.funcion
        FROM puntajes_finales pf
        LEFT JOIN docentes d ON d.cedula = pf.cedula
        LEFT JOIN personal_periodo pp
               ON pp.cedula = pf.cedula AND pp.periodo_codigo = pf.periodo_codigo
        LEFT JOIN periodos p ON p.codigo = pf.periodo_codigo
        WHERE pf.puntaje_100 IS NOT NULL
    """))
    conn.commit()
    cur2 = conn.execute(_t("SELECT COUNT(*) FROM evaluaciones"))
    inserted = cur2.scalar() or 0
    print(f"[Startup] evaluaciones poblada: {inserted} registros")
    return inserted


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
              f"{len(periodos_con_datos)}/6 periodos v2, "
              f"{legacy_count} registros legacy")

        if not periodos_con_datos:
            # Intentar ETL solo si hay archivos de datos disponibles
            try:
                run_full_etl(db)
            except FileNotFoundError:
                print("[Startup] Sin archivos de datos — se usaran los datos del DB.")
            except Exception as etl_err:
                print(f"[Startup] ETL omitido: {etl_err}")

        # Migrar evaluaciones desde puntajes_finales si está vacía (siempre)
        with engine.connect() as _conn:
            _migrate_evaluaciones_from_puntajes(_conn)

        # Actualizar estado después de migración
        estado2 = get_estado(db)
        for p in estado2["periodos"]:
            status = f"{p['puntajes']} puntajes" if p["puntajes"] > 0 else "sin datos"
            print(f"  {p['codigo']} ({p['label']}): {status}")

        db.close()
    except Exception as e:
        print(f"[Startup] Advertencia: {e}")
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
