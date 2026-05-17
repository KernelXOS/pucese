import React, { useState, useEffect, useCallback } from 'react'
import Plot from 'react-plotly.js'
import { api } from './services/api'
import {
  BarChart3, Users, TrendingUp, BrainCircuit, RefreshCw, Award,
  FileText, Search, BookOpen, Star, CheckCircle, AlertCircle, XCircle,
  Microscope, Heart, Link2, Briefcase, GraduationCap, Calendar,
  Activity, UserCheck, Menu, Bell, LogOut, ChevronDown, ChevronRight,
  LayoutDashboard, Building2, Cpu, Download,
} from 'lucide-react'

const LOGO_URL = 'https://jorgebanet.com/puce/wp-content/uploads/2025/11/cropped-Logo_PUCESD.png'

// ── Model tabs (for 360) ──────────────────────────────────────────────────────
const TABS_360 = [
  { id: 'docencia',       label: 'Docencia',        icon: GraduationCap, color: '#0056b3', desc: 'Het.Est.50 · Par.20 · CEV.10 · Auto.20' },
  { id: 'abp',            label: 'Salud / ABP',      icon: Heart,         color: '#dc2626', desc: 'Het.Est.50 · Par.20 · CEV.10 · Auto.20' },
  { id: 'posgrado',       label: 'Posgrado',         icon: BookOpen,      color: '#8b5cf6', desc: 'Het.Est.60 · Auto.30 · CEV.10' },
  { id: 'tecnologado',    label: 'Tecnologado',      icon: Cpu,           color: '#0891b2', desc: 'Het.Est.50 · Par.20 · CEV.10 · Auto.20' },
  { id: 'vinculacion',    label: 'Vinculación',      icon: Link2,         color: '#059669', desc: 'Het.Est.50 · Auto.20 · Dir.Acad.15 · Dir.Inv.15' },
  { id: 'gestion',        label: 'Gestión',          icon: Briefcase,     color: '#d97706', desc: 'Coevalúa.Dir.50 · Het.Doc.30 · Auto.20' },
  { id: 'investigacion',  label: 'Investigación',    icon: Microscope,    color: '#7c3aed', desc: 'Het.Dir.Inv.50 · Auto.20 · Par.15 · Decano.15' },
]

// Labels and max-points per component (max = peso = max contribution to /100 total)
const TAB_COMP_LABELS: Record<string, {label: string; max: number}[]> = {
  // Docencia, ABP, Tecnologado: Het.Est(50) + Pares(20) + CEV(10) + Auto(20)
  docencia:       [{label:'Het. Estudiantil',max:50},{label:'Eval. Pares',max:20},{label:'CEV / Entorno Virtual',max:10},{label:'Autoevaluación',max:20}],
  abp:            [{label:'Het. Estudiantil (Med.)',max:50},{label:'Eval. Pares',max:20},{label:'CEV / Entorno Virtual',max:10},{label:'Autoevaluación',max:20}],
  tecnologado:    [{label:'Het. Estudiantil',max:50},{label:'Eval. Pares',max:20},{label:'CEV / Entorno Virtual',max:10},{label:'Autoevaluación',max:20}],
  // Posgrado: Het.Est(60) + Auto(30) + CEV(10) — solo 3 componentes
  posgrado:       [{label:'Het. Estudiantil Posgrado',max:60},{label:'Autoevaluación',max:30},{label:'CEV / Coord. Posgrado',max:10}],
  // Vinculación: Het.Est(50) + Auto(20) + Het.Dir.Acad(15) + Het.Dir.Invest.(15)
  vinculacion:    [{label:'Het. Estudiantil',max:50},{label:'Autoevaluación',max:20},{label:'Het. Dir. Académico',max:15},{label:'Het. Dir. Investigación',max:15}],
  // Gestión / Administrativo: Coevalúa.Dir(50) + Het.Docentes(30) + Auto(20)
  gestion:        [{label:'Coevalúa. Directivo Superior',max:50},{label:'Het. Docentes',max:30},{label:'Autoevaluación',max:20}],
  administrativo: [{label:'Coevalúa. Directivo Superior',max:50},{label:'Het. Docentes',max:30},{label:'Autoevaluación',max:20}],
  // Investigación: Het.Dir.Invest(50) + Auto(20) + Par(15) + Decano(15)
  investigacion:  [{label:'Het. Dir. Investigación',max:50},{label:'Autoevaluación',max:20},{label:'Coevaluación Par',max:15},{label:'Het. Decano/Coord.',max:15}],
  // MEIPA: componentes sobre 100 cada uno (escala propia, peso indicado)
  meipa:          [{label:'Het. Estudiantil (40%)',max:100},{label:'Autoevaluación (20%)',max:100},{label:'Coord→Docente (20%)',max:100},{label:'Eval. Pares (20%)',max:100}],
}

const TAB_COMP_KEYS: Record<string, string[]> = {
  docencia:       ['het_estudiantil','eval_pares','aula_virtual','autoevaluacion'],
  abp:            ['het_estudiantil','eval_pares','aula_virtual','autoevaluacion'],
  tecnologado:    ['het_estudiantil','eval_pares','aula_virtual','autoevaluacion'],
  posgrado:       ['het_estudiantil','autoevaluacion','aula_virtual'],          // sin pares
  vinculacion:    ['comp_hetero_est','comp_auto','comp_hetero_dir','comp_pares'],
  gestion:        ['comp_hetero_dir','comp_hetero_est','comp_auto'],
  administrativo: ['comp_hetero_dir','comp_hetero_est','comp_auto'],
  investigacion:  ['comp_hetero_dir','comp_auto','comp_pares','comp_hetero_est'],
  meipa:          ['comp_hetero_est','comp_auto','comp_hetero_dir','comp_pares'],
}

const COMP_COLORS = ['#0056b3','#7c3aed','#10b981','#f59e0b','#ef4444']

// ── Splash ────────────────────────────────────────────────────────────────────
function SplashScreen({ visible, fading }: { visible: boolean; fading: boolean }) {
  if (!visible) return null
  return (
    <div className="fixed inset-0 z-50 flex flex-col" style={{ background:'#fff', opacity: fading?0:1, transition:'opacity 0.8s cubic-bezier(0.4,0,0.2,1)', pointerEvents: fading?'none':'all' }}>
      <div className="h-[3px] w-full" style={{ background:'linear-gradient(90deg,#001f4d,#0056b3,#1a78d4)' }} />
      <div className="flex-1 flex flex-col items-center justify-center px-8">
        <img
          src={LOGO_URL}
          alt="PUCESE"
          className="object-contain mb-10"
          style={{ height: 110, filter:'drop-shadow(0 4px 16px rgba(0,86,179,0.13))' }}
        />
        <div className="w-56 h-[2px] rounded-full overflow-hidden bg-slate-100">
          <div className="splash-bar h-full rounded-full" style={{ width:0, background:'linear-gradient(90deg,#0056b3,#1a78d4)' }} />
        </div>
        <p className="mt-3 text-[10px] font-bold text-slate-400 tracking-[0.3em] uppercase animate-pulse">Cargando…</p>
      </div>
      <div className="px-8 py-4 border-t border-slate-100 flex items-center justify-between" style={{ background:'#fafbfc' }}>
        <p className="text-[10px] text-slate-400 font-medium">© 2025 · PUCESE · Dirección de Calidad y Acreditación</p>
        <p className="text-[10px] font-black text-slate-300 tracking-widest uppercase">v4.0</p>
      </div>
    </div>
  )
}

function NivelBadge({ nivel }: { nivel: string }) {
  const map: Record<string,{color:string;bg:string;border:string;icon:any}> = {
    'Excelente':  { color:'#059669', bg:'#ecfdf5', border:'#a7f3d0', icon:Star },
    'Bueno':      { color:'#0056b3', bg:'#eff6ff', border:'#bfdbfe', icon:CheckCircle },
    'Regular':    { color:'#d97706', bg:'#fef3c7', border:'#fde68a', icon:AlertCircle },
    'Deficiente': { color:'#dc2626', bg:'#fef2f2', border:'#fecaca', icon:XCircle },
  }
  const s = map[nivel] || { color:'#64748b', bg:'#f8fafc', border:'#e2e8f0', icon:FileText }
  const Icon = s.icon
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-black px-2.5 py-1 rounded-lg border" style={{ color:s.color, background:s.bg, borderColor:s.border }}>
      <Icon size={10}/>{nivel || 'Sin datos'}
    </span>
  )
}

function ComponentBar({ label, value, max, peso, color }: { label:string; value:number; max:number; peso:number; color:string }) {
  const pct = max > 0 ? Math.min((value/max)*100,100) : 0
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <div>
          <span className="text-[10px] font-black text-slate-600">{label}</span>
          <span className="ml-2 text-[9px] font-semibold text-slate-400">(peso {peso}%)</span>
        </div>
        <div className="text-right">
          <span className="text-sm font-black" style={{ color }}>{value.toFixed(1)}</span>
          <span className="text-[9px] text-slate-400">/{max}</span>
        </div>
      </div>
      <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width:`${pct}%`, background:color }} />
      </div>
    </div>
  )
}

function KPICard({ title, value, label, icon, iconBg, footer, badge, badgeStyle, accent }: any) {
  return (
    <div className="bg-white border border-slate-200 relative overflow-hidden transition-shadow hover:shadow-md"
      style={{ borderRadius: 6, borderTop: `3px solid ${accent}`, boxShadow:'0 1px 3px rgba(0,0,0,0.06)', padding:'20px 22px' }}>
      <div className="flex items-start justify-between mb-4">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.22em] leading-tight">{title}</p>
        {badge && (
          <span className="text-[9px] font-bold px-2 py-0.5 rounded" style={badgeStyle}>{badge}</span>
        )}
      </div>
      <div className="flex items-baseline gap-2 flex-wrap mb-1">
        <span className="font-black text-slate-900 leading-none" style={{ fontSize: 26, letterSpacing: '-0.02em' }}>{value}</span>
        {label && <span className="text-[11px] text-slate-400 font-medium">{label}</span>}
      </div>
      <div className="mt-4 pt-3 border-t border-slate-100">
        <p className="text-[10px] text-slate-400">{footer}</p>
      </div>
    </div>
  )
}

// ── Analytics section ─────────────────────────────────────────────────────────
function AnalyticsSection({ analytics, color }: { analytics: any; color: string }) {
  if (!analytics) return null

  const genero    = analytics.por_genero     || {}
  const edad      = analytics.por_edad       || {}
  const antiguedad= analytics.por_antiguedad || {}
  const funcion   = analytics.por_funcion    || {}

  const mk3D = (keys:string[], vals:number[], colors:string|string[]) =>
    excel3DBar(keys, vals, colors)

  const filterNulls = (obj: Record<string, number|null>) => ({
    keys: Object.keys(obj).filter(k => obj[k] !== null),
    vals: Object.values(obj).filter(v => v !== null) as number[],
  })

  const { keys: gKeys, vals: gVals } = filterNulls(genero)
  const { keys: eKeys, vals: eVals } = filterNulls(edad)
  const { keys: aKeys, vals: aVals } = filterNulls(antiguedad)
  const { keys: fKeys, vals: fVals } = filterNulls(funcion)

  return (
    <div className="bg-white border border-slate-200 overflow-hidden mb-8" style={{ borderRadius: 6, boxShadow:'0 1px 3px rgba(0,0,0,0.06)' }}>
      <div className="px-5 py-3.5 border-b border-slate-100 flex items-center gap-3">
        <Activity size={14} style={{ color, opacity: 0.8 }} />
        <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em]">Análisis Comparativo ·</span>
        <h3 className="text-[13px] font-bold text-slate-700">Desempeño por Variables Demográficas</h3>
      </div>
      <div className="p-5 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">

        {/* Por género */}
        {gKeys.length > 0 && (() => { const c = mk3D(gKeys,gVals,['#0f5ca8','#be185d','#64748b']); return (
          <div className="border border-slate-100 overflow-hidden" style={{ borderRadius: 4 }}>
            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest px-4 pt-3">Por Género</p>
            <Plot data={c.data} layout={c.layout} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'220px'}} />
          </div>
        )})()}

        {/* Por edad */}
        {eKeys.length > 0 && (() => { const c = mk3D(eKeys,eVals,color); return (
          <div className="border border-slate-100 overflow-hidden" style={{ borderRadius: 4 }}>
            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest px-4 pt-3">Por Edad</p>
            <Plot data={c.data} layout={c.layout} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'220px'}} />
          </div>
        )})()}

        {/* Por antigüedad */}
        {aKeys.length > 0 && (() => { const c = mk3D(aKeys,aVals,'#047857'); return (
          <div className="border border-slate-100 overflow-hidden" style={{ borderRadius: 4 }}>
            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest px-4 pt-3">Por Antigüedad</p>
            <Plot data={c.data} layout={c.layout} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'220px'}} />
          </div>
        )})()}

        {/* Por función */}
        {fKeys.length > 0 && (() => { const c = mk3D(fKeys,fVals,'#92400e'); return (
          <div className="border border-slate-100 overflow-hidden" style={{ borderRadius: 4 }}>
            <p className="text-[9px] font-bold text-slate-400 uppercase tracking-widest px-4 pt-3">Por Función</p>
            <Plot data={c.data} layout={c.layout} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'220px'}} />
          </div>
        )})()}

        {(gKeys.length + eKeys.length + aKeys.length + fKeys.length) === 0 && (
          <div className="col-span-4 py-12 text-center text-slate-400 text-xs font-bold">
            No hay datos de analytics disponibles para este filtro.
          </div>
        )}
      </div>
    </div>
  )
}

// ── Shared chart helpers ───────────────────────────────────────────────────────
const CARD_SHADOW = { boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }

