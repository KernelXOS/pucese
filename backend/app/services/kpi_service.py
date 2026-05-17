from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.evaluacion import Evaluacion
from app.models.docente import PersonalPeriodo

# Weight definitions per model
MODEL_CONFIG = {
    # Het.Est(50) + Pares(20) + CEV/aula_virtual(10) + Auto(20) = 100
    'docencia':       {'components': [('het_estudiantil',50),('eval_pares',20),('aula_virtual',10),('autoevaluacion',20)], 'label': 'Docencia'},
    'abp':            {'components': [('het_estudiantil',50),('eval_pares',20),('aula_virtual',10),('autoevaluacion',20)], 'label': 'Salud / ABP'},
    'tecnologado':    {'components': [('het_estudiantil',50),('eval_pares',20),('aula_virtual',10),('autoevaluacion',20)], 'label': 'Tecnologado'},
    # Het.Est(60) + Auto(30) + CEV(10) = 100  (sin pares)
    'posgrado':       {'components': [('het_estudiantil',60),('autoevaluacion',30),('aula_virtual',10)],                   'label': 'Posgrado'},
    # Het.Dir.Invest(50) + Auto(20) + Par(15) + Decano(15) = 100
    'investigacion':  {'components': [('comp_hetero_dir',50),('comp_auto',20),('comp_pares',15),('comp_hetero_est',15)],   'label': 'Investigación'},
    # Het.Est(50) + Auto(20) + Het.Dir.Acad(15) + Het.Dir.Invest(15) = 100
    'vinculacion':    {'components': [('comp_hetero_est',50),('comp_auto',20),('comp_hetero_dir',15),('comp_pares',15)],   'label': 'Vinculación'},
    # Coevalúa.Dir(50) + Het.Docentes(30) + Auto(20) = 100
    'gestion':        {'components': [('comp_hetero_dir',50),('comp_hetero_est',30),('comp_auto',20)],                     'label': 'Gestión'},
    'administrativo': {'components': [('comp_hetero_dir',50),('comp_hetero_est',30),('comp_auto',20)],                     'label': 'Administrativo'},
}

MEIPA_MODEL_CONFIG = {
    'docencia': {
        'components': [
            ('comp_hetero_est', 40),
            ('comp_auto',       20),
            ('comp_hetero_dir', 20),
            ('comp_pares',      20),
        ],
        'label': 'MEIPA — Docencia',
    }
}


def _base_q(db: Session, modelo: str = None, anio: int = None, sistema: str = None):
    q = db.query(Evaluacion)
    if modelo:
        q = q.filter(Evaluacion.modelo == modelo)
    if anio:
        q = q.filter(Evaluacion.anio == anio)
    if sistema:
        q = q.filter(Evaluacion.sistema == sistema)
    return q


