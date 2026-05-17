"""
Servicio de generación de PDF por docente.
Usa Jinja2 para renderizar HTML y WeasyPrint para convertir a PDF.
"""
import os
from datetime import datetime
from typing import Optional

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from app.models.docente import Docente, PersonalPeriodo
from app.models.puntaje import PuntajeFinal
from app.etl.registry import PERIODOS, PESOS_MODELO, nivel_from_puntaje


# ── Fallback desde tabla legacy evaluaciones ──────────────────────────────────

def _legacy_datos(cedula: str, db: Session) -> tuple:
    """
    Construye proxies de Docente, perfil, puntaje y periodo_info
    desde la tabla evaluaciones (legacy) cuando las nuevas tablas están vacías.
    Retorna (docente, perfil, puntaje, periodo_info) o (None,…) si tampoco hay datos.
    """
    try:
        from app.models.evaluacion import Evaluacion
    except ImportError:
        return None, None, None, None

    ev = (
        db.query(Evaluacion)
        .filter(Evaluacion.cedula == cedula)
        .order_by(Evaluacion.anio.desc(), Evaluacion.id.desc())
        .first()
    )
    if not ev:
        return None, None, None, None

    # ── Docente proxy ─────────────────────────────────────────────────────────
    docente_p = type("DocenteP", (), {
        "cedula":          cedula,
        "nombre_completo": ev.docente_nombre or "—",
        "apellidos":       "",
        "nombres":         ev.docente_nombre or "—",
        "genero":          ev.sexo or "—",
    })()

    # ── Perfil proxy ──────────────────────────────────────────────────────────
    perfil_p = type("PerfilP", (), {
        "facultad":          ev.facultad or "—",
        "funcion":           ev.funcion_docente or "—",
        "dedicacion":        "—",
        "antiguedad_anos":   ev.antiguedad_anos,
        "nivel_instruccion": ev.nivel_estudio or "—",
    })()

    # ── Mapear anio + sistema → período conocido ──────────────────────────────
    anio_str = str(ev.anio) if ev.anio else None
    sistema  = ev.sistema or "meipa"
    candidatos = [p for p in PERIODOS if str(p["anio"]) == anio_str and p["sistema"] == sistema]
    periodo_info = candidatos[-1] if candidatos else PERIODOS[-1]

    # ── Puntaje proxy ─────────────────────────────────────────────────────────
    puntaje_100 = ev.puntaje_100 or ev.promedio or 0.0
    nivel       = ev.nivel_desempeno or nivel_from_puntaje(puntaje_100)

    puntaje_p = type("PuntajeP", (), {
        "cedula":          cedula,
        "periodo_codigo":  periodo_info["codigo"],
        "modelo":          ev.modelo or "docencia",
        "sistema":         sistema,
        "puntaje_100":     puntaje_100,
        "nivel_desempeno": nivel,
        # Componentes 360 normalizados (nueva nomenclatura)
        "comp_het_est":    ev.comp_hetero_est or ev.het_estudiantil,
        "comp_pares":      ev.comp_pares or ev.eval_pares,
        "comp_cev":        ev.aula_virtual,
        "comp_auto":       ev.comp_auto or ev.autoevaluacion,
        "comp_het_dir":    ev.comp_hetero_dir,
        # Componentes_json vacío para MEIPA legacy (la escala original no coincide)
        "componentes_json": None,
    })()

    return docente_p, perfil_p, puntaje_p, periodo_info

LOGO_URL = "https://jorgebanet.com/puce/wp-content/uploads/2025/11/cropped-Logo_PUCESD.png"

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

# Etiquetas legibles por modelo
MODELO_LABELS = {
    "docencia":      "Docencia",
    "abp":           "Salud / ABP",
    "posgrado":      "Posgrado",
    "tecnologado":   "Tecnologado",
    "investigacion": "Investigación",
    "vinculacion":   "Vinculación",
    "gestion":       "Gestión",
}

# Etiquetas de componentes por modelo
COMP_LABELS = {
    "docencia":     [("comp_het_est","Het. Estudiantil",50),("comp_pares","Eval. Pares",20),("comp_cev","Entorno Virtual",10),("comp_auto","Autoevaluación",20)],
    "abp":          [("comp_het_est","Het. Estudiantil (Salud)",50),("comp_pares","Eval. Pares",20),("comp_cev","Entorno Virtual",10),("comp_auto","Autoevaluación",20)],
    "tecnologado":  [("comp_het_est","Het. Estudiantil",50),("comp_pares","Eval. Pares",20),("comp_cev","Entorno Virtual",10),("comp_auto","Autoevaluación",20)],
    "posgrado":     [("comp_het_est","Het. Estudiantil Posgrado",60),("comp_auto","Autoevaluación",30),("comp_cev","CEV / Coord. Posgrado",10)],
    "investigacion":[("comp_het_dir","Het. Dir. Investigación",50),("comp_auto","Autoevaluación",20),("comp_pares","Coevaluación Par",15),("comp_het_est","Het. Decano/Coord.",15)],
    "vinculacion":  [("comp_het_est","Het. Estudiantil",50),("comp_auto","Autoevaluación",20),("comp_het_dir","Het. Dir. Académico",30)],
    "gestion":      [("comp_het_dir","Coevalúa. Directivo",50),("comp_het_est","Het. Docentes",30),("comp_auto","Autoevaluación",20)],
}