function ChartCard({ title, sub, children }: { title: string; sub?: string; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-slate-200 overflow-hidden" style={{ borderRadius: 6, boxShadow:'0 1px 3px rgba(0,0,0,0.06)' }}>
      <div className="px-5 py-3.5 border-b border-slate-100 flex items-center gap-2">
        {sub && <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em]">{sub} ·</span>}
        <h3 className="text-[13px] font-bold text-slate-700">{title}</h3>
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

// ── Institutional color system ─────────────────────────────────────────────────
const IC = {
  primary:  '#1e3a5f',   // deep institutional navy (sidebar, titles)
  blue:     '#1e40af',   // institutional blue (charts, primary actions)
  blueAlt:  '#2563eb',   // slightly lighter blue
  steel:    '#64748b',   // neutral steel gray
  success:  '#15803d',   // performance ≥ 90
  warning:  '#b45309',   // performance ≥ 60
  danger:   '#b91c1c',   // performance < 60
  neutral:  '#94a3b8',   // neutral / inactive
  border:   '#e2e8f0',
  bg:       '#f5f7fa',
  female:   '#9f1239',
  male:     '#1e40af',
}

function perfColor(v: number): string {
  return v >= 90 ? IC.success : v >= 75 ? IC.blue : v >= 60 ? IC.warning : IC.danger
}

// ── Power BI–style flat bar chart helpers ──────────────────────────────────────

function flatBar(
  labels: string[],
  values: number[],
  colors: string | string[],
  opts: { maxY?: number; tickAngle?: number; marginB?: number; showMeta?: boolean } = {}
): { data: any[]; layout: any } {
  const maxY = opts.maxY ?? 105
  const c = Array.isArray(colors) ? colors : labels.map(()=>colors as string)
  const mB = opts.marginB ?? (labels.some(l=>l.length>10) ? 105 : labels.some(l=>l.length>6) ? 75 : 50)

  const shapes: any[] = opts.showMeta !== false && values.some(v=>v>0) ? [{
    type:'line', x0:-0.5, x1:labels.length-0.5, y0:90, y1:90,
    line:{ color:'#15803d', width:1.2, dash:'dot' },
  }] : []
  const annotations: any[] = opts.showMeta !== false && values.some(v=>v>0) ? [{
    x:0, y:90, xref:'paper', yref:'y',
    text:'Meta 90', showarrow:false,
    font:{ size:8.5, color:'#15803d', family:'Inter', weight:600 },
    xanchor:'left', yanchor:'bottom', yshift:3,
  }] : []

  return {
    data: [{
      type:'bar', x:labels, y:values,
      marker:{ color:c, line:{ width:0 }, opacity:0.9 },
      text: values.map(v=>`${v.toFixed(1)}`),
      textposition:'outside',
      textfont:{ family:'Inter', size:8.5, color:'#475569' },
      hovertemplate:'<b>%{x}</b><br>%{y:.2f} / 100<extra></extra>',
      showlegend:false,
    }],
    layout:{
      autosize:true, paper_bgcolor:'white', plot_bgcolor:'white',
      font:{ family:'Inter', size:9, color:'#64748b' },
      margin:{ t:22, b:mB, l:44, r:14 },
      xaxis:{
        tickfont:{ family:'Inter', size:9, color:'#334155' },
        tickangle: opts.tickAngle ?? (labels.length>6?-32:0),
        showgrid:false, zeroline:false, showline:false,
        tickcolor:'#e2e8f0',
      },
      yaxis:{
        gridcolor:'#f0f4f8', range:[0,maxY+10],
        tickfont:{ family:'Inter', size:9, color:'#94a3b8' },
        showgrid:true, zeroline:true, zerolinecolor:'#e2e8f0',
        nticks:6, gridwidth:1,
      },
      bargap:0.40, shapes, annotations, showlegend:false,
    },
  }
}

/** Power BI–style grouped bar chart */
function flatBarGrouped(
  groupLabels: string[],
  series: { name:string; values:(number|null)[]; color:string }[],
  opts: { maxY?:number } = {}
): { data:any[]; layout:any } {
  const maxY = opts.maxY ?? 105
  return {
    data: series.map(ser=>({
      type:'bar', name:ser.name,
      x:groupLabels,
      y:groupLabels.map((_,i)=>ser.values[i]??0),
      marker:{ color:ser.color, line:{ width:0 }, opacity:0.9 },
      hovertemplate:`<b>${ser.name}</b><br>%{x}: %{y:.2f}/100<extra></extra>`,
    })),
    layout:{
      autosize:true, paper_bgcolor:'white', plot_bgcolor:'white',
      font:{ family:'Inter', size:9, color:'#64748b' },
      margin:{ t:22, b:70, l:44, r:14 },
      xaxis:{ tickfont:{ family:'Inter',size:9,color:'#334155' }, tickangle:-20, showgrid:false, zeroline:false, showline:false },
      yaxis:{ gridcolor:'#f0f4f8', range:[0,maxY+10], tickfont:{ family:'Inter',size:9,color:'#94a3b8' }, showgrid:true, zeroline:true, zerolinecolor:'#e2e8f0', nticks:6, gridwidth:1 },
      barmode:'group', bargap:0.30, bargroupgap:0.06,
      showlegend:true,
      legend:{ font:{ family:'Inter',size:10,color:'#334155' }, orientation:'h', y:-0.22, bgcolor:'rgba(0,0,0,0)', borderwidth:0 },
    },
  }
}

// Aliases for backward compat (renamed from excel3D*)
const excel3DBar     = flatBar
const excel3DGrouped = (gl:string[], s:any[], o?:any) => flatBarGrouped(gl, s, o)

/** Premium 2-D trend line — clean spline with tight y-range, no fill-to-zero */
function trendLine2D(
  traces: { x:any[]; y:number[]; color:string; name:string; dash?:string }[],
  opts: { minY?:number; maxY?:number } = {}
): { data:any[]; layout:any } {
  const allY = traces.flatMap(t=>t.y)
  const minY = opts.minY ?? Math.max(0, Math.floor(Math.min(...allY)) - 3)
  const maxY = opts.maxY ?? Math.ceil(Math.max(...allY)) + 5
  return {
    data: traces.map(t => ({
      type:'scatter', mode:'lines+markers+text',
      x:t.x, y:t.y, name:t.name,
      line:{color:t.color, width:3, shape:'spline', smoothing:0.7, dash:t.dash??'solid'},
      marker:{size:8, color:'white', symbol:'circle', line:{color:t.color, width:2.5}},
      text:t.y.map(v=>v.toFixed(1)),
      textposition:'top center',
      textfont:{family:'Inter',size:9,color:t.color},
      hovertemplate:`<b>${t.name}</b><br>%{x}: %{y:.2f}/100<extra></extra>`,
    })),
    layout:{
      autosize:true, paper_bgcolor:'white', plot_bgcolor:'white',
      font:{family:'Inter',size:9,color:'#64748b'},
      margin:{t:24,b:50,l:44,r:10},
      xaxis:{gridcolor:'#f0f4f8',dtick:1,tickformat:'d',
        tickfont:{family:'Inter',size:11,color:'#1e293b'},
        showgrid:false,zeroline:false,showline:true,linecolor:'#e2e8f0'},
      yaxis:{gridcolor:'#f0f4f8',range:[minY,maxY],
        tickfont:{family:'Inter',size:9,color:'#94a3b8'},showgrid:true,zeroline:false,nticks:6,gridwidth:1},
      showlegend: traces.length>1,
      legend:{font:{family:'Inter',size:10,color:'#334155'},orientation:'h',y:-0.22,
        bgcolor:'rgba(0,0,0,0)',borderwidth:0},
      shapes:[{type:'line',x0:traces[0].x[0],x1:traces[0].x[traces[0].x.length-1],
        y0:90,y1:90,line:{color:'#10b981',width:1.5,dash:'dot'}}],
    },
  }
}

// Legacy (pie/donut charts only)
function barLayout(opts: { tickAngle?: number; marginB?: number; maxY?: number } = {}): any {
  return {
    autosize:true, paper_bgcolor:'white', plot_bgcolor:'white',
    font:{color:'#94a3b8',family:'Inter',size:9},
    margin:{t:8,b:opts.marginB??60,l:42,r:8},
    xaxis:{gridcolor:'#f8fafc',tickangle:opts.tickAngle??-30},
    yaxis:{gridcolor:'#f1f5f9',range:[0,opts.maxY??105]},
    bargap:0.38,
  }
}

// ── AI Q&A Panel ──────────────────────────────────────────────────────────────
const PREGUNTAS = [
  '¿Cuál fue el mejor docente en general?',
  '¿Quién cumplió todos los parámetros de evaluación?',
  '¿Qué sistema fue más efectivo, MEIPA o 360?',
  '¿Qué género tuvo mejor desempeño y por qué?',
  '¿Los docentes más antiguos son mejores evaluados?',
  '¿Cuál fue la mejor unidad académica?',
  '¿Qué docentes necesitan apoyo o plan de mejora?',
  '¿Cómo influye la edad en el desempeño docente?',
  '¿Quiénes mejoraron más entre años?',
  '¿Las mujeres jóvenes rinden mejor que las mayores?',
]

function AIConsultaPanel({ anio }: { anio?: number }) {
  const [pregunta, setPregunta] = useState('')
  const [respuesta, setRespuesta] = useState('')
  const [loading, setLoading] = useState(false)
  const [preguntaActiva, setPreguntaActiva] = useState<string | null>(null)

  const preguntar = async (q: string) => {
    if (!q.trim() || loading) return
    setLoading(true)
    setRespuesta('')
    setPreguntaActiva(q)
    try {
      const res = await api.consultaIA(q, anio)
      setRespuesta(res.data.respuesta)
    } catch {
      setRespuesta('Error al conectar con la IA. Verifica que la API Key de Gemini esté configurada.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white border border-slate-200 overflow-hidden mb-6"
      style={{ borderRadius: 6, boxShadow: '0 1px 3px rgba(0,0,0,0.06)', borderLeft: '3px solid #4f46e5' }}>

      {/* Header */}
      <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BrainCircuit size={14} className="text-indigo-400" />
          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em]">Inteligencia Artificial ·</span>
          <h3 className="text-[13px] font-bold text-slate-700">Consulta sobre Evaluación Docente</h3>
        </div>
        <span className="text-[9px] font-bold px-2 py-1 rounded text-indigo-500 border border-indigo-100 bg-indigo-50" style={{ borderRadius: 4 }}>
          Gemini
        </span>
      </div>

      <div className="p-6 space-y-5">
        {/* Preset chips */}
        <div>
          <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-3">
            Preguntas frecuentes — haz clic para consultar
          </p>
          <div className="flex flex-wrap gap-2">
            {PREGUNTAS.map(q => (
              <button
                key={q}
                onClick={() => preguntar(q)}
                disabled={loading}
                className="text-[10px] font-semibold px-3 py-1.5 rounded-full border transition-all disabled:opacity-50"
                style={{
                  borderColor: preguntaActiva === q && respuesta ? '#4f46e5' : '#e2e8f0',
                  background: preguntaActiva === q && respuesta ? '#eef2ff' : '#f8fafc',
                  color: preguntaActiva === q && respuesta ? '#4f46e5' : '#64748b',
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Custom input */}
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Escribe tu propia pregunta sobre los datos de evaluación…"
              className="w-full pl-9 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs focus:outline-none focus:border-indigo-400 transition-all"
              value={pregunta}
              onChange={e => setPregunta(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && preguntar(pregunta)}
              disabled={loading}
            />
          </div>
          <button
            onClick={() => preguntar(pregunta)}
            disabled={loading || !pregunta.trim()}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white disabled:opacity-50 transition-all"
            style={{ background: 'linear-gradient(135deg,#4f46e5,#7c3aed)', boxShadow: '0 4px 12px rgba(79,70,229,0.25)' }}
          >
            {loading
              ? <><div className="w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin" /> Analizando…</>
              : <><BrainCircuit size={12} /> Consultar</>
            }
          </button>
        </div>

        {/* Response */}
        {(loading || respuesta) && (
          <div className="rounded-xl border border-indigo-100 bg-indigo-50/40 p-5 min-h-[80px]">
            {loading ? (
              <div className="flex items-center gap-3 text-indigo-400">
                <div className="w-4 h-4 rounded-full border-2 border-indigo-200 border-t-indigo-500 animate-spin flex-shrink-0" />
                <span className="text-xs font-semibold animate-pulse">Analizando los datos reales de evaluación…</span>
              </div>
            ) : (
              <>
                {preguntaActiva && (
                  <p className="text-[9px] font-black text-indigo-400 uppercase tracking-widest mb-3">
                    Respuesta a: "{preguntaActiva}"
                  </p>
                )}
                <p className="text-[11px] text-slate-700 leading-relaxed whitespace-pre-wrap">{respuesta}</p>
              </>
            )}
          </div>
        )}

        {!loading && !respuesta && (
          <div className="flex items-center gap-3 py-4 text-slate-400">
            <BrainCircuit size={20} className="text-indigo-200 flex-shrink-0" />
            <p className="text-xs font-semibold">
              Selecciona una pregunta frecuente o escribe la tuya. La IA analizará los datos reales de evaluación docente para responder.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Comparativo panel ─────────────────────────────────────────────────────────
function ComparativoPanel({ comparativo }: { comparativo: any }) {
  if (!comparativo) return null

  const meipa      = comparativo.meipa || { promedio: null, n: 0 }
  const tres60     = comparativo['360'] || { promedio: null, n: 0 }
  const porModelo: Record<string, any> = comparativo.por_modelo_360 || {}
  const tendMeipa: any[]  = comparativo.tendencia_meipa || []
  const tend360:   any[]  = comparativo.tendencia_360   || []
  const tendPeriodosMeipa: any[] = comparativo.tendencia_periodos_meipa || []
  const tendPeriodos360:   any[] = comparativo.tendencia_periodos_360   || []
  const porModeloPeriodo: Record<string, any[]> = comparativo.por_modelo_por_periodo || {}
  const generoPorPeriodo: any[]  = comparativo.genero_por_periodo       || []
  const edadPorPeriodo:   any[]  = comparativo.edad_por_periodo         || []
  const antiguedadPorPeriodo: any[] = comparativo.antiguedad_por_periodo || []
  const porFacultad: any[] = comparativo.por_facultad   || []
  const porGenero: Record<string, number> = comparativo.por_genero || {}
  const porEdad: Record<string, number|null> = comparativo.por_edad || {}
  const porAnt: Record<string, number|null>  = comparativo.por_antiguedad || {}
  const generoEdad: Record<string, Record<string, number|null>> = comparativo.genero_edad || {}
  const generoAnt: Record<string, Record<string, number|null>>  = comparativo.genero_antiguedad || {}

  const AGE_BRACKETS  = ['< 30 años', '31-45 años', '46-60 años', '61+ años']
  const ANTIG_BRACKETS = ['0-3 años', '4-10 años', '11-20 años', '20+ años']

  const filterNull = (obj: Record<string, number|null>) => ({
    keys: Object.keys(obj).filter(k => obj[k] != null),
    vals: Object.values(obj).filter(v => v != null) as number[],
  })

  const { keys: gKeys, vals: gVals } = filterNull(porGenero as any)
  const { keys: eKeys, vals: eVals } = filterNull(porEdad)
  const { keys: aKeys, vals: aVals } = filterNull(porAnt)

  const GENDER_COLORS: Record<string, string> = { 'Mujer': '#f43f5e', 'Hombre': '#0056b3' }
  const gColors = gKeys.map(k => GENDER_COLORS[k] || '#94a3b8')

  // Best / worst label helpers
  const bestKey = (obj: Record<string, number|null>) => {
    const filtered = Object.entries(obj).filter(([, v]) => v != null) as [string, number][]
    if (!filtered.length) return null
    return filtered.reduce((a, b) => a[1] > b[1] ? a : b)[0]
  }
  const bestGenero  = bestKey(porGenero as any)
  const bestEdad    = bestKey(porEdad)
  const bestAnt     = bestKey(porAnt)

  return (
    <div className="space-y-6 mb-8">

      {/* ── Row 1: MEIPA vs 360 summary cards ─────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white border border-slate-200 col-span-1"
          style={{ borderRadius: 6, borderTop:'3px solid #6366f1', boxShadow:'0 1px 3px rgba(0,0,0,0.06)', padding:'18px 20px' }}>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-3">MEIPA · 2023–2024</p>
          <div className="flex items-baseline gap-1.5 mb-1">
            <span className="font-black text-slate-900" style={{ fontSize:28, letterSpacing:'-0.02em' }}>{meipa.promedio ?? '—'}</span>
            <span className="text-xs text-slate-400">/ 100</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-3 pt-3 border-t border-slate-100">{meipa.n} registros</p>
        </div>

        <div className="bg-white border border-slate-200 col-span-1"
          style={{ borderRadius: 6, borderTop:'3px solid #1e40af', boxShadow:'0 1px 3px rgba(0,0,0,0.06)', padding:'18px 20px' }}>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-3">360 / MECDI · 2024–2025</p>
          <div className="flex items-baseline gap-1.5 mb-1">
            <span className="font-black text-[#1e40af]" style={{ fontSize:28, letterSpacing:'-0.02em' }}>{tres60.promedio ?? '—'}</span>
            <span className="text-xs text-slate-400">/ 100</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-3 pt-3 border-t border-slate-100">{tres60.n} registros</p>
        </div>

        {/* Best gender insight */}
        <div className="bg-white border border-slate-200 col-span-1"
          style={{ borderRadius: 6, borderTop:`3px solid ${bestGenero ? GENDER_COLORS[bestGenero] : '#94a3b8'}`, boxShadow:'0 1px 3px rgba(0,0,0,0.06)', padding:'18px 20px' }}>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-3">Mejor Género · Promedio global</p>
          <div className="flex items-baseline gap-1.5 mb-1">
            <span className="font-black" style={{ fontSize:24, letterSpacing:'-0.01em', color: bestGenero ? GENDER_COLORS[bestGenero] : '#94a3b8' }}>
              {bestGenero ?? '—'}
            </span>
          </div>
          <p className="text-[10px] text-slate-400 mt-3 pt-3 border-t border-slate-100">
            {bestGenero && porGenero[bestGenero] != null ? `${porGenero[bestGenero]}/100 pts` : 'Sin datos'}
          </p>
        </div>

        {/* Best seniority insight */}
        <div className="bg-white border border-slate-200 col-span-1"
          style={{ borderRadius: 6, borderTop:'3px solid #15803d', boxShadow:'0 1px 3px rgba(0,0,0,0.06)', padding:'18px 20px' }}>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-3">Mejor Antigüedad · Rango más alto</p>
          <div className="flex items-baseline gap-1.5 mb-1">
            <span className="font-black text-[#15803d]" style={{ fontSize:18, letterSpacing:'-0.01em', lineHeight:1.2 }}>{bestAnt ?? '—'}</span>
          </div>
          <p className="text-[10px] text-slate-400 mt-3 pt-3 border-t border-slate-100">
            {bestAnt && porAnt[bestAnt] != null ? `${porAnt[bestAnt]}/100 pts` : 'Sin datos'}
          </p>
        </div>
      </div>

      {/* ── Row 2: Modelos 360 por período + Tendencia 360 por período ──── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {(() => {
          // Gráfico de barras agrupado: modelo × período
          const MODELOS = ['docencia','abp','posgrado','tecnologado','vinculacion','gestion','investigacion']
          const MODELO_LABELS: Record<string,string> = {
            docencia:'Docencia', abp:'Salud/ABP', posgrado:'Posgrado',
            tecnologado:'Tecnologado', vinculacion:'Vinculación',
            gestion:'Gestión', investigacion:'Investigación',
          }
          const MC = ['#0f5ca8','#b91c1c','#047857','#b45309','#6d28d9','#0e7490','#7c2d12']
          // Recopilar todos los períodos disponibles
          const allPeriodos = Array.from(new Set(
            MODELOS.flatMap(m => (porModeloPeriodo[m] || []).map((d:any) => d.periodo))
          )).sort()

          if (allPeriodos.length > 0) {
            // Una barra por modelo, agrupadas por período
            const traces = MODELOS.map((m, i) => {
              const data = porModeloPeriodo[m] || []
              return {
                type: 'bar' as const,
                name: MODELO_LABELS[m],
                x: data.map((d:any) => d.periodo),
                y: data.map((d:any) => +(d.promedio ?? 0)),
                marker: { color: MC[i], opacity: 0.88 },
                text: data.map((d:any) => d.promedio ? (+d.promedio).toFixed(1) : ''),
                textposition: 'outside' as const,
                textfont: { family:'Inter', size:8, color: MC[i] },
                hovertemplate: `<b>${MODELO_LABELS[m]}</b><br>%{x}<br>%{y:.1f}/100<extra></extra>`,
              }
            })
            const layout = {
              autosize:true, paper_bgcolor:'white', plot_bgcolor:'white',
              barmode: 'group' as const,
              font:{ family:'Inter', size:9, color:'#64748b' },
              margin:{ t:28, b:70, l:46, r:16 },
              xaxis:{
                type:'category' as const,
                tickfont:{ family:'Inter', size:10, color:'#1e293b' },
                showgrid:false, zeroline:false, showline:true, linecolor:'#e2e8f0',
              },
              yaxis:{ gridcolor:'#f0f4f8', range:[0,110], tickfont:{ family:'Inter', size:9, color:'#94a3b8' }, showgrid:true, zeroline:false, nticks:6 },
              showlegend:true,
              legend:{ orientation:'h' as const, y:-0.25, font:{ size:8, family:'Inter' } },
              shapes:[{ type:'line', x0:0, x1:1, xref:'paper', y0:90, y1:90, line:{ color:'#10b981', width:1.5, dash:'dot' } }],
              annotations:[{ x:1, y:90, xref:'paper', yref:'y', text:'Meta 90', showarrow:false, font:{ size:9, color:'#10b981', family:'Inter' }, xanchor:'right', yanchor:'bottom', yshift:4 }],
            }
            return (
              <ChartCard title="Puntaje por Modelo 360" sub="Por período — Modelos MECDI">
                <Plot data={traces} layout={layout} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'300px'}} />
              </ChartCard>
            )
          }
          // Fallback: barras simples agregadas
          const filteredModelo = Object.entries(porModelo).filter(([k]) => k !== 'administrativo')
          const mL = filteredModelo.map(([m]) => MODELO_LABELS[m] || m.charAt(0).toUpperCase()+m.slice(1))
          const mV = filteredModelo.map(([,v]:any) => +(v.promedio??0))
          const ch = excel3DBar(mL, mV, MC.slice(0,mL.length), { tickAngle: mL.length>5?-28:0, marginB: mL.length>5?85:55 })
          return (
            <ChartCard title="Puntaje por Modelo 360" sub="Modelos MECDI">
              <Plot data={ch.data} layout={ch.layout} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'280px'}} />
            </ChartCard>
          )
        })()}

        {(() => {
          const src = tendPeriodos360.length > 0 ? tendPeriodos360 : tend360.map((t:any)=>({...t, periodo: String(t.anio)}))
          const vals = src.map((t:any) => +(t.promedio ?? 0))
          const labels = src.map((t:any) => t.periodo ?? String(t.anio))
          const yMin = Math.max(0, Math.floor(Math.min(...vals)) - 4)
          const yMax = Math.ceil(Math.max(...vals)) + 5
          return (
            <ChartCard title="Tendencia 360 / MECDI" sub="Evolución por período">
              <Plot data={[{
                type:'scatter', mode:'lines+markers+text',
                x: labels,
                y: vals,
                line:{ color:'#0f5ca8', width:3, shape:'spline', smoothing:0.6 },
                marker:{ size:10, color:'white', symbol:'circle', line:{ color:'#0f5ca8', width:2.5 } },
                text: vals.map((v:number)=>v.toFixed(1)),
                textposition:'top center',
                textfont:{ family:'Inter', size:10, color:'#0f5ca8' },
                hovertemplate:'<b>360/MECDI</b> · %{x}<br>%{y:.2f} / 100<extra></extra>',
              }]} layout={{
                autosize:true, paper_bgcolor:'white', plot_bgcolor:'white',
                font:{ family:'Inter', size:9, color:'#64748b' },
                margin:{ t:28, b:55, l:46, r:16 },
                xaxis:{ type:'category' as const, categoryorder:'array' as const, categoryarray: labels,
                  tickfont:{ family:'Inter', size:11, color:'#1e293b' }, showgrid:false, zeroline:false, showline:true, linecolor:'#e2e8f0' },
                yaxis:{ gridcolor:'#f0f4f8', range:[yMin, yMax], tickfont:{ family:'Inter', size:9, color:'#94a3b8' }, showgrid:true, zeroline:false, nticks:6 },
                showlegend:false,
                shapes:[{ type:'line', x0:0, x1:1, xref:'paper', y0:90, y1:90, line:{ color:'#10b981', width:1.5, dash:'dot' } }],
                annotations:[{ x:1, y:90, xref:'paper', yref:'y', text:'Meta 90', showarrow:false, font:{ size:9, color:'#10b981', family:'Inter' }, xanchor:'right', yanchor:'bottom', yshift:4 }],
              }} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'300px'}} />
            </ChartCard>
          )
        })()}
      </div>

      {/* ── Row 3: Tendencia MEIPA por período + Estadísticas ────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {(() => {
          const src = tendPeriodosMeipa.length > 0 ? tendPeriodosMeipa : tendMeipa.map((t:any)=>({...t, periodo: String(t.anio)}))
          const vals = src.map((t:any) => +(t.promedio ?? 0))
          const labels = src.map((t:any) => t.periodo ?? String(t.anio))
          const yMin = Math.max(0, Math.floor(Math.min(...vals)) - 4)
          const yMax = Math.ceil(Math.max(...vals)) + 5
          return (
            <ChartCard title="Tendencia MEIPA" sub="Evolución por período">
              <Plot data={[{
                type:'scatter', mode:'lines+markers+text',
                x: labels,
                y: vals,
                line:{ color:'#6d28d9', width:3, shape:'spline', smoothing:0.6, dash:'dash' },
                marker:{ size:10, color:'white', symbol:'diamond', line:{ color:'#6d28d9', width:2.5 } },
                text: vals.map((v:number)=>v.toFixed(1)),
                textposition:'top center',
                textfont:{ family:'Inter', size:10, color:'#6d28d9' },
                hovertemplate:'<b>MEIPA</b> · %{x}<br>%{y:.2f} / 100<extra></extra>',
              }]} layout={{
                autosize:true, paper_bgcolor:'white', plot_bgcolor:'white',
                font:{ family:'Inter', size:9, color:'#64748b' },
                margin:{ t:28, b:55, l:46, r:16 },
                xaxis:{ type:'category' as const, categoryorder:'array' as const, categoryarray: labels,
                  tickfont:{ family:'Inter', size:11, color:'#1e293b' }, showgrid:false, zeroline:false, showline:true, linecolor:'#e2e8f0' },
                yaxis:{ gridcolor:'#f0f4f8', range:[yMin, yMax], tickfont:{ family:'Inter', size:9, color:'#94a3b8' }, showgrid:true, zeroline:false, nticks:6 },
                showlegend:false,
                shapes:[{ type:'line', x0:0, x1:1, xref:'paper', y0:90, y1:90, line:{ color:'#10b981', width:1.5, dash:'dot' } }],
                annotations:[{ x:1, y:90, xref:'paper', yref:'y', text:'Meta 90', showarrow:false, font:{ size:9, color:'#10b981', family:'Inter' }, xanchor:'right', yanchor:'bottom', yshift:4 }],
              }} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'300px'}} />
            </ChartCard>
          )
        })()}

        {comparativo?.estadisticas && (() => {
          const est = comparativo.estadisticas as any
          const StatRow = ({ label, value, sub }: { label:string; value:any; sub?:string }) => (
            <div className="flex items-center justify-between py-2 border-b border-slate-50 last:border-0">
              <span className="text-[11px] text-slate-500 font-medium">{label}</span>
              <div className="text-right">
                <span className="text-[13px] font-black text-slate-800 tabular-nums">{value}</span>
                {sub && <span className="ml-1 text-[9px] text-slate-400">{sub}</span>}
              </div>
            </div>
          )
          const SysCard = ({ title, color, d }: { title:string; color:string; d:any }) => !d ? null : (
            <div className="border border-slate-100 rounded-lg p-4" style={{ borderTop:`3px solid ${color}` }}>
              <p className="text-[10px] font-black uppercase tracking-widest mb-3" style={{ color }}>{title}</p>
              <StatRow label="Media" value={d.media} sub="/ 100" />
              <StatRow label="Mediana" value={d.mediana} sub="/ 100" />
              <StatRow label="Moda (rango)" value={d.moda_rango} sub={`· ${d.moda_freq} docs`} />
              <StatRow label="Varianza" value={d.varianza} />
              <StatRow label="Desv. Estándar" value={d.desv_std} />
              <StatRow label="Mínimo" value={d.min} sub="/ 100" />
              <StatRow label="Máximo" value={d.max} sub="/ 100" />
              <StatRow label="N evaluados" value={d.n} />
            </div>
          )
          return (
            <div className="bg-white border border-slate-200 overflow-hidden"
              style={{ borderRadius:6, boxShadow:'0 1px 3px rgba(0,0,0,0.06)' }}>
              <div className="px-5 py-3.5 border-b border-slate-100">
                <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em]">Estadísticas ·</span>
                <span className="ml-1 text-[13px] font-bold text-slate-700">Media, Moda y Varianza</span>
              </div>
              <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
                <SysCard title="MEIPA" color="#6d28d9" d={est.meipa} />
                <SysCard title="360 / MECDI" color="#0f5ca8" d={est['360']} />
              </div>
            </div>
          )
        })()}
      </div>

      {/* ── Row 3: Facultades ─────────────────────────────────────────────── */}
      {porFacultad.length > 0 && (() => {
        const fL = porFacultad.map((f:any)=>f.facultad)
        const fV = porFacultad.map((f:any)=>+(f.promedio||0))
        const fC = fV.map(v=>v>=90?'#047857':v>=75?'#0f5ca8':v>=60?'#b45309':'#b91c1c')
        const ch = excel3DBar(fL, fV, fC, { maxY:108, tickAngle:-35, marginB:115 })
        return (
          <ChartCard title="Ranking de Unidades Académicas — Puntaje Promedio Global" sub="Facultades / Carreras">
            <Plot data={ch.data} layout={ch.layout} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'360px'}} />
          </ChartCard>
        )
      })()}

      {/* ── Row 4: Género | Edad | Antigüedad por período ─────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Género por período */}
        {generoPorPeriodo.length > 0 && (() => {
          const periodos = generoPorPeriodo.map((d:any) => d.periodo)
          const generos = ['Mujer','Hombre']
          const traces = generos.map(g => ({
            type: 'bar' as const,
            name: g,
            x: periodos,
            y: generoPorPeriodo.map((d:any) => d[g] ?? null),
            marker: { color: GENDER_COLORS[g] || '#94a3b8', opacity: 0.88 },
            text: generoPorPeriodo.map((d:any) => d[g] ? (+d[g]).toFixed(1) : ''),
            textposition: 'outside' as const,
            textfont: { family:'Inter', size:8 },
            hovertemplate: `<b>${g}</b><br>%{x}<br>%{y:.1f}/100<extra></extra>`,
          }))
          const yVals = generoPorPeriodo.flatMap((d:any) => generos.map(g => d[g] ?? 0)).filter(Boolean)
          const yMin = Math.max(0, Math.floor(Math.min(...yVals)) - 5)
          return (
            <ChartCard title="Desempeño por Género" sub="Por período">
              <div className="flex justify-center gap-6 mb-2">
                {gKeys.map(k=>(
                  <div key={k} className="text-center">
                    <div className="text-xl font-black" style={{color:GENDER_COLORS[k]||'#94a3b8'}}>{porGenero[k]}</div>
                    <div className="text-[9px] font-bold text-slate-500">{k}</div>
                    {bestGenero===k&&<span className="text-[7px] font-black px-1 py-0.5 rounded" style={{background:`${GENDER_COLORS[k]}20`,color:GENDER_COLORS[k]}}>MEJOR</span>}
                  </div>
                ))}
              </div>
              <Plot data={traces} layout={{
                autosize:true, paper_bgcolor:'white', plot_bgcolor:'white',
                barmode:'group' as const,
                font:{ family:'Inter', size:9 },
                margin:{ t:10, b:55, l:40, r:10 },
                xaxis:{ type:'category' as const, tickfont:{ size:9, color:'#1e293b' }, showgrid:false, zeroline:false },
                yaxis:{ gridcolor:'#f0f4f8', range:[yMin, 105], tickfont:{ size:8, color:'#94a3b8' }, showgrid:true, zeroline:false },
                legend:{ orientation:'h' as const, y:-0.22, font:{ size:8 } },
                showlegend:true,
                shapes:[{ type:'line', x0:0, x1:1, xref:'paper', y0:90, y1:90, line:{ color:'#10b981', width:1, dash:'dot' } }],
              }} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'230px'}} />
            </ChartCard>
          )
        })()}

        {/* Edad por período */}
        {edadPorPeriodo.length > 0 && (() => {
          const periodos = edadPorPeriodo.map((d:any) => d.periodo)
          const EDAD_COLORS = ['#0f5ca8','#b45309','#047857','#6d28d9']
          const traces = AGE_BRACKETS.map((b, i) => ({
            type: 'bar' as const,
            name: b,
            x: periodos,
            y: edadPorPeriodo.map((d:any) => d[b] ?? null),
            marker: { color: EDAD_COLORS[i], opacity: 0.85 },
            text: edadPorPeriodo.map((d:any) => d[b] ? (+d[b]).toFixed(1) : ''),
            textposition: 'outside' as const,
            textfont: { family:'Inter', size:7 },
            hovertemplate: `<b>${b}</b><br>%{x}<br>%{y:.1f}/100<extra></extra>`,
          }))
          const yVals = edadPorPeriodo.flatMap((d:any) => AGE_BRACKETS.map(b => d[b] ?? 0)).filter(Boolean)
          const yMin = Math.max(0, Math.floor(Math.min(...yVals)) - 5)
          return (
            <ChartCard title="Desempeño por Rango de Edad" sub="Por período">
              {bestEdad&&<p className="text-[8px] font-black mb-1 px-1" style={{color:'#b45309'}}>Mejor: <span className="text-slate-700">{bestEdad}</span> · {porEdad[bestEdad]}/100</p>}
              <Plot data={traces} layout={{
                autosize:true, paper_bgcolor:'white', plot_bgcolor:'white',
                barmode:'group' as const,
                font:{ family:'Inter', size:9 },
                margin:{ t:10, b:65, l:40, r:10 },
                xaxis:{ type:'category' as const, tickfont:{ size:9, color:'#1e293b' }, showgrid:false, zeroline:false },
                yaxis:{ gridcolor:'#f0f4f8', range:[yMin, 105], tickfont:{ size:8, color:'#94a3b8' }, showgrid:true, zeroline:false },
                legend:{ orientation:'h' as const, y:-0.28, font:{ size:7 } },
                showlegend:true,
                shapes:[{ type:'line', x0:0, x1:1, xref:'paper', y0:90, y1:90, line:{ color:'#10b981', width:1, dash:'dot' } }],
              }} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'250px'}} />
            </ChartCard>
          )
        })()}

        {/* Antigüedad por período */}
        {antiguedadPorPeriodo.length > 0 && (() => {
          const periodos = antiguedadPorPeriodo.map((d:any) => d.periodo)
          const ANT_COLORS = ['#0e7490','#b91c1c','#7c3aed','#047857']
          const traces = ANTIG_BRACKETS.map((b, i) => ({
            type: 'bar' as const,
            name: b,
            x: periodos,
            y: antiguedadPorPeriodo.map((d:any) => d[b] ?? null),
            marker: { color: ANT_COLORS[i], opacity: 0.85 },
            text: antiguedadPorPeriodo.map((d:any) => d[b] ? (+d[b]).toFixed(1) : ''),
            textposition: 'outside' as const,
            textfont: { family:'Inter', size:7 },
            hovertemplate: `<b>${b}</b><br>%{x}<br>%{y:.1f}/100<extra></extra>`,
          }))
          const yVals = antiguedadPorPeriodo.flatMap((d:any) => ANTIG_BRACKETS.map(b => d[b] ?? 0)).filter(Boolean)
          const yMin = Math.max(0, Math.floor(Math.min(...yVals)) - 5)
          return (
            <ChartCard title="Desempeño por Antigüedad" sub="Por período">
              {bestAnt&&<p className="text-[8px] font-black mb-1 px-1" style={{color:'#047857'}}>Mejor: <span className="text-slate-700">{bestAnt}</span> · {porAnt[bestAnt]}/100</p>}
              <Plot data={traces} layout={{
                autosize:true, paper_bgcolor:'white', plot_bgcolor:'white',
                barmode:'group' as const,
                font:{ family:'Inter', size:9 },
                margin:{ t:10, b:65, l:40, r:10 },
                xaxis:{ type:'category' as const, tickfont:{ size:9, color:'#1e293b' }, showgrid:false, zeroline:false },
                yaxis:{ gridcolor:'#f0f4f8', range:[yMin, 105], tickfont:{ size:8, color:'#94a3b8' }, showgrid:true, zeroline:false },
                legend:{ orientation:'h' as const, y:-0.28, font:{ size:7 } },
                showlegend:true,
                shapes:[{ type:'line', x0:0, x1:1, xref:'paper', y0:90, y1:90, line:{ color:'#10b981', width:1, dash:'dot' } }],
              }} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'250px'}} />
            </ChartCard>
          )
        })()}
      </div>

      {/* ── Row 5: Género × Edad/Antigüedad cross-analysis ────────────────── */}
      {(Object.keys(generoEdad).length > 0 || Object.keys(generoAnt).length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {Object.keys(generoEdad).length > 0 && (() => {
            const sE = Object.entries(generoEdad).map(([gen,br])=>({name:gen,color:GENDER_COLORS[gen]||'#64748b',values:AGE_BRACKETS.map(b=>br[b]??null)}))
            const ch = excel3DGrouped(AGE_BRACKETS, sE)
            return (
              <ChartCard title="Mujer vs Hombre — Por Rango de Edad" sub="Análisis cruzado">
                <Plot data={ch.data} layout={ch.layout} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'280px'}} />
              </ChartCard>
            )
          })()}
          {Object.keys(generoAnt).length > 0 && (() => {
            const sA = Object.entries(generoAnt).map(([gen,br])=>({name:gen,color:GENDER_COLORS[gen]||'#64748b',values:ANTIG_BRACKETS.map(b=>br[b]??null)}))
            const ch = excel3DGrouped(ANTIG_BRACKETS, sA)
            return (
              <ChartCard title="Mujer vs Hombre — Por Antigüedad" sub="Análisis cruzado">
                <Plot data={ch.data} layout={ch.layout} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'280px'}} />
              </ChartCard>
            )
          })()}
        </div>
      )}

    </div>
  )
}

