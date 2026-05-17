"""
migrate_to_evaluaciones.py
──────────────────────────
Pobla la tabla `evaluaciones` a partir de los datos ya procesados en:
  - puntajes_finales   (PuntajeFinal)
  - docentes           (Docente)
  - personal_periodo   (PersonalPeriodo)
  - periodos           (Periodo)

Ejecutar una sola vez (o cuando la tabla quede vacía):
    cd backend && python migrate_to_evaluaciones.py
"""

import sqlite3
from datetime import datetime

DB_PATH = "evaluacion.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Verificar cuántos registros hay
    cur.execute("SELECT COUNT(*) FROM puntajes_finales")
    total_pf = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM evaluaciones")
    total_ev = cur.fetchone()[0]
    print(f"puntajes_finales: {total_pf} rows | evaluaciones: {total_ev} rows")

    if total_pf == 0:
        print("No hay datos en puntajes_finales. Nada que migrar.")
        conn.close()
        return

    # Limpiar evaluaciones para re-poblar limpio
    print("Limpiando tabla evaluaciones...")
    cur.execute("DELETE FROM evaluaciones")

    # Traer todos los puntajes_finales con JOIN a docentes, personal_periodo y periodos
    cur.execute("""
        SELECT
            pf.id            AS pf_id,
            pf.cedula,
            pf.periodo_codigo,
            pf.modelo,
            pf.sistema,
            pf.comp_het_est,
            pf.comp_auto,
            pf.comp_pares,
            pf.comp_het_dir,
            pf.comp_cev,
            pf.puntaje_100,
            pf.nivel_desempeno,

            d.nombre_completo,
            d.genero,
            d.fecha_nacimiento,

            pp.facultad,
            pp.carrera,
            pp.funcion,
            pp.antiguedad_anos,
            pp.edad_en_periodo,

            p.anio,
            p.label_corto   AS periodo_label
        FROM puntajes_finales pf
        LEFT JOIN docentes d ON d.cedula = pf.cedula
        LEFT JOIN personal_periodo pp
               ON pp.cedula = pf.cedula AND pp.periodo_codigo = pf.periodo_codigo
        LEFT JOIN periodos p ON p.codigo = pf.periodo_codigo
        WHERE pf.puntaje_100 IS NOT NULL
    """)
    rows = cur.fetchall()
    print(f"Filas a migrar: {len(rows)}")

    now = datetime.utcnow().isoformat()
    inserted = 0

    for r in rows:
        sistema = r["sistema"] or ""
        modelo  = r["modelo"]  or "docencia"
        pf_id   = r["pf_id"]

        # ── Mapeo de componentes ─────────────────────────────────────────────
        # Para modelos 360 de docencia/abp/posgrado/tecnologado:
        #   het_estudiantil = comp_het_est  (originalmente sobre su peso)
        #   eval_pares      = comp_pares
        #   aula_virtual    = comp_cev
        #   autoevaluacion  = comp_auto
        #
        # Para vinculación/investigación/gestión/meipa y comp_* columns, se
        # usan los campos comp_hetero_* del modelo Evaluacion.

        het_estudiantil = r["comp_het_est"]
        eval_pares      = r["comp_pares"]
        aula_virtual    = r["comp_cev"]
        autoevaluacion  = r["comp_auto"]
        comp_auto       = r["comp_auto"]
        comp_pares      = r["comp_pares"]
        comp_hetero_dir = r["comp_het_dir"]
        comp_hetero_est = r["comp_het_est"]

        anio_raw = r["anio"]
        try:
            anio_int = int(anio_raw) if anio_raw else None
        except (ValueError, TypeError):
            anio_int = None

        cur.execute("""
            INSERT INTO evaluaciones (
                docente_nombre, facultad, periodo, sexo, edad,
                metodologia, puntualidad, dominio_tematico, interaccion,
                uso_tic, satisfaccion, promedio, observaciones,
                fecha_proceso, archivo_fuente,
                het_estudiantil, eval_pares, aula_virtual, autoevaluacion,
                puntaje_100, carrera, tiempo_servicio, nivel_estudio,
                grado, modalidad, nivel_desempeno, cedula,
                modelo, anio,
                comp_auto, comp_pares, comp_hetero_dir, comp_hetero_est,
                sistema, antiguedad_anos, funcion_docente
            ) VALUES (
                ?, ?, ?, ?, ?,
                NULL, NULL, NULL, NULL,
                NULL, NULL, NULL, NULL,
                ?, 'puntajes_finales',
                ?, ?, ?, ?,
                ?, ?, NULL, NULL,
                NULL, NULL, ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?
            )
        """, (
            r["nombre_completo"],           # docente_nombre
            r["facultad"],                   # facultad
            r["periodo_label"],              # periodo
            r["genero"],                     # sexo
            r["edad_en_periodo"],            # edad
            now,                             # fecha_proceso
            het_estudiantil,                 # het_estudiantil
            eval_pares,                      # eval_pares
            aula_virtual,                    # aula_virtual
            autoevaluacion,                  # autoevaluacion
            r["puntaje_100"],                # puntaje_100
            r["carrera"],                    # carrera
            r["nivel_desempeno"],            # nivel_desempeno
            r["cedula"],                     # cedula
            modelo,                          # modelo
            anio_int,                        # anio
            comp_auto,                       # comp_auto
            comp_pares,                      # comp_pares
            comp_hetero_dir,                 # comp_hetero_dir
            comp_hetero_est,                 # comp_hetero_est
            sistema,                         # sistema
            r["antiguedad_anos"],            # antiguedad_anos
            r["funcion"],                    # funcion_docente
        ))
        inserted += 1

    conn.commit()
    conn.close()
    print(f"✅ Migración completa: {inserted} registros insertados en evaluaciones.")


if __name__ == "__main__":
    main()
