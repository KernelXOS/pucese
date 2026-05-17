"""
Orquestador del ETL. Detecta rutas de datos y corre los loaders en orden.
No hace wipe completo: usa upsert por período → re-procesar un período
no afecta los demás.
"""
import os
import warnings
from typing import Optional
from sqlalchemy.orm import Session

from app.etl.registry import PERIODOS, INSTRUMENTOS
from app.etl.loader_personal import load_personal
from app.etl.loader_meipa import load_meipa
from app.etl.loader_360 import load_periodo_360
from app.models.periodo import Periodo
from app.models.instrumento import Instrumento

warnings.filterwarnings("ignore")

# ── Resolución de ruta de datos ───────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))

_DATA_CANDIDATES = [
    "/app/data",
    os.path.join(_HERE, "..", "..", "..", "data"),
    os.path.join(os.getcwd(), "data"),
    r"C:\Users\grego\Desktop\DATOS_DOCENTE",   # desarrollo Windows (grego)
    r"C:\Users\grego\Desktop\DATOS REALES",    # desarrollo Windows (alternativo)
    r"C:\Users\KernelXos\Desktop\DATOS_DOCENTE",
]


def _find_data_root() -> Optional[str]:
    for candidate in _DATA_CANDIDATES:
        if os.path.isdir(candidate):
            return os.path.normpath(candidate)
    return None


def seed_catalogs(db: Session):
    """Inserta catálogos de períodos e instrumentos si no existen."""
    for p in PERIODOS:
        if not db.query(Periodo).filter_by(codigo=p["codigo"]).first():
            db.add(Periodo(**p))

    for inst in INSTRUMENTOS:
        if not db.query(Instrumento).filter_by(cod=inst["cod"]).first():
            db.add(Instrumento(**inst))

    db.commit()
    print("[Pipeline] Catálogos de períodos e instrumentos inicializados.")


def run_full_etl(db: Session, data_root: Optional[str] = None) -> dict:
    """
    Corre el ETL completo para todos los períodos disponibles.
    Orden: catálogos → personal → MEIPA (202301-202401) → 360 (202402-202502)
    """
    if data_root is None:
        data_root = _find_data_root()

    if not data_root:
        raise FileNotFoundError(
            "No se encontró la carpeta de datos. "
            "Coloca los datos en /app/data o en C:/Users/grego/Desktop/DATOS REALES"
        )

    print(f"[Pipeline] Datos en: {data_root}")
    resultados = {"data_root": data_root, "periodos": {}}

    # 1. Catálogos
    seed_catalogs(db)

    # 2. Personal (edades.xlsx → docentes + snapshots para todos los períodos)
    _cargar_personal(data_root, db)

    # 3. MEIPA (202301, 202302, 202401)
    meipa_archivo = _find_meipa(data_root)
    if meipa_archivo:
        res = load_meipa(meipa_archivo, db)
        for p in ["202301", "202302", "202401"]:
            resultados["periodos"][p] = {"sistema": "meipa", "meipa": res}
    else:
        print("[Pipeline] WARN  No se encontró archivo MEIPA")

    # 4. 360 por período
    for periodo_cod, carpeta_360 in _find_360_carpetas(data_root).items():
        res = load_periodo_360(carpeta_360, periodo_cod, db)
        resultados["periodos"][periodo_cod] = {"sistema": "360", **res}

    print("[Pipeline] OK ETL completo finalizado")
    return resultados


def run_periodo(periodo_codigo: str, db: Session, data_root: Optional[str] = None) -> dict:
    """
    Re-procesa un único período sin tocar los demás.
    """
    if data_root is None:
        data_root = _find_data_root()
    if not data_root:
        raise FileNotFoundError("No se encontró carpeta de datos")

    seed_catalogs(db)

    sistema = next(
        (p["sistema"] for p in PERIODOS if p["codigo"] == periodo_codigo), None
    )
    if not sistema:
        raise ValueError(f"Período desconocido: {periodo_codigo}")

    if sistema == "meipa":
        meipa_archivo = _find_meipa(data_root)
        if not meipa_archivo:
            raise FileNotFoundError("Archivo MEIPA no encontrado")
        return load_meipa(meipa_archivo, db)
    else:
        carpetas = _find_360_carpetas(data_root)
        if periodo_codigo not in carpetas:
            raise FileNotFoundError(f"Carpeta 360 no encontrada para {periodo_codigo}")
        return load_periodo_360(carpetas[periodo_codigo], periodo_codigo, db)