// ── Mejores y Peores panel ────────────────────────────────────────────────────
const CATEGORIA_ICONS: Record<string, any> = {
  'Pregrado':      GraduationCap,
  'Salud / ABP':   Heart,
  'Vinculación':   Link2,
  'Investigación': Microscope,
  'Gestión':       Briefcase,
}
const CATEGORIA_COLORS: Record<string, string> = {
  'Pregrado':      '#0056b3',
  'Salud / ABP':   '#dc2626',
  'Vinculación':   '#059669',
  'Investigación': '#7c3aed',
  'Gestión':       '#d97706',
}

function MejoresPeoresPanel({ mejoresPeores }: { mejoresPeores: Record<string, any> }) {
  const cats = Object.keys(mejoresPeores || {})
  const [active, setActive] = useState(cats[0] || '')
  if (!cats.length) return null

  const data = mejoresPeores[active] || { mejores: [], peores: [], total: 0 }
  const color = CATEGORIA_COLORS[active] || '#0056b3'
  const Icon  = CATEGORIA_ICONS[active] || GraduationCap

  const nivelColor = (n: string) => ({
    'Excelente': { bg:'#ecfdf5', text:'#059669', border:'#a7f3d0' },
    'Bueno':     { bg:'#eff6ff', text:'#0056b3', border:'#bfdbfe' },
    'Regular':   { bg:'#fef3c7', text:'#d97706', border:'#fde68a' },
    'Deficiente':{ bg:'#fef2f2', text:'#dc2626', border:'#fecaca' },
  }[n] || { bg:'#f8fafc', text:'#64748b', border:'#e2e8f0' })

  const TeacherRow = ({ doc, rank, type }: { doc: any; rank: number; type: 'best'|'worst' }) => {
    const nc = nivelColor(doc.nivel)
    const isBest = type === 'best'
    return (
      <div className="flex items-center gap-3 py-2.5 border-b border-slate-50 last:border-0">
        <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-black"
          style={{ background: isBest ? `${color}15` : '#fef2f2', color: isBest ? color : '#dc2626' }}>
          {rank}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-bold text-slate-700 truncate uppercase leading-tight">{doc.nombre}</p>
          <p className="text-[9px] text-slate-400 font-medium truncate mt-0.5">{doc.facultad || '—'}</p>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-sm font-black tabular-nums" style={{ color: isBest ? color : '#dc2626' }}>{doc.puntaje}</span>
          <span className="text-[9px] text-slate-400">/100</span>
          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded border"
            style={{ background: nc.bg, color: nc.text, borderColor: nc.border }}>
            {doc.nivel}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white border border-slate-200 overflow-hidden mb-6"
      style={{ borderRadius: 6, boxShadow:'0 1px 3px rgba(0,0,0,0.06)', borderTop:`3px solid ${color}` }}>

      {/* Header */}
      <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon size={14} style={{ color }} />
          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em]">Ranking ·</span>
          <h3 className="text-[13px] font-bold text-slate-700">Mejores y Peores Docentes por Área</h3>
        </div>
        <span className="text-[9px] font-bold px-2 py-1 rounded border"
          style={{ color, background:`${color}08`, borderColor:`${color}25` }}>
          {data.total} evaluados
        </span>
      </div>

      {/* Category tabs */}
      <div className="flex overflow-x-auto border-b border-slate-100 px-4 gap-1 pt-2">
        {cats.map(cat => {
          const CatIcon = CATEGORIA_ICONS[cat] || GraduationCap
          const catColor = CATEGORIA_COLORS[cat] || '#0056b3'
          const isActive = active === cat
          return (
            <button key={cat} onClick={() => setActive(cat)}
              className="flex items-center gap-1.5 px-3 py-2 text-[10px] font-bold whitespace-nowrap rounded-t transition-all flex-shrink-0"
              style={{
                color: isActive ? catColor : '#94a3b8',
                background: isActive ? `${catColor}10` : 'transparent',
                borderBottom: isActive ? `2px solid ${catColor}` : '2px solid transparent',
              }}>
              <CatIcon size={11} />
              {cat}
              <span className="ml-1 text-[8px] font-black px-1 py-0.5 rounded"
                style={{ background: isActive ? `${catColor}20` : '#f1f5f9', color: isActive ? catColor : '#94a3b8' }}>
                {(mejoresPeores[cat]?.total || 0)}
              </span>
            </button>
          )
        })}
      </div>

      {/* Content: two columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">

        {/* Mejores */}
        <div className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full" style={{ background: color }} />
            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">
              Top 5 — Mejor Desempeño
            </p>
          </div>
          {data.mejores.length > 0 ? (
            data.mejores.map((doc: any, i: number) => (
              <TeacherRow key={i} doc={doc} rank={i + 1} type="best" />
            ))
          ) : (
            <p className="text-xs text-slate-400 font-medium py-4 text-center">Sin datos</p>
          )}
        </div>

        {/* Peores */}
        <div className="p-5">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full bg-red-400" />
            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">
              Bottom 5 — Menor Desempeño
            </p>
          </div>
          {data.peores.length > 0 ? (
            data.peores.map((doc: any, i: number) => (
              <TeacherRow key={i} doc={doc} rank={i + 1} type="worst" />
            ))
          ) : (
            <p className="text-xs text-slate-400 font-medium py-4 text-center">Sin datos</p>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Variables Detalle Panel ───────────────────────────────────────────────────
const VD_360_TABS = [
  { key: '360_docencia',    label: 'Docencia',       icon: GraduationCap, color: '#0056b3' },
  { key: '360_abp',         label: 'Salud / ABP',    icon: Heart,         color: '#dc2626' },
  { key: '360_vinculacion', label: 'Vinculación',    icon: Link2,         color: '#059669' },
  { key: '360_investigacion',label:'Investigación',  icon: Microscope,    color: '#7c3aed' },
  { key: '360_gestion',     label: 'Gestión',        icon: Briefcase,     color: '#d97706' },
]

function VariablesDetallePanel({
  title, accentColor, tabs, varData,
}: {
  title: string; accentColor: string;
  tabs: { key: string; label: string; icon: any; color: string }[];
  varData: Record<string, any[]>;
}) {
  const [activeTab, setActiveTab] = useState(tabs[0]?.key || '')
  const [activeComp, setActiveComp] = useState<number>(0)
  const rows: any[] = varData[activeTab] || []
  const tabCfg = tabs.find(t => t.key === activeTab) || tabs[0]
  const color = tabCfg?.color || accentColor
  const comp = rows[activeComp] || null

  const onChange = (key: string) => { setActiveTab(key); setActiveComp(0) }

  const TeacherMini = ({ doc, rank, type }: { doc: any; rank: number; type: 'best' | 'worst' }) => {
    const isBest = type === 'best'
    return (
      <div className="flex items-center gap-2 py-2 border-b border-slate-50 last:border-0">
        <div className="w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center text-[9px] font-black"
          style={{ background: isBest ? `${color}15` : '#fef2f2', color: isBest ? color : '#dc2626' }}>
          {rank}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[10px] font-bold text-slate-700 truncate uppercase">{doc.nombre}</p>
          <p className="text-[9px] text-slate-400">{doc.cedula}</p>
        </div>
        <div className="flex-shrink-0 text-right">
          <p className="text-[11px] font-black tabular-nums" style={{ color: isBest ? color : '#dc2626' }}>
            {doc.comp_pct}%
          </p>
          <p className="text-[8px] text-slate-400">tot: {doc.puntaje}/100</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white border border-slate-200 overflow-hidden mb-6"
      style={{ borderRadius: 6, boxShadow: '0 1px 3px rgba(0,0,0,0.06)', borderTop: `3px solid ${accentColor}` }}>

      {/* Header */}
      <div className="px-5 py-3.5 border-b border-slate-100">
        <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em]">Variables ·</span>
        <span className="ml-1 text-[13px] font-bold text-slate-700">{title}</span>
      </div>

      {/* Model tabs */}
      {tabs.length > 1 && (
        <div className="flex overflow-x-auto border-b border-slate-100 px-4 gap-1 pt-2">
          {tabs.map(t => {
            const TIcon = t.icon
            const isA = activeTab === t.key
            const hasData = (varData[t.key] || []).length > 0
            if (!hasData) return null
            return (
              <button key={t.key} onClick={() => onChange(t.key)}
                className="flex items-center gap-1.5 px-3 py-2 text-[10px] font-bold whitespace-nowrap rounded-t flex-shrink-0 transition-all"
                style={{
                  color: isA ? t.color : '#94a3b8',
                  background: isA ? `${t.color}10` : 'transparent',
                  borderBottom: isA ? `2px solid ${t.color}` : '2px solid transparent',
                }}>
                <TIcon size={11} />{t.label}
              </button>
            )
          })}
        </div>
      )}

      {/* Body: component list + teacher detail */}
      {rows.length === 0 ? (
        <p className="text-xs text-slate-400 text-center py-8">Sin datos para este modelo</p>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-100">

          {/* Left: component ranking */}
          <div className="p-5">
            <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-3">
              Componentes — Promedio General
            </p>
            <div className="space-y-2">
              {rows.map((r: any, i: number) => (
                <button key={r.key} onClick={() => setActiveComp(i)}
                  className="w-full text-left group"
                  style={{ outline: 'none' }}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-bold text-slate-600 group-hover:text-slate-900 truncate pr-2"
                      style={{ color: activeComp === i ? color : undefined }}>
                      {r.label}
                    </span>
                    <span className="text-[10px] font-black tabular-nums flex-shrink-0"
                      style={{ color: activeComp === i ? color : '#64748b' }}>
                      {r.avg_pct}%
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${r.avg_pct}%`,
                        background: activeComp === i
                          ? color
                          : r.avg_pct >= 90 ? '#059669' : r.avg_pct >= 75 ? '#0056b3' : r.avg_pct >= 60 ? '#d97706' : '#dc2626',
                      }} />
                  </div>
                  <p className="text-[8px] text-slate-400 mt-0.5">{r.n} registros</p>
                </button>
              ))}
            </div>
          </div>

          {/* Right: top/bottom for selected component */}
          {comp && (
            <div className="p-5">
              <p className="text-[9px] font-black uppercase tracking-widest mb-1" style={{ color }}>
                {comp.label}
              </p>
              <p className="text-[8px] text-slate-400 mb-4">
                Promedio: <strong>{comp.avg_pct}%</strong> · {comp.n} evaluaciones
              </p>

              {comp.top5?.length > 0 && (
                <>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-2 h-2 rounded-full" style={{ background: color }} />
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Mayor Puntaje</p>
                  </div>
                  {comp.top5.map((doc: any, i: number) => (
                    <TeacherMini key={i} doc={doc} rank={i + 1} type="best" />
                  ))}
                </>
              )}

              {comp.bot5?.length > 0 && (
                <>
                  <div className="flex items-center gap-2 mt-4 mb-2">
                    <div className="w-2 h-2 rounded-full bg-red-400" />
                    <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Menor Puntaje</p>
                  </div>
                  {comp.bot5.map((doc: any, i: number) => (
                    <TeacherMini key={i} doc={doc} rank={i + 1} type="worst" />
                  ))}
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Todos los Docentes Panel ──────────────────────────────────────────────────
const MODELO_COLOR: Record<string, string> = {
  docencia:'#0056b3', abp:'#dc2626', vinculacion:'#059669',
  investigacion:'#7c3aed', gestion:'#d97706', tecnologado:'#0891b2',
  posgrado:'#8b5cf6', administrativo:'#0f766e',
}
const SISTEMA_COLOR: Record<string, string> = { meipa:'#6d28d9', '360':'#0f5ca8' }

function TodosDocentesPanel({ docentes, context }: { docentes: any[]; context?: { modelo: string; sistema: string; label: string } }) {
  const [search, setSearch]           = useState('')
  const [filterSis, setFilterSis]     = useState('todos')
  const [filterMod, setFilterMod]     = useState('todos')
  const [sortBy, setSortBy]           = useState<'puntaje'|'nombre'>('puntaje')
  const [expanded, setExpanded]       = useState<string | null>(null)
  const [page, setPage]               = useState(1)
  const [competencias, setCompetencias] = useState<Record<string, any>>({})
  const [loadingComp, setLoadingComp]   = useState<string | null>(null)
  const PAGE = 40

  const handleExpand = useCallback(async (rowKey: string, cedula: string) => {
    if (expanded === rowKey) { setExpanded(null); return }
    setExpanded(rowKey)
    if (cedula && !competencias[cedula]) {
      setLoadingComp(cedula)
      try {
        const res = await api.getCompetenciasDocente(cedula)
        setCompetencias(prev => ({ ...prev, [cedula]: res.data }))
      } catch { /* sin datos */ }
      finally { setLoadingComp(null) }
    }
  }, [expanded, competencias])

  const modelos = Array.from(new Set(docentes.map(d => d.modelo))).sort()

  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase()
    return docentes
      .filter(d => {
        if (!context && filterSis !== 'todos' && d.sistema !== filterSis) return false
        if (!context && filterMod !== 'todos' && d.modelo !== filterMod) return false
        if (q && !d.nombre?.toLowerCase().includes(q) && !d.cedula?.includes(q) && !d.facultad?.toLowerCase().includes(q)) return false
        return true
      })
      .sort((a, b) => sortBy === 'puntaje' ? b.puntaje - a.puntaje : a.nombre.localeCompare(b.nombre))
  }, [docentes, search, filterSis, filterMod, sortBy, context])

  const total   = filtered.length
  const visible = filtered.slice(0, page * PAGE)
  const hasMore = visible.length < total

  const nivelStyle = (n: string) => ({
    'Excelente':  { bg:'#ecfdf5', c:'#059669', bd:'#a7f3d0' },
    'Bueno':      { bg:'#eff6ff', c:'#0056b3', bd:'#bfdbfe' },
    'Regular':    { bg:'#fef3c7', c:'#d97706', bd:'#fde68a' },
    'Deficiente': { bg:'#fef2f2', c:'#dc2626', bd:'#fecaca' },
  }[n] || { bg:'#f8fafc', c:'#64748b', bd:'#e2e8f0' })

  const pctColor = (p: number) => p >= 90 ? '#059669' : p >= 75 ? '#0056b3' : p >= 60 ? '#d97706' : '#dc2626'

  return (
    <div className="bg-white border border-slate-200 overflow-hidden mb-6"
      style={{ borderRadius:6, boxShadow:'0 1px 3px rgba(0,0,0,0.06)', borderTop:'3px solid #334155' }}>

      {/* Header */}
      <div className="px-5 py-3.5 border-b border-slate-100 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Users size={14} className="text-slate-500 flex-shrink-0" />
          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em]">Directorio ·</span>
          <h3 className="text-[13px] font-bold text-slate-700">
            {context ? `Docentes — ${context.label}` : 'Todos los Docentes — Desglose por Variables'}
          </h3>
        </div>
        <span className="text-[9px] font-bold px-2 py-1 rounded border border-slate-200 bg-slate-50 text-slate-500">
          {total} de {docentes.length} docentes
        </span>
      </div>

      {/* Filters */}
      <div className="px-5 py-3 border-b border-slate-100 flex flex-wrap gap-2 items-center bg-slate-50/60">
        {/* Search */}
        <div className="relative flex-1 min-w-[180px]">
          <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text" placeholder="Buscar por nombre, cédula o facultad…"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
            className="w-full pl-8 pr-3 py-1.5 text-[11px] border border-slate-200 rounded-lg bg-white outline-none focus:border-slate-400"
          />
        </div>
        {/* Sistema — solo en vista general */}
        {!context && (
          <select value={filterSis} onChange={e => { setFilterSis(e.target.value); setPage(1) }}
            className="text-[11px] font-bold border border-slate-200 rounded-lg px-3 py-1.5 bg-white outline-none text-slate-600">
            <option value="todos">Todos los sistemas</option>
            <option value="360">360 / MECDI</option>
            <option value="meipa">MEIPA</option>
          </select>
        )}
        {/* Modelo — solo en vista general */}
        {!context && (
          <select value={filterMod} onChange={e => { setFilterMod(e.target.value); setPage(1) }}
            className="text-[11px] font-bold border border-slate-200 rounded-lg px-3 py-1.5 bg-white outline-none text-slate-600">
            <option value="todos">Todos los modelos</option>
            {modelos.map(m => <option key={m} value={m}>{m.charAt(0).toUpperCase()+m.slice(1)}</option>)}
          </select>
        )}
        {/* Sort */}
        <select value={sortBy} onChange={e => setSortBy(e.target.value as any)}
          className="text-[11px] font-bold border border-slate-200 rounded-lg px-3 py-1.5 bg-white outline-none text-slate-600">
          <option value="puntaje">Ordenar: Mayor puntaje</option>
          <option value="nombre">Ordenar: Nombre A–Z</option>
        </select>
      </div>

      {/* Table header — ocultar Sistema/Modelo en vista de modelo específico */}
      {context ? (
        <div className="hidden lg:grid px-5 py-2 border-b border-slate-100 bg-slate-50/40 text-[9px] font-black uppercase tracking-widest text-slate-400"
          style={{ gridTemplateColumns:'2.5rem 1fr 5rem 6rem 1fr' }}>
          <span>#</span><span>Docente</span>
          <span className="text-right">Puntaje</span><span className="text-center">Nivel</span>
          <span>Variables</span>
        </div>
      ) : (
        <div className="hidden lg:grid px-5 py-2 border-b border-slate-100 bg-slate-50/40 text-[9px] font-black uppercase tracking-widest text-slate-400"
          style={{ gridTemplateColumns:'2.5rem 1fr 7rem 8rem 5rem 6rem 1fr' }}>
          <span>#</span><span>Docente</span><span>Sistema</span><span>Modelo</span>
          <span className="text-right">Puntaje</span><span className="text-center">Nivel</span>
          <span>Variables</span>
        </div>
      )}

      {/* Rows */}
      <div className="divide-y divide-slate-50">
        {visible.map((d: any, i: number) => {
          const rowKey = `${d.cedula}-${d.sistema}-${d.modelo}`
          const isExp  = expanded === rowKey
          const ns     = nivelStyle(d.nivel)
          const modC   = MODELO_COLOR[d.modelo] || '#64748b'
          const sisC   = SISTEMA_COLOR[d.sistema] || '#64748b'
          const best   = d.componentes?.[0]
          const worst  = d.componentes?.[d.componentes.length - 1]

          return (
            <div key={rowKey}>
              <button
                onClick={() => handleExpand(rowKey, d.cedula)}
                className="w-full text-left hover:bg-slate-50/80 transition-colors"
              >
                {/* Desktop grid */}
                <div className="hidden lg:grid px-5 py-3 items-center gap-2"
                  style={{ gridTemplateColumns: context ? '2.5rem 1fr 5rem 6rem 1fr' : '2.5rem 1fr 7rem 8rem 5rem 6rem 1fr' }}>
                  <span className="text-[11px] font-black text-slate-400 tabular-nums">{i + 1}</span>
                  <div className="min-w-0">
                    <p className="text-[11px] font-bold text-slate-800 truncate uppercase">{d.nombre}</p>
                    <p className="text-[9px] text-slate-400 truncate">{d.cedula} {d.facultad ? `· ${d.facultad}` : ''}</p>
                    {d.fecha_ingreso && (
                      <p className="text-[8px] text-slate-400 mt-0.5">
                        Ingreso: {new Date(d.fecha_ingreso + 'T00:00:00').toLocaleDateString('es-EC', { day:'2-digit', month:'short', year:'numeric' })}
                      </p>
                    )}
                  </div>
                  {/* Sistema y Modelo solo en vista general */}
                  {!context && (
                    <span className="text-[9px] font-black px-2 py-0.5 rounded-full"
                      style={{ background:`${sisC}15`, color:sisC }}>
                      {d.sistema === 'meipa' ? 'MEIPA' : '360/MECDI'}
                    </span>
                  )}
                  {!context && (
                    <span className="text-[9px] font-bold px-2 py-0.5 rounded border"
                      style={{ background:`${modC}10`, color:modC, borderColor:`${modC}30` }}>
                      {d.modelo.charAt(0).toUpperCase()+d.modelo.slice(1)}
                    </span>
                  )}
                  <span className="text-[14px] font-black tabular-nums text-right"
                    style={{ color: pctColor(d.puntaje) }}>{d.puntaje}</span>
                  <span className="text-[9px] font-black px-1.5 py-0.5 rounded text-center border"
                    style={{ background:ns.bg, color:ns.c, borderColor:ns.bd }}>{d.nivel}</span>
                  {/* Mini component bars */}
                  <div className="space-y-0.5 min-w-0">
                    {(d.componentes || []).slice(0, 3).map((c: any, ci: number) => (
                      <div key={ci} className="flex items-center gap-1.5">
                        <span className="text-[8px] text-slate-400 w-28 truncate flex-shrink-0">{c.label}</span>
                        <div className="flex-1 h-1 rounded-full bg-slate-100 overflow-hidden">
                          <div className="h-full rounded-full" style={{ width:`${c.pct}%`, background:pctColor(c.pct) }} />
                        </div>
                        <span className="text-[8px] font-black tabular-nums w-8 text-right flex-shrink-0"
                          style={{ color:pctColor(c.pct) }}>{c.pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Mobile card */}
                <div className="lg:hidden px-4 py-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="text-[11px] font-bold text-slate-800 truncate uppercase">{d.nombre}</p>
                      <p className="text-[9px] text-slate-400 truncate">{d.cedula}</p>
                      <div className="flex gap-1 mt-1">
                        <span className="text-[8px] font-black px-1.5 py-0.5 rounded-full"
                          style={{ background:`${sisC}15`, color:sisC }}>{d.sistema === 'meipa' ? 'MEIPA' : '360'}</span>
                        <span className="text-[8px] font-bold px-1.5 py-0.5 rounded border"
                          style={{ background:`${modC}10`, color:modC, borderColor:`${modC}30` }}>
                          {d.modelo.charAt(0).toUpperCase()+d.modelo.slice(1)}
                        </span>
                      </div>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-[16px] font-black tabular-nums" style={{ color:pctColor(d.puntaje) }}>{d.puntaje}</p>
                      <span className="text-[8px] font-black px-1.5 py-0.5 rounded border"
                        style={{ background:ns.bg, color:ns.c, borderColor:ns.bd }}>{d.nivel}</span>
                    </div>
                  </div>
                </div>
              </button>

              {/* Expanded detail */}
              {isExp && (
                <div className="px-5 pb-5 bg-slate-50/60 border-t border-slate-100">
                  <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest pt-3 mb-2">
                    Componentes del Modelo — {d.modelo.charAt(0).toUpperCase()+d.modelo.slice(1)} · {d.sistema === 'meipa' ? 'MEIPA' : '360/MECDI'}
                  </p>
                  <div className="space-y-2 mb-4">
                    {(d.componentes || []).map((c: any, ci: number) => {
                      const col = pctColor(c.pct)
                      const isBest  = ci === 0
                      const isWorst = ci === (d.componentes.length - 1)
                      return (
                        <div key={ci}>
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] font-bold text-slate-700">{c.label}</span>
                              {isBest  && <span className="text-[8px] font-black px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-600 border border-emerald-200">✦ Mejor</span>}
                              {isWorst && d.componentes.length > 1 && <span className="text-[8px] font-black px-1.5 py-0.5 rounded bg-red-50 text-red-500 border border-red-200">↓ Menor</span>}
                            </div>
                            <span className="text-[12px] font-black tabular-nums" style={{ color:col }}>{c.pct}%</span>
                          </div>
                          <div className="h-2 rounded-full bg-slate-200 overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-700"
                              style={{ width:`${c.pct}%`, background:col }} />
                          </div>
                        </div>
                      )
                    })}
                  </div>

                  {loadingComp === d.cedula ? (
                    <div className="flex items-center gap-2 py-3 text-slate-400">
                      <RefreshCw size={11} className="animate-spin" />
                      <span className="text-[10px]">Cargando competencias…</span>
                    </div>
                  ) : (() => {
                    const comp = competencias[d.cedula]
                    if (!comp) return null
                    const all360   = comp['360']   || []
                    const allMeipa = comp['meipa'] || []
                    const grupos360: Record<string, any[]> = {}
                    for (const c of all360) {
                      const gk = `${c.periodo} · ${c.instrumento}`
                      if (!grupos360[gk]) grupos360[gk] = []
                      grupos360[gk].push(c)
                    }
                    const gruposMeipa: Record<string, any[]> = {}
                    for (const c of allMeipa) {
                      if (!gruposMeipa[c.periodo]) gruposMeipa[c.periodo] = []
                      gruposMeipa[c.periodo].push(c)
                    }
                    const hasAny = all360.length > 0 || allMeipa.length > 0
                    if (!hasAny) return (
                      <p className="text-[9px] text-slate-400 italic">Sin datos de competencias por pregunta disponibles.</p>
                    )
                    return (
                      <div>
                        <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-3 border-t border-slate-200 pt-3">
                          Competencias por Pregunta
                        </p>
                        {Object.entries(grupos360).map(([gk, items]) => {
                          const sorted = [...items].sort((a, b) => b.pct - a.pct)
                          return (
                            <div key={gk} className="mb-4">
                              <p className="text-[9px] font-black text-[#0056b3] mb-1.5 uppercase tracking-wider">{gk}</p>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1.5">
                                {sorted.map((c: any, ci: number) => (
                                  <div key={ci} className="flex items-center gap-2">
                                    <span className="text-[9px] text-slate-600 flex-1 min-w-0 truncate">{c.competencia}</span>
                                    <div className="w-16 h-1.5 rounded-full bg-slate-200 overflow-hidden flex-shrink-0">
                                      <div className="h-full rounded-full" style={{ width:`${c.pct}%`, background:pctColor(c.pct) }} />
                                    </div>
                                    <span className="text-[9px] font-black w-8 text-right flex-shrink-0" style={{ color:pctColor(c.pct) }}>{c.pct}%</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )
                        })}
                        {Object.entries(gruposMeipa).map(([periodo, items]) => {
                          const sorted = [...items].sort((a, b) => b.pct - a.pct)
                          return (
                            <div key={periodo} className="mb-4">
                              <p className="text-[9px] font-black text-[#6d28d9] mb-1.5 uppercase tracking-wider">MEIPA · {periodo}</p>
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1.5">
                                {sorted.map((c: any, ci: number) => (
                                  <div key={ci} className="flex items-center gap-2">
                                    <span className="text-[9px] text-slate-600 flex-1 min-w-0 truncate">{c.competencia}</span>
                                    <div className="w-16 h-1.5 rounded-full bg-slate-200 overflow-hidden flex-shrink-0">
                                      <div className="h-full rounded-full" style={{ width:`${c.pct}%`, background:pctColor(c.pct) }} />
                                    </div>
                                    <span className="text-[9px] font-black w-8 text-right flex-shrink-0" style={{ color:pctColor(c.pct) }}>{c.pct}%</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )
                  })()}
                </div>
              )}
            </div>
          )
        })}

        {total === 0 && (
          <p className="text-sm text-slate-400 text-center py-10">No se encontraron docentes con los filtros actuales.</p>
        )}
      </div>

      {/* Load more */}
      {hasMore && (
        <div className="px-5 py-3 border-t border-slate-100 flex items-center justify-between bg-slate-50/40">
          <span className="text-[11px] text-slate-400">Mostrando {visible.length} de {total}</span>
          <button onClick={() => setPage(p => p + 1)}
            className="text-[11px] font-bold text-[#0056b3] hover:underline">
            Cargar {Math.min(PAGE, total - visible.length)} más →
          </button>
        </div>
      )}
    </div>
  )
}

// ── Sidebar item ──────────────────────────────────────────────────────────────
function SidebarItem({ icon, label, active, collapsed, onClick, accentColor, badge }: {
  icon: React.ReactNode; label: string; active: boolean; collapsed: boolean;
  onClick: () => void; accentColor: string; badge?: string;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 text-left transition-all relative"
      style={{
        padding: collapsed ? '9px 10px' : '9px 10px 9px 14px',
        color: active ? '#fff' : 'rgba(255,255,255,0.58)',
        background: active ? 'rgba(255,255,255,0.08)' : 'transparent',
        borderRadius: 4,
        borderLeft: active ? '2px solid rgba(77,166,232,0.9)' : '2px solid transparent',
      }}
    >
      <span className="flex-shrink-0" style={{ opacity: active ? 1 : 0.65 }}>{icon}</span>
      {!collapsed && (
        <>
          <span className="flex-1 truncate" style={{ fontSize: 13, fontWeight: active ? 600 : 500 }}>{label}</span>
          {badge && (
            <span style={{ fontSize: 9, fontWeight: 700, padding:'2px 5px', borderRadius: 3, background:'rgba(255,255,255,0.1)', color:'rgba(255,255,255,0.5)', letterSpacing:'0.04em' }}>
              {badge}
            </span>
          )}
        </>
      )}
    </button>
  )
}

const PERIODO_TO_ANIO: Record<string, number> = {
  '202301': 2023, '202302': 2023, '202401': 2024,
  '202402': 2024, '202501': 2025, '202502': 2025,
}

// ══════════════════════════════════════════════════════════════════════════════
// Main App
// ══════════════════════════════════════════════════════════════════════════════
export default function App() {
  // Sistema selector: 'overview' | 'meipa' | '360' | 'salud'
  const [sistema, setSistema]         = useState<'overview'|'meipa'|'360'|'salud'>('overview')
  const [activeTab, setActiveTab]     = useState('docencia')  // for 360 sub-model
  const [activeAnio, setActiveAnio]   = useState<number | undefined>(undefined)

  const [kpis, setKpis]               = useState<any>(null)
  const [ranking, setRanking]         = useState<any[]>([])
  const [demograficos, setDemograficos] = useState<any>(null)
  const [tendencias, setTendencias]   = useState<any[]>([])
  const [analytics, setAnalytics]     = useState<any>(null)
  const [comparativo, setComparativo]       = useState<any>(null)
  const [todosDocentes, setTodosDocentes]   = useState<any[]>([])
  const [aiAnalysis, setAiAnalysis]         = useState('')
  const [loading, setLoading]               = useState(true)
  const [processing, setProcessing]   = useState(false)
  const [searchTerm, setSearchTerm]   = useState('')
  const [splashVisible, setSplashVisible] = useState(true)

  // ── Períodos v2 ────────────────────────────────────────────────────────────
  const [periodos, setPeriodos]           = useState<any[]>([])
  const [periodoActivo, setPeriodoActivo] = useState<string>('')  // '202502' etc.
  const [pdfLoading, setPdfLoading]       = useState<string | null>(null) // cedula en descarga
  const [splashFading, setSplashFading]   = useState(false)

  useEffect(() => {
    const t1 = setTimeout(() => setSplashFading(true), 1600)
    const t2 = setTimeout(() => setSplashVisible(false), 2400)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [])

  // Cargar períodos al montar
  useEffect(() => {
    api.getPeriodos().then(res => {
      const cargados = res.data.filter((p: any) => p.cargado)
      setPeriodos(res.data)
      if (cargados.length > 0) {
        setPeriodoActivo(cargados[cargados.length - 1].codigo) // último período cargado
      }
    }).catch(() => {})
  }, [])

  const handleDescargarPDF = async (cedula: string) => {
    if (pdfLoading) return
    setPdfLoading(cedula)
    try {
      await api.descargarReportePDF(cedula, periodoActivo || undefined)
    } catch (e) {
      alert('Error al generar el PDF. Intenta de nuevo.')
    } finally {
      setPdfLoading(null)
    }
  }

  // Determine query params from state — activeAnio is the single source of truth for year filter
  const getQueryParams = useCallback(() => {
    if (sistema === 'overview') return { modelo: undefined,  anio: activeAnio, sistemaParam: undefined }
    if (sistema === 'meipa')    return { modelo: 'docencia', anio: activeAnio, sistemaParam: 'meipa'  }
    if (sistema === 'salud')    return { modelo: 'abp',      anio: activeAnio, sistemaParam: '360'    }
    return { modelo: activeTab, anio: activeAnio, sistemaParam: '360' }
  }, [sistema, activeTab, activeAnio])

  const fetchData = useCallback(async () => {
    setLoading(true)
    setKpis(null); setRanking([]); setDemograficos(null)
    setTendencias([]); setAnalytics(null); setComparativo(null); setTodosDocentes([])
    try {
      const { modelo, anio, sistemaParam } = getQueryParams()

      if (sistema === 'overview') {
        const [compRes, todosRes] = await Promise.all([
          api.getComparativo(anio),
          api.getTodosDocentes(anio, undefined, undefined),
        ])
        setComparativo(compRes.data)
        setTodosDocentes(Array.isArray(todosRes.data) ? todosRes.data : [])
      } else {
        const [kpiRes, rankRes, demoRes, tendRes, analyticsRes, todosRes] = await Promise.all([
          api.getKPIs(modelo, anio, sistemaParam),
          api.getRanking(1000, modelo, anio, sistemaParam),
          api.getDemograficos(modelo, anio, sistemaParam),
          api.getTendencias(modelo, sistemaParam),
          api.getAnalytics(sistemaParam, modelo, anio),
          api.getTodosDocentes(anio, modelo, sistemaParam),
        ])
        setKpis(kpiRes.data)
        setRanking(rankRes.data)
        setDemograficos(demoRes.data)
        setTendencias(tendRes.data)
        setAnalytics(analyticsRes.data)
        setTodosDocentes(Array.isArray(todosRes.data) ? todosRes.data : [])
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [sistema, getQueryParams])

  useEffect(() => { fetchData() }, [fetchData])

  const handleSistemaChange = (s: 'overview'|'meipa'|'360'|'salud') => {
    setSistema(s)
    setSearchTerm('')
    setAiAnalysis('')
    if (s === '360') setActiveTab('docencia')
  }

  const handleTabChange = (tab: string) => {
    setActiveTab(tab)
    setSearchTerm('')
    setAiAnalysis('')
  }

  const runETL = async () => {
    try {
      setProcessing(true)
      await fetchData()
    } catch { alert('Error actualizando datos') }
    setProcessing(false)
  }

  const runAnalysisIA = async () => {
    try {
      setAiAnalysis('Generando análisis estratégico…')
      const { modelo, anio, sistemaParam } = getQueryParams()
      const res = await api.getAIAnalysis(modelo, anio, sistemaParam)
      setAiAnalysis(res.data.analysis)
    } catch { setAiAnalysis('Error generando análisis.') }
  }

  const filteredRanking = ranking.filter((doc: any) =>
    (doc.nombre || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (doc.facultad || '').toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Which tab config to use for displays
  const currentTabCfg = sistema === 'meipa'
    ? { id:'meipa', label:'MEIPA — Docencia', icon:UserCheck, color:'#6366f1', desc:'Het.40 · Auto.20 · Coord.20 · Par.20' }
    : sistema === 'salud'
      ? { id:'abp', label:'Salud — Docencia (ABP)', icon:Heart, color:'#dc2626', desc:'Het.Est.50 · Par.20 · CEV.10 · Auto.20' }
      : (TABS_360.find(t => t.id === activeTab) || TABS_360[0])

  const _tabKey = sistema === 'meipa' ? 'meipa' : sistema === 'salud' ? 'abp' : activeTab
  const compLabels = TAB_COMP_LABELS[_tabKey] || TAB_COMP_LABELS['docencia']
  const compKeys   = TAB_COMP_KEYS[_tabKey]   || TAB_COMP_KEYS['docencia']
  const componentes= kpis?.componentes || {}
  const distNivel  = kpis?.distribucion_nivel || {}
  const aniosDisp  = kpis?.anios_disponibles ?? comparativo?.anios_disponibles ?? [2023, 2024, 2025]

  const compValues = compKeys.map(k => {
    const c = componentes[k]
    return c ? c.promedio : 0
  })

  const [sidebarOpen, setSidebarOpen]     = useState(true)
  const [expandedMEIPA, setExpandedMEIPA] = useState(true)
  const [expanded360, setExpanded360]     = useState(true)
  const [expandedSalud, setExpandedSalud] = useState(true)

  const SIDEBAR_W = sidebarOpen ? 268 : 68

  if (loading && !kpis && !comparativo) {
    return (
      <>
        <SplashScreen visible={splashVisible} fading={splashFading} />
        <div className="flex items-center justify-center min-h-screen" style={{ background:'#f5f7fa' }}>
          <div className="flex flex-col items-center gap-5">
            <div className="relative">
              <div className="w-14 h-14 rounded-full border-4 border-slate-200 border-t-[#1a7fc1] animate-spin" />
              <div className="absolute inset-0 flex items-center justify-center">
                <BookOpen size={18} style={{ color:'#1a7fc1' }} />
              </div>
            </div>
            <p className="text-slate-600 font-bold text-sm">Cargando datos…</p>
          </div>
        </div>
      </>
    )
  }

  const SIDEBAR_BG  = '#0f1e38'
  const SIDEBAR_ACT = 'rgba(26,127,193,0.28)'
  const TOPBAR_H    = 60

  return (
    <>
      <SplashScreen visible={splashVisible} fading={splashFading} />
      <div className="flex h-screen overflow-hidden font-sans" style={{ background:'#f5f7fa' }}>

        {/* ── SIDEBAR ──────────────────────────────────────────────────────── */}
        <aside
          className="flex-shrink-0 flex flex-col h-full transition-all duration-300 z-30 relative"
          style={{ width: SIDEBAR_W, background: 'linear-gradient(180deg, #0f1e38 0%, #122444 60%, #0d1c34 100%)', borderRight:'1px solid rgba(255,255,255,0.06)' }}
        >
          {/* Logo */}
          <div
            className="flex items-center gap-3 px-4 border-b"
            style={{ borderColor:'rgba(255,255,255,0.07)', minHeight: 72, background:'rgba(0,0,0,0.18)' }}
          >
            <div className="flex-shrink-0 rounded-xl p-1.5" style={{ background:'rgba(255,255,255,0.96)' }}>
              <img src={LOGO_URL} alt="PUCE" className="object-contain" style={{ height: sidebarOpen ? 40 : 28, width: sidebarOpen ? 40 : 28 }} />
            </div>
            {sidebarOpen && (
              <div className="leading-tight min-w-0">
                <p className="text-white font-black tracking-tight truncate" style={{ fontSize: 15, letterSpacing: '-0.01em' }}>PUCE</p>
                <p className="font-black uppercase truncate" style={{ color:'#4da6e8', fontSize: 10, letterSpacing: '0.18em' }}>Esmeraldas</p>
                <p className="truncate" style={{ color:'rgba(255,255,255,0.35)', fontSize: 9, fontWeight: 600, marginTop: 1 }}>Evaluación Docente</p>
              </div>
            )}
          </div>

          {/* Nav */}
          <nav className="flex-1 overflow-y-auto py-3 px-2.5" style={{ display:'flex', flexDirection:'column', gap: 2 }}>

            {/* ── Vista General ── */}
            <button
              onClick={() => { handleSistemaChange('overview'); setPeriodoActivo(''); setActiveAnio(undefined) }}
              className="w-full flex items-center gap-3 text-left transition-all rounded-xl"
              style={{
                padding: sidebarOpen ? '10px 12px' : '10px',
                justifyContent: sidebarOpen ? 'flex-start' : 'center',
                color: sistema === 'overview' ? '#fff' : 'rgba(255,255,255,0.5)',
                background: sistema === 'overview' ? 'linear-gradient(135deg,rgba(26,127,193,0.35),rgba(26,127,193,0.15))' : 'transparent',
                borderLeft: sistema === 'overview' ? '2px solid #4da6e8' : '2px solid transparent',
              }}
            >
              <LayoutDashboard size={17} style={{ flexShrink: 0 }} />
              {sidebarOpen && <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: '-0.01em' }}>Vista General</span>}
            </button>

            {sidebarOpen && <div style={{ height: 1, background:'rgba(255,255,255,0.06)', margin:'6px 4px' }} />}

            {/* ── MEIPA ── */}
            <button
              onClick={() => { setExpandedMEIPA(v => !v); if (sistema !== 'meipa') { handleSistemaChange('meipa'); setPeriodoActivo(''); setActiveAnio(undefined) } }}
              className="w-full flex items-center gap-3 text-left transition-all rounded-xl"
              style={{
                padding: sidebarOpen ? '10px 12px' : '10px',
                justifyContent: sidebarOpen ? 'flex-start' : 'center',
                color: sistema === 'meipa' ? '#fff' : 'rgba(255,255,255,0.55)',
                background: sistema === 'meipa' ? 'linear-gradient(135deg,rgba(99,102,241,0.3),rgba(99,102,241,0.12))' : 'transparent',
                borderLeft: sistema === 'meipa' ? '2px solid #818cf8' : '2px solid transparent',
              }}
            >
              <UserCheck size={17} style={{ flexShrink:0, color: sistema === 'meipa' ? '#a5b4fc' : 'inherit' }} />
              {sidebarOpen && <>
                <div className="flex-1 min-w-0">
                  <div style={{ fontSize:13, fontWeight:700, letterSpacing:'-0.01em' }}>MEIPA</div>
                  <div style={{ fontSize:9, color:'rgba(255,255,255,0.35)', fontWeight:600, letterSpacing:'0.1em' }}>2023 – 2024</div>
                </div>
                <span style={{ color:'rgba(255,255,255,0.3)' }}>
                  {expandedMEIPA ? <ChevronDown size={13}/> : <ChevronRight size={13}/>}
                </span>
              </>}
            </button>

            {/* MEIPA sub-items */}
            {sidebarOpen && expandedMEIPA && (
              <div style={{ marginLeft:12, paddingLeft:10, borderLeft:'1px solid rgba(99,102,241,0.25)', display:'flex', flexDirection:'column', gap:1 }}>
                {/* Vista General MEIPA */}
                <button
                  onClick={() => { handleSistemaChange('meipa'); setPeriodoActivo(''); setActiveAnio(undefined) }}
                  className="w-full flex items-center gap-2 text-left rounded-lg transition-all"
                  style={{
                    padding:'6px 10px',
                    color: sistema === 'meipa' && !periodoActivo ? '#c7d2fe' : 'rgba(255,255,255,0.4)',
                    background: sistema === 'meipa' && !periodoActivo ? 'rgba(99,102,241,0.15)' : 'transparent',
                    fontSize: 11.5, fontWeight: sistema === 'meipa' && !periodoActivo ? 600 : 400,
                  }}
                >
                  <LayoutDashboard size={11} style={{ flexShrink:0, opacity:0.7 }}/>
                  <span>Vista General</span>
                </button>
                {/* Period items MEIPA */}
                {[
                  { codigo:'202301', label:'I Período 2023' },
                  { codigo:'202302', label:'II Período 2023' },
                  { codigo:'202401', label:'I Período 2024' },
                ].map(p => {
                  const apiP  = periodos.find((x: any) => x.codigo === p.codigo)
                  const loaded = apiP ? apiP.cargado : false
                  const active = sistema === 'meipa' && periodoActivo === p.codigo
                  return (
                    <button key={p.codigo}
                      onClick={() => { handleSistemaChange('meipa'); setPeriodoActivo(p.codigo); setActiveAnio(PERIODO_TO_ANIO[p.codigo]) }}
                      className="w-full flex items-center gap-2 text-left rounded-lg transition-all"
                      style={{
                        padding:'6px 10px',
                        color: active ? '#e0e7ff' : loaded ? 'rgba(255,255,255,0.45)' : 'rgba(255,255,255,0.2)',
                        background: active ? 'rgba(99,102,241,0.2)' : 'transparent',
                        fontSize: 11.5, fontWeight: active ? 600 : 400,
                        cursor: loaded ? 'pointer' : 'default',
                      }}
                    >
                      <span style={{ width:6, height:6, borderRadius:'50%', flexShrink:0, background: active ? '#818cf8' : loaded ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.07)' }} />
                      <span className="flex-1 truncate">{p.label}</span>
                      {!loaded && <span style={{ fontSize:9, color:'rgba(255,255,255,0.18)', fontStyle:'italic' }}>sin datos</span>}
                    </button>
                  )
                })}
              </div>
            )}

            {sidebarOpen && <div style={{ height:1, background:'rgba(255,255,255,0.06)', margin:'6px 4px' }} />}

            {/* ── 360 / MECDI ── */}
            <button
              onClick={() => { setExpanded360(v => !v); if (sistema !== '360') { handleSistemaChange('360'); setActiveTab('docencia'); setPeriodoActivo(''); setActiveAnio(undefined) } }}
              className="w-full flex items-center gap-3 text-left transition-all rounded-xl"
              style={{
                padding: sidebarOpen ? '10px 12px' : '10px',
                justifyContent: sidebarOpen ? 'flex-start' : 'center',
                color: sistema === '360' ? '#fff' : 'rgba(255,255,255,0.55)',
                background: sistema === '360' ? 'linear-gradient(135deg,rgba(6,182,212,0.28),rgba(6,182,212,0.1))' : 'transparent',
                borderLeft: sistema === '360' ? '2px solid #22d3ee' : '2px solid transparent',
              }}
            >
              <BarChart3 size={17} style={{ flexShrink:0, color: sistema === '360' ? '#67e8f9' : 'inherit' }} />
              {sidebarOpen && <>
                <div className="flex-1 min-w-0">
                  <div style={{ fontSize:13, fontWeight:700, letterSpacing:'-0.01em' }}>360 / MECDI</div>
                  <div style={{ fontSize:9, color:'rgba(255,255,255,0.35)', fontWeight:600, letterSpacing:'0.1em' }}>2024 – 2025</div>
                </div>
                <span style={{ color:'rgba(255,255,255,0.3)' }}>
                  {expanded360 ? <ChevronDown size={13}/> : <ChevronRight size={13}/>}
                </span>
              </>}
            </button>

            {/* 360 sub-items */}
            {sidebarOpen && expanded360 && (
              <div style={{ marginLeft:12, paddingLeft:10, borderLeft:'1px solid rgba(6,182,212,0.2)', display:'flex', flexDirection:'column', gap:1 }}>
                {/* Vista General 360 */}
                <button
                  onClick={() => { handleSistemaChange('360'); setActiveTab('docencia'); setPeriodoActivo(''); setActiveAnio(undefined) }}
                  className="w-full flex items-center gap-2 text-left rounded-lg transition-all"
                  style={{
                    padding:'6px 10px',
                    color: sistema === '360' && !periodoActivo ? '#a5f3fc' : 'rgba(255,255,255,0.4)',
                    background: sistema === '360' && !periodoActivo ? 'rgba(6,182,212,0.12)' : 'transparent',
                    fontSize: 11.5, fontWeight: sistema === '360' && !periodoActivo ? 600 : 400,
                  }}
                >
                  <LayoutDashboard size={11} style={{ flexShrink:0, opacity:0.7 }}/>
                  <span>Vista General</span>
                </button>
                {/* Period items 360 */}
                {[
                  { codigo:'202402', label:'II Período 2024' },
                  { codigo:'202501', label:'I Período 2025' },
                  { codigo:'202502', label:'II Período 2025' },
                ].map(p => {
                  const apiP  = periodos.find((x: any) => x.codigo === p.codigo)
                  const loaded = apiP ? apiP.cargado : false
                  const active = sistema === '360' && periodoActivo === p.codigo
                  return (
                    <button key={p.codigo}
                      onClick={() => { handleSistemaChange('360'); setActiveTab('docencia'); setPeriodoActivo(p.codigo); setActiveAnio(PERIODO_TO_ANIO[p.codigo]) }}
                      className="w-full flex items-center gap-2 text-left rounded-lg transition-all"
                      style={{
                        padding:'6px 10px',
                        color: active ? '#cffafe' : loaded ? 'rgba(255,255,255,0.45)' : 'rgba(255,255,255,0.2)',
                        background: active ? 'rgba(6,182,212,0.18)' : 'transparent',
                        fontSize: 11.5, fontWeight: active ? 600 : 400,
                        cursor: loaded ? 'pointer' : 'default',
                      }}
                    >
                      <span style={{ width:6, height:6, borderRadius:'50%', flexShrink:0, background: active ? '#22d3ee' : loaded ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.07)' }} />
                      <span className="flex-1 truncate">{p.label}</span>
                      {!loaded && <span style={{ fontSize:9, color:'rgba(255,255,255,0.18)', fontStyle:'italic' }}>sin datos</span>}
                    </button>
                  )
                })}
                {/* Model tabs (no ABP) */}
                <div style={{ marginTop:4, paddingTop:4, borderTop:'1px solid rgba(255,255,255,0.06)' }}>
                  {TABS_360.filter(t => t.id !== 'abp' && t.id !== 'tecnologado').map(tab => {
                    const Icon = tab.icon
                    const active = sistema === '360' && activeTab === tab.id
                    return (
                      <button key={tab.id}
                        onClick={() => { handleSistemaChange('360'); handleTabChange(tab.id) }}
                        className="w-full flex items-center gap-2.5 text-left rounded-lg transition-all"
                        style={{
                          padding:'5px 10px',
                          color: active ? '#fff' : 'rgba(255,255,255,0.38)',
                          background: active ? `${tab.color}22` : 'transparent',
                          fontSize: 11.5, fontWeight: active ? 600 : 400,
                          marginBottom: 1,
                        }}
                      >
                        <Icon size={11} style={{ color: active ? tab.color : 'rgba(255,255,255,0.25)', flexShrink:0 }} />
                        <span className="flex-1 truncate">{tab.label}</span>
                        {active && <span style={{ width:4, height:4, borderRadius:'50%', background:tab.color, flexShrink:0 }} />}
                      </button>
                    )
                  })}
                </div>
              </div>
            )}

            {sidebarOpen && <div style={{ height:1, background:'rgba(255,255,255,0.06)', margin:'6px 4px' }} />}

            {/* ── Salud ── */}
            <button
              onClick={() => { setExpandedSalud(v => !v); if (sistema !== 'salud') { handleSistemaChange('salud'); setPeriodoActivo(''); setActiveAnio(undefined) } }}
              className="w-full flex items-center gap-3 text-left transition-all rounded-xl"
              style={{
                padding: sidebarOpen ? '10px 12px' : '10px',
                justifyContent: sidebarOpen ? 'flex-start' : 'center',
                color: sistema === 'salud' ? '#fff' : 'rgba(255,255,255,0.55)',
                background: sistema === 'salud' ? 'linear-gradient(135deg,rgba(220,38,38,0.28),rgba(220,38,38,0.1))' : 'transparent',
                borderLeft: sistema === 'salud' ? '2px solid #f87171' : '2px solid transparent',
              }}
            >
              <Heart size={17} style={{ flexShrink:0, color: sistema === 'salud' ? '#fca5a5' : 'inherit' }} />
              {sidebarOpen && <>
                <div className="flex-1 min-w-0">
                  <div style={{ fontSize:13, fontWeight:700, letterSpacing:'-0.01em' }}>Salud</div>
                  <div style={{ fontSize:9, color:'rgba(255,255,255,0.35)', fontWeight:600, letterSpacing:'0.1em' }}>ABP / Medicina</div>
                </div>
                <span style={{ color:'rgba(255,255,255,0.3)' }}>
                  {expandedSalud ? <ChevronDown size={13}/> : <ChevronRight size={13}/>}
                </span>
              </>}
            </button>

            {/* Salud sub-items */}
            {sidebarOpen && expandedSalud && (
              <div style={{ marginLeft:12, paddingLeft:10, borderLeft:'1px solid rgba(220,38,38,0.2)', display:'flex', flexDirection:'column', gap:1 }}>
                <button
                  onClick={() => { handleSistemaChange('salud'); setPeriodoActivo(''); setActiveAnio(undefined) }}
                  className="w-full flex items-center gap-2 text-left rounded-lg transition-all"
                  style={{
                    padding:'6px 10px',
                    color: sistema === 'salud' && !periodoActivo ? '#fecaca' : 'rgba(255,255,255,0.4)',
                    background: sistema === 'salud' && !periodoActivo ? 'rgba(220,38,38,0.12)' : 'transparent',
                    fontSize: 11.5, fontWeight: sistema === 'salud' && !periodoActivo ? 600 : 400,
                  }}
                >
                  <LayoutDashboard size={11} style={{ flexShrink:0, opacity:0.7 }}/>
                  <span>Vista General</span>
                </button>
                {[
                  { codigo:'202402', label:'II Período 2024' },
                  { codigo:'202501', label:'I Período 2025' },
                  { codigo:'202502', label:'II Período 2025' },
                ].map(p => {
                  const apiP  = periodos.find((x: any) => x.codigo === p.codigo)
                  const loaded = apiP ? apiP.cargado : false
                  const active = sistema === 'salud' && periodoActivo === p.codigo
                  return (
                    <button key={p.codigo}
                      onClick={() => { handleSistemaChange('salud'); setPeriodoActivo(p.codigo); setActiveAnio(PERIODO_TO_ANIO[p.codigo]) }}
                      className="w-full flex items-center gap-2 text-left rounded-lg transition-all"
                      style={{
                        padding:'6px 10px',
                        color: active ? '#fee2e2' : loaded ? 'rgba(255,255,255,0.45)' : 'rgba(255,255,255,0.2)',
                        background: active ? 'rgba(220,38,38,0.18)' : 'transparent',
                        fontSize: 11.5, fontWeight: active ? 600 : 400,
                        cursor: loaded ? 'pointer' : 'default',
                      }}
                    >
                      <span style={{ width:6, height:6, borderRadius:'50%', flexShrink:0, background: active ? '#f87171' : loaded ? 'rgba(255,255,255,0.2)' : 'rgba(255,255,255,0.07)' }} />
                      <span className="flex-1 truncate">{p.label}</span>
                      {!loaded && <span style={{ fontSize:9, color:'rgba(255,255,255,0.18)', fontStyle:'italic' }}>sin datos</span>}
                    </button>
                  )
                })}
                {/* ABP shown as Docencia */}
                <div style={{ marginTop:4, paddingTop:4, borderTop:'1px solid rgba(255,255,255,0.06)' }}>
                  <button
                    onClick={() => handleSistemaChange('salud')}
                    className="w-full flex items-center gap-2.5 text-left rounded-lg transition-all"
                    style={{
                      padding:'5px 10px',
                      color: sistema === 'salud' ? '#fff' : 'rgba(255,255,255,0.38)',
                      background: sistema === 'salud' ? 'rgba(220,38,38,0.2)' : 'transparent',
                      fontSize: 11.5, fontWeight: sistema === 'salud' ? 600 : 400,
                    }}
                  >
                    <GraduationCap size={11} style={{ color: sistema === 'salud' ? '#fca5a5' : 'rgba(255,255,255,0.25)', flexShrink:0 }} />
                    <span>Docencia (ABP)</span>
                    {sistema === 'salud' && <span style={{ width:4, height:4, borderRadius:'50%', background:'#f87171', flexShrink:0, marginLeft:'auto' }} />}
                  </button>
                </div>
              </div>
            )}

          </nav>

          {/* Bottom: toggle collapse */}
          <div className="px-3 py-3" style={{ borderTop:'1px solid rgba(255,255,255,0.07)' }}>
            <button
              onClick={() => setSidebarOpen(v => !v)}
              className="w-full flex items-center gap-3 rounded-lg transition-all"
              style={{ padding:'9px 10px', color:'rgba(255,255,255,0.38)', background:'transparent' }}
            >
              <Menu size={16} className="flex-shrink-0" />
              {sidebarOpen && <span style={{ fontSize: 12, fontWeight: 600 }}>Colapsar</span>}
            </button>
          </div>
        </aside>

        {/* ── MAIN AREA ─────────────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">

          {/* Topbar */}
          <header
            className="flex-shrink-0 flex items-center justify-between px-6 bg-white z-20"
            style={{ height: TOPBAR_H, borderBottom:'1px solid #e8edf2', boxShadow:'0 2px 12px rgba(0,0,0,0.06)' }}
          >
            <div className="flex items-center gap-3">
              <div>
                <span className="text-slate-800 font-black" style={{ fontSize: 14 }}>
                  {sistema === 'overview' ? 'Vista General' : sistema === 'meipa' ? 'MEIPA — Evaluación Docente' : sistema === 'salud' ? 'Salud — Docencia ABP' : `360 / MECDI — ${currentTabCfg.label}`}
                </span>
              </div>
              {loading && <div className="w-4 h-4 rounded-full border-2 border-slate-200 border-t-[#1a7fc1] animate-spin" />}
            </div>

            <div className="flex items-center gap-3">
              {/* Selector de Período (v2) */}
              {periodos.length > 0 && (
                <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5">
                  <FileText size={12} className="text-slate-400" />
                  <select
                    className="text-xs font-bold text-slate-600 bg-transparent outline-none cursor-pointer"
                    value={periodoActivo}
                    onChange={e => setPeriodoActivo(e.target.value)}
                  >
                    <option value="">Todos los períodos</option>
                    {periodos.map((p: any) => (
                      <option key={p.codigo} value={p.codigo} disabled={!p.cargado}>
                        {p.label} {p.cargado ? '' : '(sin datos)'}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Year (legacy) */}
              <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5">
                <Calendar size={12} className="text-slate-400" />
                <select
                  className="text-xs font-bold text-slate-600 bg-transparent outline-none cursor-pointer"
                  value={activeAnio ?? ''}
                  onChange={e => setActiveAnio(e.target.value ? Number(e.target.value) : undefined)}
                >
                  <option value="">Todos los años</option>
                  {aniosDisp.map((a: number) => <option key={a} value={a}>{a}</option>)}
                </select>
              </div>

              {/* Search */}
              <div className="relative hidden md:block">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={13} />
                <input
                  type="text" placeholder="Buscar docente o facultad…"
                  className="pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:border-[#1a7fc1] w-52 transition-all"
                  value={searchTerm} onChange={e => setSearchTerm(e.target.value)}
                />
              </div>

              {/* Update */}
              <button onClick={runETL} disabled={processing}
                className="flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-bold text-white disabled:opacity-60 transition-all"
                style={{ background:'linear-gradient(135deg,#1a7fc1,#0d5a8c)', boxShadow:'0 2px 8px rgba(26,127,193,0.3)' }}>
                <RefreshCw size={12} className={processing ? 'animate-spin' : ''} />
                {processing ? 'Actualizando…' : 'Actualizar'}
              </button>

              {/* Topbar icons (decorative, matching SIGA style) */}
              <div className="flex items-center gap-1 pl-2 border-l border-slate-200">
                <button className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 transition-colors relative">
                  <Bell size={16} />
                </button>
                <button className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold text-white transition-all"
                  style={{ background:'#e53e3e' }}>
                  <LogOut size={13} />
                  <span className="hidden lg:inline">Cerrar sesión</span>
                </button>
              </div>
            </div>
          </header>

          {/* Scrollable content */}
          <main className="flex-1 overflow-y-auto p-6" style={{ background:'#f5f7fa' }}>

          {/* ── OVERVIEW / COMPARATIVO ─────────────────────────────────────── */}
          {sistema === 'overview' && (
            <>
              <div className="flex items-center gap-3 mb-6">
                <div>
                  <h2 className="text-base font-bold text-slate-800">Vista Comparativa — MEIPA vs 360</h2>
                  <p className="text-[11px] text-slate-400">Análisis cruzado de ambos sistemas de evaluación docente</p>
                </div>
                {loading && <div className="ml-auto w-4 h-4 rounded-full border-2 border-slate-200 border-t-[#1e40af] animate-spin" />}
              </div>
              <ComparativoPanel comparativo={comparativo} />
              {comparativo?.mejores_peores && Object.keys(comparativo.mejores_peores).length > 0 && (
                <MejoresPeoresPanel mejoresPeores={comparativo.mejores_peores} />
              )}
              {comparativo?.variables_detalle && (() => {
                const vd = comparativo.variables_detalle as Record<string, any[]>
                const has360 = VD_360_TABS.some(t => (vd[t.key] || []).length > 0)
                const hasMeipa = (vd['meipa_docencia'] || []).length > 0
                return (
                  <>
                    {has360 && (
                      <VariablesDetallePanel
                        title="Puntaje por Variable — Sistema 360 / MECDI"
                        accentColor="#0056b3"
                        tabs={VD_360_TABS}
                        varData={vd}
                      />
                    )}
                    {hasMeipa && (
                      <VariablesDetallePanel
                        title="Puntaje por Variable — Sistema MEIPA"
                        accentColor="#6d28d9"
                        tabs={[{ key: 'meipa_docencia', label: 'Docencia', icon: GraduationCap, color: '#6d28d9' }]}
                        varData={vd}
                      />
                    )}
                  </>
                )
              })()}
              {todosDocentes.length > 0 && (
                <TodosDocentesPanel docentes={todosDocentes} />
              )}
              <AIConsultaPanel anio={activeAnio} />
            </>
          )}

          {/* ── MEIPA or 360 view ──────────────────────────────────────────── */}
          {sistema !== 'overview' && (
            <>
              {/* No data */}
              {!kpis && !loading && (
                <div className="flex flex-col items-center justify-center py-32 gap-5">
                  <div className="p-5 rounded-3xl" style={{ background:`${currentTabCfg.color}12` }}>
                    <currentTabCfg.icon size={40} style={{ color:currentTabCfg.color, opacity:0.5 }} />
                  </div>
                  <div className="text-center">
                    <h3 className="text-lg font-black text-slate-700 mb-1">Sin datos para {currentTabCfg.label}</h3>
                    <p className="text-sm text-slate-400 font-medium">
                      No se encontraron evaluaciones{activeAnio ? ` en ${activeAnio}` : ''}.
                    </p>
                  </div>
                </div>
              )}

              {kpis && (
                <>
                  {/* Section header */}
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-1 self-stretch rounded-full" style={{ background:currentTabCfg.color }} />
                    <div>
                      <h2 className="text-base font-bold text-slate-800">{currentTabCfg.label}</h2>
                      <p className="text-[11px] text-slate-400">{currentTabCfg.desc}
                        {activeAnio && (
                          <span className="ml-2 px-1.5 py-0.5 rounded text-[10px] font-bold"
                            style={{ background:`${currentTabCfg.color}12`, color:currentTabCfg.color }}>
                            {activeAnio}
                          </span>
                        )}
                      </p>
                    </div>
                    {loading && <div className="ml-auto w-4 h-4 rounded-full border-2 border-slate-200 border-t-[#1e40af] animate-spin" />}
                  </div>

                  {/* KPI Cards */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5 mb-8">
                    <KPICard
                      title="Puntaje Institucional"
                      value={`${kpis?.promedio_general_100 ?? '—'}`}
                      label="/ 100 pts"
                      icon={<BarChart3 size={21} style={{ color:currentTabCfg.color }} />}
                      iconBg={`${currentTabCfg.color}15`}
                      footer={`Escala 0-5: ${kpis?.promedio_general ?? '—'}`}
                      accent={currentTabCfg.color}
                    />
                    <KPICard
                      title="Evaluados"
                      value={kpis?.total_docentes}
                      label="participantes"
                      icon={<Users size={21} className="text-violet-500" />}
                      iconBg="#f5f3ff"
                      footer={`${kpis?.total_evaluaciones?.toLocaleString() ?? 0} registros totales`}
                      accent="#7c3aed"
                    />
                    <KPICard
                      title="Máximo Desempeño"
                      value={kpis?.mejor_docente?.toUpperCase() || 'N/A'}
                      label={kpis?.mejor_docente_facultad || ''}
                      icon={<Award size={21} className="text-amber-500" />}
                      iconBg="#fffbeb"
                      footer={`Puntaje: ${kpis?.mejor_docente_score ?? 'N/A'}`}
                      badge="TOP"
                      badgeStyle={{ color:'#d97706', background:'#fef3c7', border:'1px solid #fde68a' }}
                      accent="#f59e0b"
                    />
                    <KPICard
                      title="Unidades Académicas"
                      value={kpis?.total_facultades || 0}
                      label="unidades"
                      icon={<TrendingUp size={21} className="text-emerald-500" />}
                      iconBg="#ecfdf5"
                      footer={`${Object.keys(kpis?.promedio_por_facultad || {}).length} programas activos`}
                      accent="#10b981"
                    />
                  </div>

                  {/* Components */}
                  <div className="bg-white border border-slate-200 mb-8" style={{ borderRadius: 6, boxShadow:'0 1px 3px rgba(0,0,0,0.06)', padding:'20px 22px' }}>
                    <div className="flex items-center justify-between mb-5">
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em]">Desglose por Componente ·</span>
                        <h3 className="text-[13px] font-bold text-slate-700">
                          Componentes — <span style={{ color:currentTabCfg.color }}>{currentTabCfg.label}</span>
                        </h3>
                      </div>
                      <span className="text-[10px] font-bold px-2.5 py-1 rounded border"
                        style={{ color:currentTabCfg.color, background:`${currentTabCfg.color}08`, borderColor:`${currentTabCfg.color}25`, borderRadius: 4 }}>
                        Promedio institucional
                      </span>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {compLabels.map((cl, i) => (
                        <ComponentBar
                          key={cl.label}
                          label={cl.label}
                          value={compValues[i] || 0}
                          max={cl.max}
                          peso={compLabels[i] ? Math.round((cl.max / compLabels.reduce((s,x) => s+x.max, 0)) * 100) : 0}
                          color={COMP_COLORS[i]}
                        />
                      ))}
                    </div>
                  </div>

                  {/* Charts row */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                    {/* Pies */}
                    <div className="bg-white border border-slate-200 overflow-hidden" style={{ borderRadius: 6, boxShadow:'0 1px 3px rgba(0,0,0,0.06)' }}>
                      <div className="px-5 py-3.5 border-b border-slate-100 flex items-center gap-2">
                        <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em]">Demografía ·</span>
                        <h3 className="text-[13px] font-bold text-slate-700">Perfil del Cuerpo Docente</h3>
                      </div>
                      <div className="p-6 space-y-5">
                        <div>
                          <p className="text-[9px] font-black text-slate-400 uppercase tracking-[0.3em] mb-3">Por Nivel de Desempeño</p>
                          <Plot data={[{ values: Object.values(distNivel), labels: Object.keys(distNivel),
                            type:'pie', hole:0.62, marker:{colors:['#059669','#0056b3','#f59e0b','#dc2626','#94a3b8']},
                            textinfo:'percent', textfont:{size:11,family:'Inter'} }]}
                            layout={{ autosize:true, paper_bgcolor:'white', margin:{t:0,b:0,l:0,r:0}, showlegend:true,
                              legend:{orientation:'h',font:{size:10,family:'Inter'},y:-0.12}, height:175 }}
                            config={{ responsive:true, displayModeBar:false }} style={{ width:'100%' }} />
                        </div>
                        <div className="border-t border-slate-100 pt-5">
                          <p className="text-[9px] font-black text-slate-400 uppercase tracking-[0.3em] mb-3">Por Género</p>
                          <Plot data={[{ values: Object.values(demograficos?.sexo || {}), labels: Object.keys(demograficos?.sexo || {}),
                            type:'pie', hole:0.62, marker:{colors:['#0056b3','#f43f5e','#94a3b8']},
                            textinfo:'percent', textfont:{size:11,family:'Inter'} }]}
                            layout={{ autosize:true, paper_bgcolor:'white', margin:{t:0,b:0,l:0,r:0}, showlegend:true,
                              legend:{orientation:'h',font:{size:10,family:'Inter'},y:-0.12}, height:175 }}
                            config={{ responsive:true, displayModeBar:false }} style={{ width:'100%' }} />
                        </div>
                      </div>
                    </div>

                    {/* Bar por facultad */}
                    <div className="lg:col-span-2 bg-white border border-slate-200 overflow-hidden" style={{ borderRadius: 6, boxShadow:'0 1px 3px rgba(0,0,0,0.06)' }}>
                      <div className="px-5 py-3.5 border-b border-slate-100 flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em]">Comparativo ·</span>
                          <h3 className="text-[13px] font-bold text-slate-700">Puntaje Promedio por Unidad Académica</h3>
                        </div>
                        <span className="text-[10px] font-bold px-2.5 py-1 rounded border"
                          style={{ color:currentTabCfg.color, background:`${currentTabCfg.color}08`, borderColor:`${currentTabCfg.color}25`, borderRadius: 4 }}>
                          Sobre 100 pts
                        </span>
                      </div>
                      <div className="p-5">{(() => {
                        const fE = Object.entries(kpis?.promedio_por_facultad||{}).slice(0,15)
                        const fL = fE.map(([k])=>k)
                        const fV = fE.map(([,v])=>Number(v))
                        const fC = fV.map(v=>v>=90?'#047857':v>=75?currentTabCfg.color:v>=60?'#b45309':'#b91c1c')
                        const ch = excel3DBar(fL, fV, fC, {maxY:108,tickAngle:-35,marginB:120})
                        return <Plot data={ch.data} layout={ch.layout} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'400px'}} />
                      })()}</div>
                    </div>
                  </div>

                  {/* Tendencia anual */}
                  {tendencias.length > 1 && (
                    <div className="bg-white border border-slate-200 overflow-hidden mb-8" style={{ borderRadius: 6, boxShadow:'0 1px 3px rgba(0,0,0,0.06)' }}>
                      <div className="px-5 py-3.5 border-b border-slate-100 flex items-center gap-2">
                        <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em]">Evolución ·</span>
                        <h3 className="text-[13px] font-bold text-slate-700">Tendencia Anual — {currentTabCfg.label}</h3>
                      </div>
                      <div className="p-5">{(() => {
                        const yVals = tendencias.map(t=>+t.puntaje_100)
                        const ch = trendLine2D([{x:tendencias.map(t=>t.anio),y:yVals,color:currentTabCfg.color,name:currentTabCfg.label}],{minY:Math.min(...yVals)})
                        return <Plot data={ch.data} layout={ch.layout} config={{responsive:true,displayModeBar:false}} style={{width:'100%',height:'230px'}} />
                      })()}</div>
                    </div>
                  )}

                  {/* Analytics section */}
                  <AnalyticsSection analytics={analytics} color={currentTabCfg.color} />

                  {/* Bottom: AI + Table */}
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                    {/* AI Analysis */}
                    <div className="bg-white border border-slate-200 overflow-hidden flex flex-col"
                      style={{ borderRadius: 6, boxShadow:'0 1px 3px rgba(0,0,0,0.06)', borderLeft:'3px solid #4f46e5' }}>
                      <div className="px-5 py-3.5 border-b border-slate-100 flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <BrainCircuit size={14} className="text-indigo-400" />
                          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em]">Inteligencia Artificial ·</span>
                          <h3 className="text-[13px] font-bold text-slate-700">Análisis IA</h3>
                        </div>
                        <button onClick={runAnalysisIA}
                          className="text-[10px] font-black px-3 py-1.5 rounded-lg text-white flex items-center gap-1.5"
                          style={{ background:'linear-gradient(135deg,#4f46e5,#7c3aed)', boxShadow:'0 4px 12px rgba(79,70,229,0.3)' }}>
                          <BrainCircuit size={11}/> Generar
                        </button>
                      </div>
                      <div className="p-7 flex-1">
                        {aiAnalysis ? (
                          <p className="text-[11px] text-slate-700 leading-relaxed whitespace-pre-wrap">{aiAnalysis}</p>
                        ) : (
                          <div className="h-full flex flex-col items-center justify-center gap-3 py-8 text-center">
                            <BrainCircuit size={28} className="text-indigo-200" />
                            <p className="text-xs font-bold text-slate-400">
                              Presiona "Generar" para obtener un análisis estratégico con IA sobre {currentTabCfg.label}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Ranking Table */}
                    <div className="lg:col-span-2 bg-white border border-slate-200 overflow-hidden flex flex-col" style={{ borderRadius: 6, boxShadow:'0 1px 3px rgba(0,0,0,0.06)' }}>
                      <div className="px-5 py-3.5 border-b border-slate-100 flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] font-bold text-slate-400 uppercase tracking-[0.2em]">Ranking ·</span>
                          <h3 className="text-[13px] font-bold text-slate-700">
                            Tabla de {currentTabCfg.label} · {filteredRanking.length} registros
                          </h3>
                        </div>
                        <div className="relative lg:hidden">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={13} />
                          <input type="text" placeholder="Buscar…"
                            className="pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-[#0056b3] w-40"
                            value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
                        </div>
                      </div>

                      <div className="overflow-auto max-h-[500px] flex-1">
                        <table className="w-full text-left" style={{ minWidth:'640px' }}>
                          <thead className="sticky top-0 z-10">
                            <tr className="bg-slate-50/95 text-slate-400 uppercase text-[9px] font-black tracking-[0.18em] border-b border-slate-100">
                              <th className="px-3 py-3 w-8 text-center">#</th>
                              <th className="px-4 py-3">Docente</th>
                              <th className="px-3 py-3 hidden md:table-cell">Facultad</th>
                              {compLabels.map((cl,i) => (
                                <th key={i} className="px-2 py-3 text-center" title={`${cl.label} /${cl.max}`}>
                                  {cl.label.split(' ')[0].substring(0,4)}.
                                </th>
                              ))}
                              <th className="px-3 py-3 text-center font-black text-slate-600">Total/100</th>
                              <th className="px-3 py-3 text-center">Nivel</th>
                              <th className="px-3 py-3 text-center">PDF</th>
                            </tr>
                          </thead>
                          <tbody>
                            {filteredRanking.map((doc: any, i) => (
                              <tr key={i} className="border-b border-slate-50 hover:bg-blue-50/30 transition-colors group">
                                <td className="px-3 py-3 text-center">
                                  <span className="text-[10px] font-black text-slate-300 tabular-nums">{i + 1}</span>
                                </td>
                                <td className="px-4 py-3">
                                  <div className="font-bold text-slate-700 text-xs uppercase leading-tight group-hover:text-[#0056b3] transition-colors truncate max-w-[140px]">{doc.nombre}</div>
                                  <div className="text-[10px] text-slate-400 font-medium mt-0.5">{doc.cedula || doc.anio || doc.periodo}</div>
                                  {doc.fecha_ingreso && (
                                    <div className="text-[9px] text-slate-400 mt-0.5">
                                      Ingreso: {new Date(doc.fecha_ingreso + 'T00:00:00').toLocaleDateString('es-EC', { day: '2-digit', month: 'short', year: 'numeric' })}
                                    </div>
                                  )}
                                </td>
                                <td className="px-3 py-3 hidden md:table-cell">
                                  <span className="text-[10px] font-semibold text-slate-500 bg-slate-50 border border-slate-100 px-2 py-0.5 rounded-lg truncate block max-w-[110px]">{doc.facultad}</span>
                                </td>
                                {compKeys.map((ck, ci) => (
                                  <td key={ck} className="px-2 py-3 text-center">
                                    <span className="text-[11px] font-bold tabular-nums" style={{ color:COMP_COLORS[ci] }}>
                                      {(doc[ck] || 0).toFixed(1)}
                                    </span>
                                  </td>
                                ))}
                                <td className="px-3 py-3 text-center">
                                  <span className={`inline-flex items-center text-xs font-black px-2.5 py-1 rounded-lg ${
                                    (doc.puntaje_100||0)>=90?'bg-emerald-50 text-emerald-600 border border-emerald-100':
                                    (doc.puntaje_100||0)>=75?'bg-blue-50 text-[#0056b3] border border-blue-100':
                                    (doc.puntaje_100||0)>=60?'bg-amber-50 text-amber-600 border border-amber-100':
                                    'bg-red-50 text-red-600 border border-red-100'}`}>
                                    {(doc.puntaje_100 || 0).toFixed(1)}
                                  </span>
                                </td>
                                <td className="px-3 py-3 text-center">
                                  <NivelBadge nivel={doc.nivel || ''} />
                                </td>
                                <td className="px-3 py-3 text-center">
                                  {doc.cedula ? (
                                    <button
                                      onClick={() => handleDescargarPDF(doc.cedula)}
                                      disabled={pdfLoading === doc.cedula}
                                      title="Descargar reporte PDF individual"
                                      className="inline-flex items-center justify-center gap-1 text-[9px] font-black px-2 py-1.5 rounded-lg border transition-all"
                                      style={{
                                        background: pdfLoading === doc.cedula ? '#f1f5f9' : '#eff6ff',
                                        borderColor: '#bfdbfe',
                                        color: pdfLoading === doc.cedula ? '#94a3b8' : '#0056b3',
                                        cursor: pdfLoading === doc.cedula ? 'not-allowed' : 'pointer',
                                      }}
                                    >
                                      {pdfLoading === doc.cedula
                                        ? <RefreshCw size={10} className="animate-spin" />
                                        : <Download size={10} />
                                      }
                                    </button>
                                  ) : (
                                    <span className="text-slate-200">—</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {filteredRanking.length === 0 && (
                          <div className="p-20 text-center text-slate-400 text-xs font-bold uppercase tracking-widest">
                            No se encontraron registros.
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </>
              )}

              {/* Todos los Docentes — filtrado por modelo/periodo de esta sección */}
              {todosDocentes.length > 0 && (() => {
                const tabLabel = sistema === 'meipa' ? 'MEIPA · Docencia'
                  : sistema === 'salud' ? 'Salud / ABP · 360/MECDI'
                  : `${activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} · 360/MECDI`
                const { modelo, sistemaParam } = getQueryParams()
                return (
                  <div className="mt-6">
                    <TodosDocentesPanel
                      docentes={todosDocentes}
                      context={{ modelo: modelo || '', sistema: sistemaParam || '', label: tabLabel }}
                    />
                  </div>
                )
              })()}
            </>
          )}

          {/* Footer */}
          <div className="mt-12 pt-8 border-t border-slate-200/80 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <img src={LOGO_URL} alt="PUCESE" className="h-7 object-contain opacity-50" />
              <div className="h-4 w-px bg-slate-200" />
              <p className="text-[11px] text-slate-400 font-medium">© 2025 · Pontificia Universidad Católica del Ecuador · Sede Esmeraldas</p>
            </div>
            <p className="text-[10px] text-slate-400 font-black tracking-widest uppercase">SIGA · Calidad Docente v4.0</p>
          </div>
        </main>
        </div>{/* end MAIN AREA */}
      </div>{/* end outer flex */}
    </>
  )
}