# Para MEIPA los componentes vienen en comp_json
MEIPA_COMP_LABELS = [
    ("het_est","Het. Estudiantil (Estud→Doc)",40),
    ("auto","Autoevaluación",20),
    ("coord","Coord→Docente",20),
    ("pares","Eval. Pares",20),
]


def _fmt_puntaje(val) -> str:
    if val is None:
        return "—"
    return f"{val:.1f}"


def _nivel_css(nivel: str) -> str:
    return {
        "Excelente":  "excelente",
        "Bueno":      "bueno",
        "Regular":    "regular",
        "Deficiente": "deficiente",
    }.get(nivel, "sin-datos")


def _antiguedad_str(anos: Optional[float]) -> str:
    if anos is None:
        return "—"
    a = int(anos)
    m = int((anos - a) * 12)
    if a == 0:
        return f"{m} meses"
    if m == 0:
        return f"{a} años"
    return f"{a} años {m} meses"


def _get_ultimo_periodo_docente(cedula: str, db: Session) -> Optional[str]:
    """Devuelve el último período en que el docente tiene puntaje final."""
    orden = [p["codigo"] for p in reversed(PERIODOS)]
    for cod in orden:
        try:
            existe = db.query(PuntajeFinal).filter_by(cedula=cedula, periodo_codigo=cod).first()
        except Exception:
            db.rollback()
            return None
        if existe:
            return cod
    return None


def _get_puntaje_actual(cedula: str, periodo_codigo: str, db: Session) -> Optional[PuntajeFinal]:
    """Obtiene el puntaje principal del docente en el período (prioriza docencia)."""
    prioridad = ["docencia", "abp", "tecnologado", "posgrado", "investigacion", "vinculacion", "gestion"]
    for modelo in prioridad:
        try:
            p = db.query(PuntajeFinal).filter_by(
                cedula=cedula, periodo_codigo=periodo_codigo, modelo=modelo
            ).first()
        except Exception:
            db.rollback()
            return None
        if p:
            return p
    return None


def _build_componentes(puntaje: PuntajeFinal) -> list:
    """Construye la lista de componentes para la tabla del PDF."""
    modelo = puntaje.modelo
    sistema = puntaje.sistema

    componentes = []

    if sistema == "meipa":
        comp_json = puntaje.componentes_json or {}
        # Escalar componentes MEIPA: el valor raw es sobre el peso (ej. het_est max 2.0 → peso 40%)
        for campo, label, peso in MEIPA_COMP_LABELS:
            raw = comp_json.get(campo)
            if raw is None:
                continue
            # El valor raw de MEIPA es la puntuación en escala del peso (0 a peso/100*5)
            # Ya viene guardado como fracción de su peso → convertir a 0-100
            valor_100 = round(min((raw / (peso / 100)) * 100, 100), 1) if raw else 0
            nivel = nivel_from_puntaje(valor_100)
            componentes.append({
                "label":     label,
                "peso":      peso,
                "valor_fmt": _fmt_puntaje(valor_100),
                "pct":       round(min(valor_100, 100), 1),
                "nivel":     nivel,
                "nivel_css": _nivel_css(nivel),
            })
    else:
        defs = COMP_LABELS.get(modelo, [])
        for campo, label, peso in defs:
            valor = getattr(puntaje, campo, None)
            if valor is None:
                continue
            # Los componentes ya están en escala 0-100 (sobre su peso relativo al modelo)
            # Para mostrar en la barra, expresar como % del máximo posible del componente
            pct = round(min(valor, 100), 1)
            nivel = nivel_from_puntaje(valor)
            componentes.append({
                "label":     label,
                "peso":      peso,
                "valor_fmt": _fmt_puntaje(valor),
                "pct":       pct,
                "nivel":     nivel,
                "nivel_css": _nivel_css(nivel),
            })

    return componentes