# ── Helpers de búsqueda de archivos ──────────────────────────────────────────

def _find_meipa(data_root: str) -> Optional[str]:
    """Busca el archivo MEIPA en la carpeta MEIPA/."""
    meipa_dir = os.path.join(data_root, "MEIPA")
    if not os.path.isdir(meipa_dir):
        # Buscar directamente en data_root
        for f in os.listdir(data_root):
            if "RESULTADOS" in f.upper() and f.endswith(".xlsx"):
                return os.path.join(data_root, f)
        return None
    for f in os.listdir(meipa_dir):
        if f.endswith(".xlsx"):
            return os.path.join(meipa_dir, f)
    return None


def _find_360_carpetas(data_root: str) -> dict:
    """Retorna {periodo_codigo: ruta_carpeta} para las carpetas 360."""
    resultado = {}
    carpeta_360 = os.path.join(data_root, "360")

    if os.path.isdir(carpeta_360):
        for sub in os.listdir(carpeta_360):
            ruta_sub = os.path.join(carpeta_360, sub)
            if os.path.isdir(ruta_sub) and sub.isdigit() and len(sub) == 6:
                resultado[sub] = ruta_sub
    else:
        # Buscar carpetas con nombre de período directamente
        for sub in os.listdir(data_root):
            ruta_sub = os.path.join(data_root, sub)
            if os.path.isdir(ruta_sub) and sub.isdigit() and len(sub) == 6:
                periodo_info = next((p for p in PERIODOS if p["codigo"] == sub), None)
                if periodo_info and periodo_info["sistema"] == "360":
                    resultado[sub] = ruta_sub

    return resultado


def _cargar_personal(data_root: str, db: Session):
    """Carga archivos de personal en orden cronológico."""
    archivos_personal = []

    # Buscar en subcarpeta ANTIGUEDAD
    ant_dir = os.path.join(data_root, "ANTIGUEDAD")
    if os.path.isdir(ant_dir):
        for f in os.listdir(ant_dir):
            if f.endswith(".xlsx"):
                archivos_personal.append((os.path.join(ant_dir, f), "all"))

    # Buscar reportes de personal en data_root
    for f in sorted(os.listdir(data_root)):
        if "REPORTE" in f.upper() and "PERSONAL" in f.upper() and f.endswith(".xlsx"):
            # Detectar año del archivo
            anio = None
            for a in ["2023", "2024", "2025"]:
                if a in f:
                    anio = a
                    break
            archivos_personal.append((os.path.join(data_root, f), anio))

    if not archivos_personal:
        print("[Pipeline] WARN  No se encontraron archivos de personal")
        return

    # Cargar cada archivo para los períodos correspondientes
    for ruta, anio in archivos_personal:
        if anio == "all" or anio is None:
            # edades.xlsx → aplicar a todos los períodos
            for p in PERIODOS:
                load_personal(ruta, p["codigo"], db)
        else:
            # Reporte de un año específico → aplicar a períodos de ese año
            for p in PERIODOS:
                if p["anio"] == anio:
                    load_personal(ruta, p["codigo"], db)


def get_estado(db: Session) -> dict:
    """Retorna conteos actuales por período para diagnóstico."""
    from app.models.puntaje import PuntajeFinal
    from app.models.respuesta import RespuestaRaw
    from app.models.docente import Docente

    total_docentes = db.query(Docente).count()

    periodos_estado = []
    for p in PERIODOS:
        cod = p["codigo"]
        n_finales = db.query(PuntajeFinal).filter_by(periodo_codigo=cod).count()
        n_raw = db.query(RespuestaRaw).filter_by(periodo_codigo=cod).count() if p["sistema"] == "360" else None
        periodos_estado.append({
            "codigo":    cod,
            "label":     p["label_corto"],
            "sistema":   p["sistema"],
            "puntajes":  n_finales,
            "respuestas_raw": n_raw,
        })

    return {
        "total_docentes": total_docentes,
        "periodos": periodos_estado,
    }
