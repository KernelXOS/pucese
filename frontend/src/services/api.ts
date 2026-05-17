import axios from 'axios';

// VITE_API_URL puede venir con o sin /evaluacion al final — normalizamos
const _RAW = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1').replace(/\/+$/, '')
const BASE = _RAW.endsWith('/evaluacion') ? _RAW.slice(0, -'/evaluacion'.length) : _RAW
const EVAL = `${BASE}/evaluacion`;
const DOC  = `${BASE}/docentes`;
const ETL  = `${BASE}/etl`;

function params(opts: Record<string, string | number | undefined>) {
  const p: Record<string, string> = {};
  for (const [k, v] of Object.entries(opts)) {
    if (v !== undefined && v !== null && v !== '') p[k] = String(v);
  }
  return new URLSearchParams(p).toString();
}

export const api = {
  // ── Legacy (compatibilidad con dashboard actual) ───────────────────────────
  getKPIs: (modelo?: string, anio?: number, sistema?: string) =>
    axios.get(`${EVAL}/kpis/institucionales?${params({ modelo, anio, sistema })}`),

  getRanking: (limit = 1000, modelo?: string, anio?: number, sistema?: string) =>
    axios.get(`${EVAL}/ranking?${params({ limit, modelo, anio, sistema })}`),

  getCriticos: (threshold = 3.5, modelo?: string, anio?: number, sistema?: string) =>
    axios.get(`${EVAL}/criticos?${params({ threshold, modelo, anio, sistema })}`),

  getTendencias: (modelo?: string, sistema?: string) =>
    axios.get(`${EVAL}/tendencias?${params({ modelo, sistema })}`),

  getVariables: (modelo?: string, anio?: number, sistema?: string) =>
    axios.get(`${EVAL}/variables?${params({ modelo, anio, sistema })}`),

  getDemograficos: (modelo?: string, anio?: number, sistema?: string) =>
    axios.get(`${EVAL}/demograficos?${params({ modelo, anio, sistema })}`),

  getAIAnalysis: (modelo?: string, anio?: number, sistema?: string) =>
    axios.get(`${EVAL}/analisis-ia?${params({ modelo, anio, sistema })}`),

  getAnalytics: (sistema?: string, modelo?: string, anio?: number) =>
    axios.get(`${EVAL}/analytics?${params({ sistema, modelo, anio })}`),

  getComparativo: (anio?: number) =>
    axios.get(`${EVAL}/comparativo?${params({ anio })}`),

  getTodosDocentes: (anio?: number, modelo?: string, sistema?: string) =>
    axios.get(`${EVAL}/todos-docentes?${params({ anio, modelo, sistema })}`),

  processETL: () => axios.post(`${EVAL}/etl/process`),

  consultaIA: (pregunta: string, anio?: number) =>
    axios.post(`${EVAL}/consulta-ia`, { pregunta, anio }),

  // ── Nuevos: períodos ────────────────────────────────────────────────────────
  getPeriodos: () =>
    axios.get(`${ETL}/periodos`),

  getEstadoETL: () =>
    axios.get(`${ETL}/estado`),

  procesarPeriodo: (periodo: string) =>
    axios.post(`${ETL}/procesar-periodo/${periodo}`),

  // ── Nuevos: docentes ────────────────────────────────────────────────────────
  getDocentes: (opts: { periodo?: string; facultad?: string; modelo?: string; q?: string; limit?: number }) =>
    axios.get(`${DOC}/?${params(opts)}`),

  getPerfilDocente: (cedula: string) =>
    axios.get(`${DOC}/${cedula}/perfil`),

  getCompetenciasDocente: (cedula: string) =>
    axios.get(`${EVAL}/competencias/${cedula}`),

  /** Descarga el PDF del docente. Retorna Blob. */
  descargarReportePDF: async (cedula: string, periodo?: string): Promise<void> => {
    const url = `${DOC}/${cedula}/reporte.pdf${periodo ? `?periodo=${periodo}` : ''}`;
    const resp = await axios.get(url, { responseType: 'blob' });
    const blob = new Blob([resp.data], { type: 'application/pdf' });
    const href = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = href;
    a.download = resp.headers['content-disposition']
      ?.split('filename="')[1]?.replace('"', '')
      || `Reporte_${cedula}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(href);
  },
};
