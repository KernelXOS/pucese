from google import genai
from app.core.config import settings

class GeminiService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None and settings.GEMINI_API_KEY:
            try:
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                print(f"Error inicializando Gemini: {e}")
        return self._client

    def answer_question(self, pregunta: str, context: dict) -> str:
        current_client = self.client
        if not current_client:
            return "Gemini API Key no configurada."

        ranking_top = context.get('ranking_top', [])
        ranking_txt = "\n".join(
            f"  {i+1}. {r['nombre']} ({r.get('facultad','?')}) — {r.get('puntaje_100','?')}/100 — {r.get('sistema','?').upper()}"
            for i, r in enumerate(ranking_top[:20])
        )

        criticos = context.get('criticos', [])
        criticos_txt = "\n".join(
            f"  - {r['nombre']} ({r.get('facultad','?')}) — {r.get('puntaje_100','?')}/100"
            for r in criticos[:10]
        )

        comp = context.get('comparativo', {})
        meipa = comp.get('meipa', {})
        tres60 = comp.get('360', {})
        por_genero = comp.get('por_genero', {})
        por_edad = comp.get('por_edad', {})
        por_ant = comp.get('por_antiguedad', {})
        por_fac = comp.get('por_facultad', [])
        genero_edad = comp.get('genero_edad', {})
        genero_ant  = comp.get('genero_antiguedad', {})

        fac_txt = "\n".join(
            f"  {i+1}. {f['facultad']}: {f['promedio']}/100 ({f['n']} registros)"
            for i, f in enumerate(por_fac[:15])
        )

        prompt = f"""
Eres un analista experto en calidad educativa universitaria de la PUCE Esmeraldas.
Tienes acceso a los resultados reales de las evaluaciones docentes y debes responder
la siguiente pregunta con datos concretos, nombres reales y conclusiones claras.

PREGUNTA DEL USUARIO:
"{pregunta}"

=== DATOS REALES DE EVALUACIÓN DOCENTE ===

RESUMEN POR SISTEMA:
  - MEIPA (2023-2024): promedio {meipa.get('promedio','N/D')}/100, {meipa.get('n',0)} registros
  - 360/MECDI (2024-2025): promedio {tres60.get('promedio','N/D')}/100, {tres60.get('n',0)} registros

TOP 20 DOCENTES MEJOR EVALUADOS (nombre, facultad, puntaje, sistema):
{ranking_txt}

DOCENTES QUE NECESITAN ATENCIÓN (puntaje < umbral):
{criticos_txt if criticos_txt else '  (Sin datos críticos disponibles)'}

RANKING DE UNIDADES ACADÉMICAS:
{fac_txt}

ANÁLISIS POR GÉNERO:
{por_genero}

ANÁLISIS POR EDAD:
{por_edad}

ANÁLISIS POR ANTIGÜEDAD:
{por_ant}

CRUCE GÉNERO × EDAD:
{genero_edad}

CRUCE GÉNERO × ANTIGÜEDAD:
{genero_ant}

=== INSTRUCCIONES DE RESPUESTA ===
- Responde directamente la pregunta usando los datos reales.
- Menciona nombres específicos, puntajes y facultades cuando sea relevante.
- Si la pregunta es sobre comparaciones, da cifras exactas de diferencia.
- Sé conciso pero completo (máximo 300 palabras).
- Usa un tono profesional y directo.
- Si los datos no son suficientes para responder, indícalo claramente.
"""
        try:
            response = current_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Error generando respuesta: {str(e)}"

    def generate_executive_analysis(self, kpis: dict):
        current_client = self.client
        if not current_client:
            return f"Gemini API Key no configurada o inválida. (Key presente: {'Sí' if settings.GEMINI_API_KEY else 'No'})"
            
        prompt = f"""
        Actúa como un experto en gestión académica universitaria.
        Analiza los siguientes KPIs de evaluación docente y genera un informe ejecutivo:
        -------------------------------------------------------------------------------------------------------------------------------------------
        - Promedio Institucional: {kpis['promedio_general']}
        - Total de Evaluaciones: {kpis['total_evaluaciones']}
        - Mejor Docente: {kpis['mejor_docente']}
        - Peor Docente: {kpis['peor_docente']}
        - Promedio por Facultad: {kpis['promedio_por_facultad']}
        
        Variables críticas (Promedios por dimensión):
        {kpis.get('variables', 'No disponibles')}
        
        El informe debe incluir:
        1. Interpretación automática de los resultados.
        2. Recomendaciones estratégicas para la universidad.
        3. Alertas académicas basadas en los datos.
        4. Un resumen ejecutivo para las autoridades.
        
        Usa un tono profesional, constructivo y orientado a la mejora continua.
        """
        
        try:
            response = current_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Error generando análisis: {str(e)}"

gemini_service = GeminiService()