def _build_historico(cedula: str, db: Session) -> tuple[list, list]:
    """
    Construye la estructura para la tabla histórica.
    Retorna (periodos_lista, modelos_rows).
    """
    # Períodos ordenados cronológicamente
    periodos_info = []
    for p in PERIODOS:
        periodos_info.append({
            "codigo":   p["codigo"],
            "label":    p["label_corto"],
            "sistema":  p["sistema"],
        })

    # Todos los puntajes del docente
    try:
        todos = db.query(PuntajeFinal).filter_by(cedula=cedula).all()
    except Exception:
        db.rollback()
        todos = []
    if not todos:
        return periodos_info, []

    # Agrupar por modelo
    modelos_set = sorted(set(p.modelo for p in todos))

    modelos_rows = []
    for modelo in modelos_set:
        celdas = []
        valores_cronologicos = []
        for p in periodos_info:
            pf = next((x for x in todos if x.periodo_codigo == p["codigo"] and x.modelo == modelo), None)
            valor = pf.puntaje_100 if pf else None
            celdas.append({
                "valor":     valor,
                "valor_fmt": _fmt_puntaje(valor),
                "es_actual": False,  # se marca después
            })
            if valor is not None:
                valores_cronologicos.append(valor)

        # Calcular tendencia (último vs penúltimo con datos)
        tendencia = 0.0
        if len(valores_cronologicos) >= 2:
            tendencia = round(valores_cronologicos[-1] - valores_cronologicos[-2], 1)

        modelos_rows.append({
            "modelo":        modelo,
            "label":         MODELO_LABELS.get(modelo, modelo.capitalize()),
            "celdas":        celdas,
            "tendencia":     tendencia,
            "tendencia_fmt": f"{abs(tendencia):.1f}",
        })

    return periodos_info, modelos_rows


def _build_ranking(cedula: str, periodo_codigo: str, modelo: str, puntaje_100: float, db: Session) -> dict:
    """Calcula posición y percentil del docente en la institución."""
    _no_rank = {"ranking": "—", "percentil": "—", "promedio_inst": None, "diff": None, "diff_str": "—", "diff_color": "#64748b"}
    try:
        todos = db.query(PuntajeFinal).filter_by(
            periodo_codigo=periodo_codigo, modelo=modelo
        ).filter(PuntajeFinal.puntaje_100.isnot(None)).all()
    except Exception:
        db.rollback()
        return _no_rank

    if not todos:
        return _no_rank

    puntajes = sorted([p.puntaje_100 for p in todos], reverse=True)
    promedio = round(sum(puntajes) / len(puntajes), 1)
    pos = next((i+1 for i, v in enumerate(puntajes) if v <= puntaje_100), len(puntajes))
    percentil = round(((len(puntajes) - pos) / len(puntajes)) * 100)

    diff = round(puntaje_100 - promedio, 1)
    diff_color = "#059669" if diff >= 0 else "#dc2626"

    return {
        "ranking":      f"#{pos} / {len(puntajes)}",
        "percentil":    f"P{percentil}",
        "promedio_inst": promedio,
        "diff":         diff,
        "diff_color":   diff_color,
        "diff_str":     f"+{diff}" if diff >= 0 else str(diff),
    }