class KPIService:

    def get_institutional_kpis(
        self,
        db: Session,
        modelo: str = None,
        anio: int = None,
        sistema: str = None,
    ):
        q = _base_q(db, modelo, anio, sistema)
        total = q.count()
        if total == 0:
            return None

        total_docentes   = q.with_entities(func.count(func.distinct(Evaluacion.docente_nombre))).scalar()
        total_facultades = q.with_entities(func.count(func.distinct(Evaluacion.facultad))).scalar()

        promedio_100 = q.with_entities(func.avg(Evaluacion.puntaje_100)).scalar() or 0
        promedio_gral_100 = round(promedio_100, 2)
        promedio_gral_5   = round(promedio_gral_100 / 100 * 5, 2)

        mejor = q.with_entities(
            Evaluacion.docente_nombre, Evaluacion.facultad,
            func.avg(Evaluacion.puntaje_100).label('avg_score')
        ).group_by(Evaluacion.docente_nombre).order_by(
            func.avg(Evaluacion.puntaje_100).desc()
        ).first()

        peor = q.with_entities(
            Evaluacion.docente_nombre, Evaluacion.facultad,
            func.avg(Evaluacion.puntaje_100).label('avg_score')
        ).group_by(Evaluacion.docente_nombre).order_by(
            func.avg(Evaluacion.puntaje_100).asc()
        ).first()

        por_facultad = q.with_entities(
            Evaluacion.facultad, func.avg(Evaluacion.puntaje_100)
        ).group_by(Evaluacion.facultad).all()

        dist_nivel = q.with_entities(
            Evaluacion.nivel_desempeno, func.count(Evaluacion.id)
        ).filter(Evaluacion.nivel_desempeno != None).group_by(Evaluacion.nivel_desempeno).all()

        # Choose component config based on sistema
        if sistema == 'meipa':
            cfg = MEIPA_MODEL_CONFIG.get(modelo or 'docencia', MEIPA_MODEL_CONFIG['docencia'])
        else:
            cfg = MODEL_CONFIG.get(modelo or 'docencia', MODEL_CONFIG['docencia'])

        componentes = {}
        for col, peso in cfg['components']:
            col_attr = getattr(Evaluacion, col, None)
            if col_attr is None:
                continue
            avg_val = q.with_entities(func.avg(col_attr)).scalar() or 0
            n_val   = q.with_entities(func.count(Evaluacion.id)).filter(col_attr > 0).scalar() or 0
            componentes[col] = {'peso': peso, 'promedio': round(avg_val, 2), 'n_docentes': n_val}

        anios_disponibles   = [r[0] for r in db.query(func.distinct(Evaluacion.anio)).order_by(Evaluacion.anio).all() if r[0]]
        modelos_disponibles = [r[0] for r in db.query(func.distinct(Evaluacion.modelo)).all() if r[0]]
        sistemas_disponibles= [r[0] for r in db.query(func.distinct(Evaluacion.sistema)).all() if r[0]]

        return {
            'promedio_general':        promedio_gral_5,
            'promedio_general_100':    promedio_gral_100,
            'mejor_docente':           mejor[0] if mejor else 'N/A',
            'mejor_docente_facultad':  mejor[1] if mejor else 'N/A',
            'mejor_docente_score':     round(mejor[2], 2) if mejor else 0,
            'peor_docente':            peor[0] if peor else 'N/A',
            'total_evaluaciones':      total,
            'total_docentes':          total_docentes,
            'total_facultades':        total_facultades,
            'promedio_por_facultad':   {f: round(p, 2) for f, p in por_facultad if f},
            'distribucion_nivel':      {n if n else 'Sin datos': c for n, c in dist_nivel},
            'componentes':             componentes,
            'modelo_label':            cfg['label'],
            'anios_disponibles':       anios_disponibles,
            'modelos_disponibles':     modelos_disponibles,
            'sistemas_disponibles':    sistemas_disponibles,
        }

    def get_meipa_kpis(self, db: Session, anio: int = None):
        """Return aggregated MEIPA-specific metrics."""
        return self.get_institutional_kpis(db, modelo='docencia', anio=anio, sistema='meipa')

    def get_analytics(
        self,
        db: Session,
        sistema: str = None,
        modelo: str = None,
        anio: int = None,
    ) -> dict:
        """
        Return breakdowns:
          por_genero:    {M: avg, F: avg}
          por_edad:      {'<30': avg, '31-45': avg, '46-60': avg, '61+': avg}
          por_antiguedad:{'0-3 años': avg, '4-10 años': avg, '11-20 años': avg, '20+ años': avg}
          por_funcion:   {'DOCENCIA': avg, 'COORDINACIÓN': avg, ...}
        """
        q = _base_q(db, modelo, anio, sistema)

        # ── Por género ────────────────────────────────────────────────────────
        rows_g = q.with_entities(Evaluacion.sexo, func.avg(Evaluacion.puntaje_100))\
                   .filter(Evaluacion.sexo != None, Evaluacion.sexo != '')\
                   .group_by(Evaluacion.sexo).all()
        # Normalise gender labels from different source formats
        _GENERO_NORM = {
            'mujer': 'Mujer', 'femenino': 'Mujer', 'f': 'Mujer',
            'hombre': 'Hombre', 'masculino': 'Hombre', 'm': 'Hombre',
        }
        _merged: dict = {}
        for g, v in rows_g:
            key = _GENERO_NORM.get(str(g).lower().strip(), str(g).strip())
            _merged[key] = (_merged.get(key, []))
            _merged[key].append(float(v or 0))
        por_genero = {k: round(sum(vs)/len(vs), 2) for k, vs in _merged.items() if vs}

        # ── Por edad (bracket) ────────────────────────────────────────────────
        edad_rows = q.with_entities(Evaluacion.edad, Evaluacion.puntaje_100)\
                     .filter(Evaluacion.edad != None, Evaluacion.puntaje_100 != None).all()
        brackets_edad = {'<30': [], '31-45': [], '46-60': [], '61+': []}
        for edad, pun in edad_rows:
            if edad and pun is not None:
                if edad < 30:
                    brackets_edad['<30'].append(pun)
                elif edad <= 45:
                    brackets_edad['31-45'].append(pun)
                elif edad <= 60:
                    brackets_edad['46-60'].append(pun)
                else:
                    brackets_edad['61+'].append(pun)
        por_edad = {k: round(sum(v)/len(v), 2) if v else None for k, v in brackets_edad.items()}

        # ── Por antigüedad ────────────────────────────────────────────────────
        antig_rows = q.with_entities(Evaluacion.antiguedad_anos, Evaluacion.puntaje_100)\
                      .filter(Evaluacion.antiguedad_anos != None, Evaluacion.puntaje_100 != None).all()
        brackets_ant = {'0-3 años': [], '4-10 años': [], '11-20 años': [], '20+ años': []}
        for ant, pun in antig_rows:
            if ant is not None and pun is not None:
                if ant <= 3:
                    brackets_ant['0-3 años'].append(pun)
                elif ant <= 10:
                    brackets_ant['4-10 años'].append(pun)
                elif ant <= 20:
                    brackets_ant['11-20 años'].append(pun)
                else:
                    brackets_ant['20+ años'].append(pun)
        por_antiguedad = {k: round(sum(v)/len(v), 2) if v else None for k, v in brackets_ant.items()}

        # ── Por función ───────────────────────────────────────────────────────
        rows_f = q.with_entities(Evaluacion.funcion_docente, func.avg(Evaluacion.puntaje_100))\
                   .filter(Evaluacion.funcion_docente != None, Evaluacion.funcion_docente != '')\
                   .group_by(Evaluacion.funcion_docente).all()
        por_funcion = {f: round(v or 0, 2) for f, v in rows_f}

        return {
            'por_genero':      por_genero,
            'por_edad':        por_edad,
            'por_antiguedad':  por_antiguedad,
            'por_funcion':     por_funcion,
        }

    def get_comparativo(self, db: Session, anio: int = None) -> dict:
        """Full overview: MEIPA vs 360, models, trends, faculty, gender, age, seniority, cross-analysis."""
        _GENERO_NORM = {
            'mujer': 'Mujer', 'femenino': 'Mujer', 'f': 'Mujer',
            'hombre': 'Hombre', 'masculino': 'Hombre', 'm': 'Hombre',
        }
        AGE_BRACKETS    = ['< 30 años', '31-45 años', '46-60 años', '61+ años']
        ANTIG_BRACKETS  = ['0-3 años', '4-10 años', '11-20 años', '20+ años']

        def avg_for(sistema, modelo=None):
            q = _base_q(db, modelo, anio, sistema)
            v = q.with_entities(func.avg(Evaluacion.puntaje_100)).scalar()
            n = q.count()
            return {'promedio': round(v, 2) if v else None, 'n': n}

        meipa_overall  = avg_for('meipa')
        tres60_overall = avg_for('360')

        modelos_360    = ['docencia', 'abp', 'posgrado', 'tecnologado', 'vinculacion', 'gestion', 'administrativo', 'investigacion']
        por_modelo_360 = {m: avg_for('360', m) for m in modelos_360}

        def trend(sistema):
            q = db.query(Evaluacion)
            if sistema:
                q = q.filter(Evaluacion.sistema == sistema)
            if anio:
                q = q.filter(Evaluacion.anio == anio)
            rows = q.with_entities(Evaluacion.anio, func.avg(Evaluacion.puntaje_100))\
                    .filter(Evaluacion.anio != None)\
                    .group_by(Evaluacion.anio)\
                    .order_by(Evaluacion.anio).all()
            return [{'anio': r[0], 'promedio': round(r[1], 2) if r[1] else None} for r in rows]

        def trend_periodos(sistema):
            """Tendencia agrupada por período (ej: 2023-I, 2023-II, 2024-I…)."""
            q = db.query(Evaluacion)
            if sistema:
                q = q.filter(Evaluacion.sistema == sistema)
            if anio:
                q = q.filter(Evaluacion.anio == anio)
            rows = q.with_entities(
                Evaluacion.periodo,
                Evaluacion.anio,
                func.avg(Evaluacion.puntaje_100),
                func.count(Evaluacion.id),
            ).filter(
                Evaluacion.periodo != None,
                Evaluacion.anio    != None,
            ).group_by(Evaluacion.periodo, Evaluacion.anio)\
             .order_by(Evaluacion.anio, Evaluacion.periodo).all()
            return [
                {'periodo': r[0], 'anio': r[1],
                 'promedio': round(r[2], 2) if r[2] else None,
                 'n': r[3]}
                for r in rows
            ]

        def por_modelo_por_periodo_360():
            """Promedio por (modelo, período) para el gráfico de barras agrupado."""
            modelos = ['docencia','abp','posgrado','tecnologado','vinculacion','gestion','investigacion']
            result = {}
            for m in modelos:
                q = db.query(Evaluacion).filter(
                    Evaluacion.sistema == '360',
                    Evaluacion.modelo  == m,
                )
                if anio:
                    q = q.filter(Evaluacion.anio == anio)
                rows = q.with_entities(
                    Evaluacion.periodo,
                    Evaluacion.anio,
                    func.avg(Evaluacion.puntaje_100),
                    func.count(Evaluacion.id),
                ).filter(Evaluacion.periodo != None, Evaluacion.anio != None)\
                 .group_by(Evaluacion.periodo, Evaluacion.anio)\
                 .order_by(Evaluacion.anio, Evaluacion.periodo).all()
                result[m] = [
                    {'periodo': r[0], 'anio': r[1],
                     'promedio': round(r[2], 2) if r[2] else None,
                     'n': r[3]}
                    for r in rows
                ]
            return result

        # ── Base query (all records, optional year filter) ────────────────────
        q_all = db.query(Evaluacion)
        if anio:
            q_all = q_all.filter(Evaluacion.anio == anio)

        # ── Facultades ────────────────────────────────────────────────────────
        rows_fac = (
            q_all.with_entities(Evaluacion.facultad,
                                func.avg(Evaluacion.puntaje_100),
                                func.count())
            .filter(Evaluacion.facultad != None, Evaluacion.facultad != '')
            .group_by(Evaluacion.facultad)
            .order_by(func.avg(Evaluacion.puntaje_100).desc())
            .all()
        )
        por_facultad = [{'facultad': f, 'promedio': round(p, 2), 'n': n}
                        for f, p, n in rows_fac if f]

        # ── Por género ────────────────────────────────────────────────────────
        rows_g = (
            q_all.with_entities(Evaluacion.sexo, func.avg(Evaluacion.puntaje_100))
            .filter(Evaluacion.sexo != None, Evaluacion.sexo != '')
            .group_by(Evaluacion.sexo).all()
        )
        _mg: dict = {}
        for g, v in rows_g:
            key = _GENERO_NORM.get(str(g).lower().strip(), str(g).strip())
            _mg.setdefault(key, []).append(float(v or 0))
        por_genero = {k: round(sum(vs)/len(vs), 2) for k, vs in _mg.items()}

        # ── Por edad ──────────────────────────────────────────────────────────
        edad_rows = (
            q_all.with_entities(Evaluacion.edad, Evaluacion.puntaje_100)
            .filter(Evaluacion.edad != None, Evaluacion.puntaje_100 != None).all()
        )
        _be: dict = {b: [] for b in AGE_BRACKETS}
        for edad, pun in edad_rows:
            if edad is None or pun is None: continue
            if edad < 30:   _be['< 30 años'].append(pun)
            elif edad <= 45: _be['31-45 años'].append(pun)
            elif edad <= 60: _be['46-60 años'].append(pun)
            else:            _be['61+ años'].append(pun)
        por_edad = {k: round(sum(v)/len(v), 2) if v else None for k, v in _be.items()}

        # ── Por antigüedad ────────────────────────────────────────────────────
        antig_rows = (
            q_all.with_entities(Evaluacion.antiguedad_anos, Evaluacion.puntaje_100)
            .filter(Evaluacion.antiguedad_anos != None, Evaluacion.puntaje_100 != None).all()
        )
        _ba: dict = {b: [] for b in ANTIG_BRACKETS}
        for ant, pun in antig_rows:
            if ant is None or pun is None: continue
            if ant <= 3:    _ba['0-3 años'].append(pun)
            elif ant <= 10: _ba['4-10 años'].append(pun)
            elif ant <= 20: _ba['11-20 años'].append(pun)
            else:           _ba['20+ años'].append(pun)
        por_antiguedad = {k: round(sum(v)/len(v), 2) if v else None for k, v in _ba.items()}

        # ── Género × Edad cross-analysis ──────────────────────────────────────
        gedad_rows = (
            q_all.with_entities(Evaluacion.sexo, Evaluacion.edad, Evaluacion.puntaje_100)
            .filter(Evaluacion.sexo != None, Evaluacion.edad != None,
                    Evaluacion.puntaje_100 != None).all()
        )
        _cross: dict = {g: {b: [] for b in AGE_BRACKETS} for g in ('Mujer', 'Hombre')}
        for sexo, edad, pun in gedad_rows:
            gkey = _GENERO_NORM.get(str(sexo).lower().strip(), str(sexo).strip())
            if gkey not in _cross: continue
            if edad < 30:   bkt = '< 30 años'
            elif edad <= 45: bkt = '31-45 años'
            elif edad <= 60: bkt = '46-60 años'
            else:            bkt = '61+ años'
            _cross[gkey][bkt].append(pun)
        genero_edad = {
            g: {b: round(sum(v)/len(v), 2) if v else None for b, v in brackets.items()}
            for g, brackets in _cross.items()
        }

        # ── Género × Antigüedad cross-analysis ────────────────────────────────
        gantig_rows = (
            q_all.with_entities(Evaluacion.sexo, Evaluacion.antiguedad_anos, Evaluacion.puntaje_100)
            .filter(Evaluacion.sexo != None, Evaluacion.antiguedad_anos != None,
                    Evaluacion.puntaje_100 != None).all()
        )
        _crossa: dict = {g: {b: [] for b in ANTIG_BRACKETS} for g in ('Mujer', 'Hombre')}
        for sexo, ant, pun in gantig_rows:
            gkey = _GENERO_NORM.get(str(sexo).lower().strip(), str(sexo).strip())
            if gkey not in _crossa: continue
            if ant <= 3:    bkt = '0-3 años'
            elif ant <= 10: bkt = '4-10 años'
            elif ant <= 20: bkt = '11-20 años'
            else:           bkt = '20+ años'
            _crossa[gkey][bkt].append(pun)
        genero_antiguedad = {
            g: {b: round(sum(v)/len(v), 2) if v else None for b, v in brackets.items()}
            for g, brackets in _crossa.items()
        }

        # ── Demografía por período ────────────────────────────────────────────
        # Género × período
        gp_rows = (
            q_all.with_entities(Evaluacion.periodo, Evaluacion.anio, Evaluacion.sexo, func.avg(Evaluacion.puntaje_100))
            .filter(Evaluacion.periodo != None, Evaluacion.sexo != None, Evaluacion.sexo != '')
            .group_by(Evaluacion.periodo, Evaluacion.anio, Evaluacion.sexo)
            .order_by(Evaluacion.anio, Evaluacion.periodo).all()
        )
        _gp: dict = {}
        for periodo, anio_val, sexo, avg_v in gp_rows:
            gkey = _GENERO_NORM.get(str(sexo).lower().strip(), str(sexo).strip())
            if periodo not in _gp:
                _gp[periodo] = {'periodo': periodo, 'anio': anio_val}
            _gp[periodo][gkey] = round(float(avg_v), 2) if avg_v else None
        genero_por_periodo = sorted(_gp.values(), key=lambda x: (x.get('anio', 0), x.get('periodo', '')))

        # Edad × período
        ep_raw = (
            q_all.with_entities(Evaluacion.periodo, Evaluacion.anio, Evaluacion.edad, Evaluacion.puntaje_100)
            .filter(Evaluacion.periodo != None, Evaluacion.edad != None, Evaluacion.puntaje_100 != None).all()
        )
        _ep: dict = {}
        for periodo, anio_val, edad, pun in ep_raw:
            if not periodo or edad is None: continue
            if edad < 30:    bracket = '< 30 años'
            elif edad <= 45: bracket = '31-45 años'
            elif edad <= 60: bracket = '46-60 años'
            else:            bracket = '61+ años'
            if periodo not in _ep:
                _ep[periodo] = {'periodo': periodo, 'anio': anio_val, '_b': {b: [] for b in AGE_BRACKETS}}
            _ep[periodo]['_b'][bracket].append(float(pun))
        edad_por_periodo = []
        for p, d in sorted(_ep.items(), key=lambda x: (x[1].get('anio', 0), x[0])):
            entry: dict = {'periodo': d['periodo'], 'anio': d['anio']}
            for b in AGE_BRACKETS:
                v = d['_b'][b]
                entry[b] = round(sum(v)/len(v), 2) if v else None
            edad_por_periodo.append(entry)

        # Antigüedad × período
        ap_raw = (
            q_all.with_entities(Evaluacion.periodo, Evaluacion.anio, Evaluacion.antiguedad_anos, Evaluacion.puntaje_100)
            .filter(Evaluacion.periodo != None, Evaluacion.antiguedad_anos != None, Evaluacion.puntaje_100 != None).all()
        )
        _ant: dict = {}
        for periodo, anio_val, ant, pun in ap_raw:
            if not periodo or ant is None: continue
            if ant <= 3:    bracket = '0-3 años'
            elif ant <= 10: bracket = '4-10 años'
            elif ant <= 20: bracket = '11-20 años'
            else:           bracket = '20+ años'
            if periodo not in _ant:
                _ant[periodo] = {'periodo': periodo, 'anio': anio_val, '_b': {b: [] for b in ANTIG_BRACKETS}}
            _ant[periodo]['_b'][bracket].append(float(pun))
        antiguedad_por_periodo = []
        for p, d in sorted(_ant.items(), key=lambda x: (x[1].get('anio', 0), x[0])):
            entry2: dict = {'periodo': d['periodo'], 'anio': d['anio']}
            for b in ANTIG_BRACKETS:
                v = d['_b'][b]
                entry2[b] = round(sum(v)/len(v), 2) if v else None
            antiguedad_por_periodo.append(entry2)

        # ── Mejores y Peores por modelo 360 ──────────────────────────────────
        RANKING_MODELS = {
            'Pregrado':      'docencia',
            'Salud / ABP':   'abp',
            'Vinculación':   'vinculacion',
            'Investigación': 'investigacion',
            'Gestión':       'gestion',
        }
        mejores_peores = {}
        for label, modelo in RANKING_MODELS.items():
            q_m = db.query(Evaluacion).filter(
                Evaluacion.sistema == '360',
                Evaluacion.modelo == modelo,
                Evaluacion.puntaje_100.isnot(None),
                Evaluacion.docente_nombre.isnot(None),
            )
            if anio:
                q_m = q_m.filter(Evaluacion.anio == anio)
            rows = q_m.with_entities(
                Evaluacion.docente_nombre,
                Evaluacion.facultad,
                Evaluacion.cedula,
                func.avg(Evaluacion.puntaje_100).label('puntaje'),
                Evaluacion.nivel_desempeno,
            ).group_by(
                Evaluacion.docente_nombre, Evaluacion.facultad, Evaluacion.cedula
            ).order_by(func.avg(Evaluacion.puntaje_100).desc()).all()

            def _td(r):
                return {
                    'nombre':   r[0] or 'Sin nombre',
                    'facultad': r[1] or '',
                    'puntaje':  round(float(r[3] or 0), 1),
                    'nivel':    r[4] or 'Sin datos',
                }

            all_ranked = [_td(r) for r in rows]
            mejores_peores[label] = {
                'mejores': all_ranked[:5],
                'peores':  list(reversed(all_ranked[-5:])) if len(all_ranked) >= 5 else list(reversed(all_ranked)),
                'total':   len(all_ranked),
            }

        # ── Estadísticas descriptivas por sistema y por modelo ───────────────
        import statistics as _stat

        def _puntajes(sistema_f=None, modelo_f=None):
            q2 = db.query(Evaluacion.puntaje_100).filter(Evaluacion.puntaje_100.isnot(None))
            if anio:      q2 = q2.filter(Evaluacion.anio == anio)
            if sistema_f: q2 = q2.filter(Evaluacion.sistema == sistema_f)
            if modelo_f:  q2 = q2.filter(Evaluacion.modelo == modelo_f)
            return [float(r[0]) for r in q2.all()]

        def _desc(vals):
            if not vals:
                return None
            n = len(vals)
            mean = sum(vals) / n
            variance = sum((v - mean) ** 2 for v in vals) / n
            sorted_v = sorted(vals)
            mid = n // 2
            median = (sorted_v[mid - 1] + sorted_v[mid]) / 2 if n % 2 == 0 else sorted_v[mid]
            bins: dict = {}
            for v in vals:
                b = int(v // 5) * 5
                key = f"{b}–{b+5}"
                bins[key] = bins.get(key, 0) + 1
            moda_bin = max(bins, key=lambda k: bins[k])
            return {
                'n': n, 'media': round(mean, 2), 'mediana': round(median, 2),
                'varianza': round(variance, 2), 'desv_std': round(variance ** 0.5, 2),
                'moda_rango': moda_bin, 'moda_freq': bins[moda_bin],
                'min': round(sorted_v[0], 2), 'max': round(sorted_v[-1], 2),
            }

        estadisticas = {
            'meipa': _desc(_puntajes('meipa')),
            '360':   _desc(_puntajes('360')),
            'por_modelo': {
                m: _desc(_puntajes('360', m))
                for m in ['docencia', 'abp', 'vinculacion', 'investigacion', 'gestion', 'tecnologado', 'posgrado']
            },
        }

        # ── Variables detalle: best/worst components + teachers per model ───
        # (col, label, max_db_value)  — max_db_value is used to normalize to %
        _VARS_CFG = {
            '360_docencia': ('360', 'docencia', [
                ('het_estudiantil', 'Heteroevaluación Estudiantil', 50),
                ('eval_pares',      'Evaluación por Pares',         20),
                ('aula_virtual',    'Aula Virtual / CEV',           10),
                ('autoevaluacion',  'Autoevaluación',               20),
            ]),
            '360_abp': ('360', 'abp', [
                ('het_estudiantil', 'Het. Estudiantil (Med.)',       50),
                ('eval_pares',      'Evaluación por Pares',          20),
                ('aula_virtual',    'Aula Virtual / CEV',            10),
                ('autoevaluacion',  'Autoevaluación',                20),
            ]),
            '360_vinculacion': ('360', 'vinculacion', [
                ('comp_hetero_est', 'Het. Estudiantil',              100),
                ('comp_hetero_dir', 'Het. Dir. Académico',           100),
                ('comp_auto',       'Autoevaluación',                100),
            ]),
            '360_investigacion': ('360', 'investigacion', [
                ('comp_hetero_dir', 'Het. Dir. Investigación',       100),
                ('comp_pares',      'Coevaluación Par',              100),
                ('comp_hetero_est', 'Het. Decano / Coord.',          100),
                ('comp_auto',       'Autoevaluación',                100),
            ]),
            '360_gestion': ('360', 'gestion', [
                ('comp_hetero_dir', 'Coevalúa. Directivo Superior',  100),
                ('comp_hetero_est', 'Het. Docentes',                 100),
                ('comp_auto',       'Autoevaluación',                100),
            ]),
            'meipa_docencia': ('meipa', 'docencia', [
                ('comp_hetero_est', 'Heteroevaluación Estudiantil',  100),
                ('comp_hetero_dir', 'Coord. → Docente',              100),
                ('comp_pares',      'Evaluación por Pares',          100),
                ('comp_auto',       'Autoevaluación',                100),
            ]),
        }

        def _teacher_fmt(r, mx):
            raw = float(r[2] or 0)
            return {'nombre': r[0] or 'Sin nombre', 'cedula': r[1] or '—',
                    'comp_pct': round(min(100.0, raw / mx * 100), 1),
                    'puntaje': round(float(r[3] or 0), 1)}

        variables_detalle = {}
        for cfg_key, (sistema_f, modelo_f, comps) in _VARS_CFG.items():
            q_base = db.query(Evaluacion).filter(
                Evaluacion.sistema == sistema_f,
                Evaluacion.modelo == modelo_f,
                Evaluacion.puntaje_100.isnot(None),
            )
            if anio:
                q_base = q_base.filter(Evaluacion.anio == anio)

            comp_rows = []
            for col_key, label, max_val in comps:
                col = getattr(Evaluacion, col_key, None)
                if col is None:
                    continue
                q_c = q_base.filter(col.isnot(None), col > 0)
                avg_raw = q_c.with_entities(func.avg(col)).scalar()
                n_c = q_c.with_entities(func.count(Evaluacion.id)).scalar() or 0
                if avg_raw is None or n_c == 0:
                    continue
                avg_pct = round(min(100.0, float(avg_raw) / max_val * 100), 1)

                top5 = q_c.with_entities(
                    Evaluacion.docente_nombre, Evaluacion.cedula,
                    func.avg(col).label('comp_v'),
                    func.avg(Evaluacion.puntaje_100).label('tot'),
                ).group_by(Evaluacion.docente_nombre, Evaluacion.cedula)\
                 .order_by(func.avg(col).desc()).limit(5).all()

                bot5 = q_c.with_entities(
                    Evaluacion.docente_nombre, Evaluacion.cedula,
                    func.avg(col).label('comp_v'),
                    func.avg(Evaluacion.puntaje_100).label('tot'),
                ).group_by(Evaluacion.docente_nombre, Evaluacion.cedula)\
                 .order_by(func.avg(col).asc()).limit(5).all()

                comp_rows.append({
                    'label': label, 'key': col_key,
                    'avg_pct': avg_pct, 'n': n_c,
                    'top5': [_teacher_fmt(r, max_val) for r in top5],
                    'bot5': [_teacher_fmt(r, max_val) for r in bot5],
                })

            comp_rows.sort(key=lambda x: x['avg_pct'], reverse=True)
            variables_detalle[cfg_key] = comp_rows

        return {
            'meipa':              meipa_overall,
            '360':                tres60_overall,
            'por_modelo_360':     por_modelo_360,
            'tendencia_meipa':    trend('meipa'),
            'tendencia_360':      trend('360'),
            'tendencia_periodos_meipa': trend_periodos('meipa'),
            'tendencia_periodos_360':  trend_periodos('360'),
            'por_modelo_por_periodo':  por_modelo_por_periodo_360(),
            'genero_por_periodo':      genero_por_periodo,
            'edad_por_periodo':        edad_por_periodo,
            'antiguedad_por_periodo':  antiguedad_por_periodo,
            'por_facultad':       por_facultad,
            'por_genero':         por_genero,
            'por_edad':           por_edad,
            'por_antiguedad':     por_antiguedad,
            'genero_edad':        genero_edad,
            'genero_antiguedad':  genero_antiguedad,
            'mejores_peores':     mejores_peores,
            'estadisticas':       estadisticas,
            'variables_detalle':  variables_detalle,
        }

    def get_ranking_docentes(self, db: Session, modelo: str = None, anio: int = None,
                              limit: int = 1000, sistema: str = None):
        q = _base_q(db, modelo, anio, sistema)
        ranking = q.with_entities(
            Evaluacion.docente_nombre,
            Evaluacion.facultad,
            Evaluacion.periodo,
            Evaluacion.anio,
            Evaluacion.modelo,
            func.avg(Evaluacion.puntaje_100).label('puntaje_100'),
            func.avg(Evaluacion.promedio).label('promedio'),
            func.avg(Evaluacion.het_estudiantil).label('het_estudiantil'),
            func.avg(Evaluacion.eval_pares).label('eval_pares'),
            func.avg(Evaluacion.aula_virtual).label('aula_virtual'),
            func.avg(Evaluacion.autoevaluacion).label('autoevaluacion'),
            func.avg(Evaluacion.comp_auto).label('comp_auto'),
            func.avg(Evaluacion.comp_pares).label('comp_pares'),
            func.avg(Evaluacion.comp_hetero_dir).label('comp_hetero_dir'),
            func.avg(Evaluacion.comp_hetero_est).label('comp_hetero_est'),
            Evaluacion.nivel_desempeno,
            Evaluacion.cedula,
            Evaluacion.sistema,
        ).group_by(Evaluacion.docente_nombre, Evaluacion.facultad, Evaluacion.modelo)\
         .order_by(func.avg(Evaluacion.puntaje_100).desc())\
         .limit(limit).all()

        result = [{
            'nombre':          r[0],
            'facultad':        r[1],
            'periodo':         r[2],
            'anio':            r[3],
            'modelo':          r[4],
            'puntaje_100':     round(r[5] or 0, 2),
            'promedio':        round(r[6] or 0, 2),
            'het_estudiantil': round(r[7] or 0, 2),
            'eval_pares':      round(r[8] or 0, 2),
            'aula_virtual':    round(r[9] or 0, 2),
            'autoevaluacion':  round(r[10] or 0, 2),
            'comp_auto':       round(r[11] or 0, 2),
            'comp_pares':      round(r[12] or 0, 2),
            'comp_hetero_dir': round(r[13] or 0, 2),
            'comp_hetero_est': round(r[14] or 0, 2),
            'nivel':           r[15] or 'Sin datos',
            'cedula':          r[16] or '',
            'sistema':         r[17] or '',
            'fecha_ingreso':   None,
        } for r in ranking]

        # Enriquecer con fecha_ingreso desde personal_periodo (más reciente por cédula)
        cedulas = [r['cedula'] for r in result if r['cedula']]
        if cedulas:
            fi_rows = (
                db.query(PersonalPeriodo.cedula, PersonalPeriodo.fecha_ingreso)
                .filter(
                    PersonalPeriodo.cedula.in_(cedulas),
                    PersonalPeriodo.fecha_ingreso.isnot(None),
                )
                .order_by(PersonalPeriodo.periodo_codigo.desc())
                .all()
            )
            fi_map: dict = {}
            for ced, fi in fi_rows:
                if ced not in fi_map:
                    fi_map[ced] = fi.isoformat() if fi else None
            for r in result:
                r['fecha_ingreso'] = fi_map.get(r['cedula'])

        return result

    def get_todos_docentes(self, db: Session, anio: int = None, modelo: str = None, sistema: str = None) -> list:
        """All teachers grouped by (cedula, sistema, modelo) with per-component normalized %."""
        _COMP_CFG: dict = {
            ('360', 'docencia'):     [('het_estudiantil',50),('eval_pares',20),('aula_virtual',10),('autoevaluacion',20)],
            ('360', 'abp'):          [('het_estudiantil',50),('eval_pares',20),('aula_virtual',10),('autoevaluacion',20)],
            ('360', 'tecnologado'):  [('het_estudiantil',50),('eval_pares',20),('aula_virtual',10),('autoevaluacion',20)],
            ('360', 'posgrado'):     [('het_estudiantil',60),('autoevaluacion',30),('aula_virtual',10)],
            ('360', 'vinculacion'):  [('comp_hetero_est',100),('comp_hetero_dir',100),('comp_auto',100)],
            ('360', 'investigacion'):[('comp_hetero_dir',100),('comp_pares',100),('comp_hetero_est',100),('comp_auto',100)],
            ('360', 'gestion'):      [('comp_hetero_dir',100),('comp_hetero_est',100),('comp_auto',100)],
            ('360', 'administrativo'):[('comp_hetero_dir',100),('comp_hetero_est',100),('comp_auto',100)],
            ('meipa', 'docencia'):   [('comp_hetero_est',100),('comp_hetero_dir',100),('comp_pares',100),('comp_auto',100)],
        }
        _COMP_LABELS: dict = {
            'het_estudiantil': 'Het. Estudiantil',
            'eval_pares':      'Eval. Pares',
            'aula_virtual':    'Aula Virtual / CEV',
            'autoevaluacion':  'Autoevaluación',
            'comp_hetero_est': 'Het. Estudiantil',
            'comp_hetero_dir': 'Het. Directivo',
            'comp_auto':       'Autoevaluación',
            'comp_pares':      'Coevaluación Par',
        }
        _COMP_LABELS_360: dict = {
            ('360', 'vinculacion',  'comp_hetero_est'): 'Het. Estudiantil',
            ('360', 'vinculacion',  'comp_hetero_dir'): 'Het. Dir. Académico',
            ('360', 'investigacion','comp_hetero_dir'): 'Het. Dir. Investigación',
            ('360', 'investigacion','comp_hetero_est'): 'Het. Decano / Coord.',
            ('360', 'investigacion','comp_pares'):      'Coevaluación Par',
            ('360', 'gestion',      'comp_hetero_dir'): 'Coevalúa. Directivo',
            ('360', 'gestion',      'comp_hetero_est'): 'Het. Docentes',
            ('meipa','docencia',    'comp_hetero_est'): 'Het. Estudiantil',
            ('meipa','docencia',    'comp_hetero_dir'): 'Coord. → Docente',
            ('meipa','docencia',    'comp_pares'):      'Eval. Pares',
        }

        q = db.query(Evaluacion).filter(
            Evaluacion.puntaje_100.isnot(None),
            Evaluacion.puntaje_100 > 0,
        )
        if anio:
            q = q.filter(Evaluacion.anio == anio)
        if modelo:
            q = q.filter(Evaluacion.modelo == modelo)
        if sistema:
            q = q.filter(Evaluacion.sistema == sistema)

        from collections import defaultdict
        groups: dict = defaultdict(list)
        for rec in q.all():
            key = (rec.cedula or rec.docente_nombre, rec.sistema, rec.modelo)
            groups[key].append(rec)

        result = []
        for (ced, sis, mod), recs in groups.items():
            nombre = next((r.docente_nombre for r in recs if r.docente_nombre and not r.docente_nombre.startswith('CED-')), None) \
                     or next((r.docente_nombre for r in recs if r.docente_nombre), f'CED-{ced}')
            facultad = next((r.facultad for r in recs if r.facultad), '')
            valid_niveles = ('Excelente', 'Bueno', 'Regular', 'Deficiente')
            nivel = next((r.nivel_desempeno for r in recs if r.nivel_desempeno in valid_niveles), 'Sin datos')
            puntaje = round(sum(r.puntaje_100 for r in recs) / len(recs), 1)

            cfg = _COMP_CFG.get((sis, mod), [])
            componentes = []
            for col_key, max_val in cfg:
                vals = [getattr(r, col_key) for r in recs if (getattr(r, col_key) or 0) > 0]
                if not vals:
                    continue
                avg_val = sum(vals) / len(vals)
                pct = round(min(100.0, avg_val / max_val * 100), 1)
                label = _COMP_LABELS_360.get((sis, mod, col_key)) or _COMP_LABELS.get(col_key, col_key)
                componentes.append({'label': label, 'pct': pct})

            componentes.sort(key=lambda x: x['pct'], reverse=True)
            result.append({
                'nombre':      nombre,
                'cedula':      ced or '',
                'sistema':     sis or '',
                'modelo':      mod or '',
                'facultad':    facultad,
                'puntaje':     puntaje,
                'nivel':       nivel,
                'componentes': componentes,
                'fecha_ingreso': None,
            })

        result.sort(key=lambda x: x['puntaje'], reverse=True)

        # Enriquecer con fecha_ingreso
        cedulas = [r['cedula'] for r in result if r['cedula']]
        if cedulas:
            fi_rows = (
                db.query(PersonalPeriodo.cedula, PersonalPeriodo.fecha_ingreso)
                .filter(
                    PersonalPeriodo.cedula.in_(cedulas),
                    PersonalPeriodo.fecha_ingreso.isnot(None),
                )
                .order_by(PersonalPeriodo.periodo_codigo.desc())
                .all()
            )
            fi_map: dict = {}
            for ced2, fi in fi_rows:
                if ced2 not in fi_map:
                    fi_map[ced2] = fi.isoformat() if fi else None
            for r in result:
                r['fecha_ingreso'] = fi_map.get(r['cedula'])

        return result

    def get_competencias_docente(self, db: Session, cedula: str) -> dict:
        """Desglose de competencias por docente a partir de RespuestaRaw (360°) y PuntajeFinal (MEIPA)."""
        from app.models.respuesta import RespuestaRaw
        from app.models.puntaje import PuntajeFinal
        from app.models.instrumento import Instrumento

        # Mapa instrumento code → descripción
        instr_map = {r.cod: r.descripcion for r in db.query(Instrumento).all()}

        # ── 360°: competencias desde RespuestaRaw ────────────────────────────
        rows_360 = (
            db.query(
                RespuestaRaw.competencia,
                RespuestaRaw.cod_instrumento,
                RespuestaRaw.periodo_codigo,
                func.avg(RespuestaRaw.calificacion).label('avg_cal'),
                func.count(RespuestaRaw.id).label('n'),
            )
            .filter(
                RespuestaRaw.cedula_evaluado == cedula,
                RespuestaRaw.competencia.isnot(None),
                RespuestaRaw.competencia != '',
                RespuestaRaw.calificacion.isnot(None),
            )
            .group_by(
                RespuestaRaw.competencia,
                RespuestaRaw.cod_instrumento,
                RespuestaRaw.periodo_codigo,
            )
            .order_by(RespuestaRaw.periodo_codigo.desc(), func.avg(RespuestaRaw.calificacion).desc())
            .all()
        )

        competencias_360 = [
            {
                'competencia':    comp,
                'instrumento':    instr_map.get(cod_inst, f'Instrumento {cod_inst}'),
                'cod_instrumento': cod_inst,
                'periodo':        periodo,
                'pct':            round(min(100.0, float(avg_cal) / 4.0 * 100), 1),
                'n':              n,
            }
            for comp, cod_inst, periodo, avg_cal, n in rows_360
            if comp and avg_cal is not None
        ]

        # ── MEIPA: componentes desde PuntajeFinal ────────────────────────────
        _MEIPA_LABELS = {
            'comp_het_est': 'Heteroevaluación Estudiantil',
            'comp_auto':    'Autoevaluación',
            'comp_het_dir': 'Coordinador → Docente',
            'comp_pares':   'Evaluación de Pares',
        }
        meipa_rows = (
            db.query(PuntajeFinal)
            .filter(PuntajeFinal.cedula == cedula, PuntajeFinal.sistema == 'meipa')
            .order_by(PuntajeFinal.periodo_codigo.desc())
            .all()
        )
        competencias_meipa = []
        for pf in meipa_rows:
            for attr, label in _MEIPA_LABELS.items():
                val = getattr(pf, attr, None)
                if val is not None:
                    competencias_meipa.append({
                        'competencia':    label,
                        'instrumento':    'MEIPA — Evaluación Docente',
                        'cod_instrumento': 'meipa',
                        'periodo':        pf.periodo_codigo,
                        'pct':            round(float(val), 1),
                        'n':              1,
                    })

        return {
            '360':          competencias_360,
            'meipa':        competencias_meipa,
            'total_360':    len(competencias_360),
            'total_meipa':  len(competencias_meipa),
        }

    def get_docentes_criticos(self, db: Session, modelo: str = None, anio: int = None,
                               threshold: float = 3.5, sistema: str = None):
        q = _base_q(db, modelo, anio, sistema)
        threshold_100 = threshold / 5 * 100
        criticos = q.with_entities(
            Evaluacion.docente_nombre,
            Evaluacion.facultad,
            func.avg(Evaluacion.puntaje_100).label('puntaje_100'),
        ).group_by(Evaluacion.docente_nombre, Evaluacion.facultad)\
         .having(func.avg(Evaluacion.puntaje_100) < threshold_100)\
         .order_by(func.avg(Evaluacion.puntaje_100).asc()).all()
        return [{'nombre': r[0], 'facultad': r[1], 'puntaje_100': round(r[2], 2),
                 'promedio': round(r[2] / 100 * 5, 2)} for r in criticos]

    def get_tendencias(self, db: Session, modelo: str = None, sistema: str = None):
        q = db.query(Evaluacion)
        if modelo:
            q = q.filter(Evaluacion.modelo == modelo)
        if sistema:
            q = q.filter(Evaluacion.sistema == sistema)
        tendencias = q.with_entities(Evaluacion.anio, func.avg(Evaluacion.puntaje_100))\
            .filter(Evaluacion.anio != None)\
            .group_by(Evaluacion.anio)\
            .order_by(Evaluacion.anio).all()
        return [{'anio': t[0], 'puntaje_100': round(t[1], 2),
                 'promedio': round(t[1] / 100 * 5, 2)} for t in tendencias]

    def get_variables_kpis(self, db: Session, modelo: str = None, anio: int = None, sistema: str = None):
        q = _base_q(db, modelo, anio, sistema)
        if sistema == 'meipa':
            cfg = MEIPA_MODEL_CONFIG.get(modelo or 'docencia', MEIPA_MODEL_CONFIG['docencia'])
        else:
            cfg = MODEL_CONFIG.get(modelo or 'docencia', MODEL_CONFIG['docencia'])
        results = {}
        for col, peso in cfg['components']:
            col_attr = getattr(Evaluacion, col, None)
            if col_attr is None:
                continue
            avg_val = q.with_entities(func.avg(col_attr)).scalar() or 0
            n_val   = q.with_entities(func.count(Evaluacion.id)).filter(col_attr > 0).scalar() or 0
            results[col] = {'promedio': round(avg_val, 2), 'peso': peso, 'n_docentes': n_val}
        sorted_r = sorted(results.items(), key=lambda x: x[1]['promedio'])
        return {
            'componentes': results,
            'mas_baja': sorted_r[0] if sorted_r else None,
            'mas_alta':  sorted_r[-1] if sorted_r else None,
        }

    def get_demograficos(self, db: Session, modelo: str = None, anio: int = None, sistema: str = None):
        q = _base_q(db, modelo, anio, sistema)
        sexo_raw = q.with_entities(Evaluacion.sexo, func.count(Evaluacion.id)).group_by(Evaluacion.sexo).all()
        _GN = {'mujer':'Mujer','femenino':'Mujer','f':'Mujer','hombre':'Hombre','masculino':'Hombre','m':'Hombre'}
        _sex_merged: dict = {}
        for s, c in sexo_raw:
            key = _GN.get(str(s or '').lower().strip(), str(s or 'No definido').strip())
            _sex_merged[key] = _sex_merged.get(key, 0) + (c or 0)
        sexo_dist = list(_sex_merged.items())
        edades = [e[0] for e in q.with_entities(Evaluacion.edad).all() if e[0]]
        rangos = {
            '20-30': len([e for e in edades if 20 <= e <= 30]),
            '31-45': len([e for e in edades if 31 <= e <= 45]),
            '46-60': len([e for e in edades if 46 <= e <= 60]),
            '61+':   len([e for e in edades if e > 60]),
        }
        carrera_dist = q.with_entities(Evaluacion.carrera, func.count(Evaluacion.id))\
            .filter(Evaluacion.carrera != None).group_by(Evaluacion.carrera).all()
        nivel_dist = q.with_entities(Evaluacion.nivel_desempeno, func.count(Evaluacion.id))\
            .filter(Evaluacion.nivel_desempeno != None).group_by(Evaluacion.nivel_desempeno).all()
        return {
            'sexo':            dict(sexo_dist),
            'edad':            rangos,
            'carrera':         {c if c else 'Sin carrera': n for c, n in carrera_dist},
            'nivel_desempeno': {n if n else 'Sin datos': c for n, c in nivel_dist},
        }


kpi_service = KPIService()
