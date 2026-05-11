import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1/evaluacion';

function params(opts: {
  modelo?: string;
  anio?: number;
  sistema?: string;
  limit?: number;
  threshold?: number;
}) {
  const p: Record<string, string> = {};
  if (opts.modelo)    p['modelo']    = opts.modelo;
  if (opts.anio)      p['anio']      = String(opts.anio);
  if (opts.sistema)   p['sistema']   = opts.sistema;
  if (opts.limit)     p['limit']     = String(opts.limit);
  if (opts.threshold) p['threshold'] = String(opts.threshold);
  return new URLSearchParams(p).toString();
}

export const api = {
  getKPIs: (modelo?: string, anio?: number, sistema?: string) =>
    axios.get(`${API_BASE_URL}/kpis/institucionales?${params({ modelo, anio, sistema })}`),

  getRanking: (limit = 1000, modelo?: string, anio?: number, sistema?: string) =>
    axios.get(`${API_BASE_URL}/ranking?${params({ limit, modelo, anio, sistema })}`),

  getCriticos: (threshold = 3.5, modelo?: string, anio?: number, sistema?: string) =>
    axios.get(`${API_BASE_URL}/criticos?${params({ threshold, modelo, anio, sistema })}`),

  getTendencias: (modelo?: string, sistema?: string) =>
    axios.get(`${API_BASE_URL}/tendencias?${params({ modelo, sistema })}`),

  getVariables: (modelo?: string, anio?: number, sistema?: string) =>
    axios.get(`${API_BASE_URL}/variables?${params({ modelo, anio, sistema })}`),

  getDemograficos: (modelo?: string, anio?: number, sistema?: string) =>
    axios.get(`${API_BASE_URL}/demograficos?${params({ modelo, anio, sistema })}`),

  getAIAnalysis: (modelo?: string, anio?: number, sistema?: string) =>
    axios.get(`${API_BASE_URL}/analisis-ia?${params({ modelo, anio, sistema })}`),

  getAnalytics: (sistema?: string, modelo?: string, anio?: number) =>
    axios.get(`${API_BASE_URL}/analytics?${params({ sistema, modelo, anio })}`),

  getComparativo: (anio?: number) =>
    axios.get(`${API_BASE_URL}/comparativo?${params({ anio })}`),

  getTodosDocentes: (anio?: number) =>
    axios.get(`${API_BASE_URL}/todos-docentes?${params({ anio })}`),

  processETL: () => axios.post(`${API_BASE_URL}/etl/process`),

  consultaIA: (pregunta: string, anio?: number) =>
    axios.post(`${API_BASE_URL}/consulta-ia`, { pregunta, anio }),
};