def generar_pdf_docente(
    cedula: str,
    db: Session,
    periodo_codigo: Optional[str] = None,
) -> bytes:
    """
    Genera el PDF de reporte para un docente.
    Si periodo_codigo es None, usa el último período disponible.
    Retorna bytes del PDF.
    """
    # ── Intentar con tablas nuevas (ETL v2) ──────────────────────────────────
    # Las tablas nuevas pueden no existir aún (se crean al arrancar FastAPI)
    docente = None
    try:
        docente = db.query(Docente).filter_by(cedula=cedula).first()
    except Exception:
        db.rollback()  # libera la transacción rota antes de seguir

    if not docente:
        # Fallback: construir todo desde tabla legacy evaluaciones
        docente, perfil_legacy, puntaje_actual, periodo_info = _legacy_datos(cedula, db)
        if not docente:
            raise ValueError(f"Docente {cedula} no encontrado en ninguna fuente de datos")
        if not puntaje_actual:
            raise ValueError(f"No hay datos de evaluación para el docente {cedula}")
        perfil = perfil_legacy
        periodo_codigo = periodo_info["codigo"]
    else:
        # Resolver período desde tablas nuevas
        if not periodo_codigo:
            periodo_codigo = _get_ultimo_periodo_docente(cedula, db)
        if not periodo_codigo:
            # Docente existe en nueva tabla pero sin puntajes → probar legacy
            _, perfil_legacy, puntaje_actual, periodo_info = _legacy_datos(cedula, db)
            if not puntaje_actual:
                raise ValueError(f"No hay datos de evaluación para el docente {cedula}")
            periodo_codigo = periodo_info["codigo"]
            perfil = perfil_legacy
        else:
            periodo_info = next((p for p in PERIODOS if p["codigo"] == periodo_codigo), None)
            if not periodo_info:
                raise ValueError(f"Período {periodo_codigo} no válido")

            # Perfil del período
            perfil = db.query(PersonalPeriodo).filter_by(
                cedula=cedula, periodo_codigo=periodo_codigo
            ).first()
            if not perfil:
                perfil = db.query(PersonalPeriodo).filter_by(cedula=cedula).first()

            # Puntaje principal
            puntaje_actual = _get_puntaje_actual(cedula, periodo_codigo, db)
            if not puntaje_actual:
                # Puntaje no encontrado en nuevas tablas → fallback legacy
                _, perfil_leg, puntaje_actual, _ = _legacy_datos(cedula, db)
                if not puntaje_actual:
                    raise ValueError(f"No hay puntaje para {cedula} en período {periodo_codigo}")
                if not perfil:
                    perfil = perfil_leg

    # Componentes
    componentes = _build_componentes(puntaje_actual)

    # Ranking
    rank_data = _build_ranking(
        cedula, periodo_codigo, puntaje_actual.modelo, puntaje_actual.puntaje_100, db
    )

    # Histórico
    periodos_lista, historico_modelos = _build_historico(cedula, db)

    # Marcar período actual en el histórico
    for row in historico_modelos:
        for i, p in enumerate(periodos_lista):
            if p["codigo"] == periodo_codigo:
                row["celdas"][i]["es_actual"] = True

    # Colores por nivel
    nivel = puntaje_actual.nivel_desempeno or "Sin datos"
    ranking_colors = {
        "Excelente": "#059669", "Bueno": "#0056b3",
        "Regular": "#d97706", "Deficiente": "#dc2626"
    }

    # Datos del perfil con fallbacks
    class PerfilProxy:
        facultad = "—"
        funcion = "—"
        dedicacion = "—"
        antiguedad_str = "—"
        nivel_instruccion = "—"

    perfil_ctx = PerfilProxy()
    if perfil:
        perfil_ctx.facultad = perfil.facultad or "—"
        perfil_ctx.funcion = perfil.funcion or "—"
        perfil_ctx.dedicacion = perfil.dedicacion or "—"
        perfil_ctx.antiguedad_str = _antiguedad_str(perfil.antiguedad_anos)
        perfil_ctx.nivel_instruccion = perfil.nivel_instruccion or "—"

    # Contexto del template
    ctx = {
        "logo_url":       LOGO_URL,
        "periodo_label":  periodo_info["label_corto"],
        "sistema_label":  "Sistema MEIPA" if periodo_info["sistema"] == "meipa" else "Sistema 360°",
        "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "docente": {
            "cedula":          docente.cedula,
            "nombre_completo": docente.nombre_completo or f"{docente.apellidos} {docente.nombres}".strip(),
            "genero":          docente.genero or "—",
        },
        "perfil": perfil_ctx,
        "puntaje_actual": {
            "puntaje_fmt":    _fmt_puntaje(puntaje_actual.puntaje_100),
            "nivel_desempeno": nivel,
            "modelo_label":   MODELO_LABELS.get(puntaje_actual.modelo, puntaje_actual.modelo),
            "sistema":        puntaje_actual.sistema or "",
        },
        "componentes":    componentes,
        "ranking_str":    rank_data["ranking"],
        "ranking_color":  ranking_colors.get(nivel, "#64748b"),
        "percentil_str":  rank_data["percentil"],
        "promedio_inst_str": _fmt_puntaje(rank_data.get("promedio_inst")),
        "diff_str":       rank_data.get("diff_str", "—"),
        "diff_color":     rank_data.get("diff_color", "#64748b"),
        "historico":      periodos_lista,
        "historico_modelos": historico_modelos,
        "ia_comentario":  None,  # opcional, se puede pasar desde el endpoint
    }

    # Renderizar HTML
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("reporte_docente.html")
    html_str = template.render(**ctx)

    # Convertir a PDF — intenta WeasyPrint primero, cae a xhtml2pdf
    try:
        from weasyprint import HTML as WP_HTML
        pdf_bytes = WP_HTML(string=html_str, base_url=TEMPLATE_DIR).write_pdf()
        return pdf_bytes
    except Exception:
        pass  # WeasyPrint no disponible (Windows sin GTK, etc.) → usar xhtml2pdf

    try:
        import io
        from xhtml2pdf import pisa
        buf = io.BytesIO()
        status = pisa.CreatePDF(html_str, dest=buf)
        if status.err:
            raise RuntimeError("xhtml2pdf falló al generar el PDF")
        return buf.getvalue()
    except ImportError:
        raise RuntimeError(
            "No se pudo generar el PDF. Instala xhtml2pdf: pip install xhtml2pdf"
        )
