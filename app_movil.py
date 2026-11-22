@ -0,0 +1,1112 @@
﻿import base64
import csv
import io
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

BASE_DIR = Path(r"C:\Users\nicolas\Documents\docente-agil\doc_engine")
if not BASE_DIR.exists():
    BASE_DIR = Path(__file__).resolve().parent

os.chdir(BASE_DIR)
load_dotenv(dotenv_path=BASE_DIR / ".env")

from generar_set4 import generar_set4

st.set_page_config(
    page_title="DocenteÁgil",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed",
)


def _inyectar_identidad_app():
    """Inyecta manifest PWA inline y estilos de aplicación móvil/escritorio."""
    manifest = {
        "name": "DocenteÁgil",
        "short_name": "DocenteÁgil",
        "start_url": ".",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#0f172a",
        "description": "Gestión docente: SET 4, Cuaderno de actuaciones, Actas, Informes, Asistencia y Calificación por curso.",
    }
    manifest_b64 = base64.b64encode(
        json.dumps(manifest, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")

    st.markdown(
        f"""
        <link rel="manifest" href="data:application/manifest+json;base64,{manifest_b64}">
        <meta name="theme-color" content="#0f172a">
        <meta name="apple-mobile-web-app-capable" content="yes">
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
        <meta name="apple-mobile-web-app-title" content="DocenteÁgil">
        <style>
            #MainMenu {{visibility: hidden;}}
            footer {{visibility: hidden;}}
            header[data-testid="stHeader"] {{
                background: transparent;
                height: 2.2rem;
            }}
            .block-container {{
                padding-top: 1rem;
                padding-bottom: 3rem;
                max-width: 720px;
            }}
            .app-header {{
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: #f8fafc;
                padding: 1.05rem 1.2rem;
                border-radius: 16px;
                margin-bottom: 0.9rem;
                border: 1px solid rgba(148, 163, 184, 0.2);
                box-shadow: 0 6px 18px rgba(15, 23, 42, 0.14);
            }}
            .app-header-top {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.75rem;
            }}
            .app-title {{
                font-size: 1.35rem;
                font-weight: 700;
                letter-spacing: -0.01em;
                margin: 0;
                line-height: 1.2;
            }}
            .app-badge {{
                background: rgba(56, 189, 248, 0.18);
                color: #7dd3fc;
                border: 1px solid rgba(125, 211, 252, 0.35);
                padding: 0.2rem 0.6rem;
                border-radius: 999px;
                font-size: 0.75rem;
                font-weight: 600;
                white-space: nowrap;
            }}
            .app-subtitle {{
                margin: 0.35rem 0 0 0;
                font-size: 0.85rem;
                color: #cbd5e1;
            }}
            .stTabs [data-baseweb="tab-list"] {{
                gap: 0.35rem;
                overflow-x: auto;
                padding-bottom: 0.25rem;
            }}
            .stTabs [data-baseweb="tab"] {{
                border-radius: 10px;
                padding: 0.45rem 0.75rem;
                font-weight: 600;
                white-space: nowrap;
            }}
            .stButton > button, .stDownloadButton > button {{
                min-height: 2.9rem;
                font-weight: 600;
                border-radius: 12px;
            }}
            div[data-testid="stMetric"] {{
                background-color: rgba(128, 128, 128, 0.08);
                border: 1px solid rgba(128, 128, 128, 0.14);
                padding: 0.6rem 0.8rem;
                border-radius: 12px;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


_inyectar_identidad_app()


@st.cache_resource
def obtener_cliente_supabase():
    url = ""
    key = ""
    try:
        if "SUPABASE_URL" in st.secrets:
            url = str(st.secrets["SUPABASE_URL"]).strip()
        if "SUPABASE_KEY" in st.secrets:
            key = str(st.secrets["SUPABASE_KEY"]).strip()
    except Exception:
        pass

    if not url:
        url = os.getenv("SUPABASE_URL", "").strip()
    if not key:
        key = os.getenv("SUPABASE_KEY", "").strip()

    if not url or not key:
        return None
    return create_client(url, key)


def ejecutar_seguro(accion, mensaje_error: str):
    try:
        return accion()
    except Exception as exc:
        st.error(f"{mensaje_error}: {exc}")
        return None


def nombre_archivo_seguro(texto: str) -> str:
    limpio = re.sub(r"[^\w\-]+", "_", (texto or "registro").strip().lower())
    return limpio.strip("_") or "registro"


def construir_csv(columnas: list[str], filas: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columnas, extrasaction="ignore")
    writer.writeheader()
    for fila in filas:
        writer.writerow(fila)
    return buffer.getvalue().encode("utf-8-sig")


def cargar_perfil_reciente(supabase):
    resp = ejecutar_seguro(
        lambda: supabase.table("perfil_docente")
        .select("*")
        .order("creado_en", desc=True)
        .limit(1)
        .execute(),
        "Error leyendo perfil_docente",
    )
    return resp.data[0] if (resp and resp.data) else None


def cargar_todas_planillas_set4(supabase, limite: int = 200):
    resp = ejecutar_seguro(
        lambda: supabase.table("planillas_set4")
        .select("*")
        .order("creado_en", desc=True)
        .limit(limite)
        .execute(),
        "Error leyendo planillas_set4",
    )
    return resp.data if (resp and resp.data) else []


def cargar_actuaciones(supabase, limite: int = 200):
    resp = ejecutar_seguro(
        lambda: supabase.table("cuaderno_actuaciones")
        .select("*")
        .order("creado_en", desc=True)
        .limit(limite)
        .execute(),
        "Error leyendo cuaderno_actuaciones",
    )
    return resp.data if (resp and resp.data) else []


def cargar_cursos(supabase):
    resp = ejecutar_seguro(
        lambda: supabase.table("cursos")
        .select("*")
        .order("creado_en", desc=False)
        .execute(),
        "Error leyendo cursos",
    )
    return resp.data if (resp and resp.data) else []


def cargar_estudiantes_curso(supabase, curso_id: str):
    resp = ejecutar_seguro(
        lambda: supabase.table("estudiantes")
        .select("*")
        .eq("curso_id", curso_id)
        .order("nombre_completo", desc=False)
        .execute(),
        "Error leyendo estudiantes del curso",
    )
    return resp.data if (resp and resp.data) else []


def cargar_asistencias_curso(supabase, curso_id: str, limite: int = 100):
    resp = ejecutar_seguro(
        lambda: supabase.table("asistencia_curso")
        .select("*")
        .eq("curso_id", curso_id)
        .order("creado_en", desc=True)
        .limit(limite)
        .execute(),
        "Error leyendo asistencia del curso",
    )
    return resp.data if (resp and resp.data) else []


def cargar_calificaciones_curso(supabase, curso_id: str, limite: int = 200):
    resp = ejecutar_seguro(
        lambda: supabase.table("calificaciones_curso")
        .select("*")
        .eq("curso_id", curso_id)
        .order("creado_en", desc=True)
        .limit(limite)
        .execute(),
        "Error leyendo calificaciones del curso",
    )
    return resp.data if (resp and resp.data) else []


def generar_y_archivar_set4(datos: dict, etiqueta_archivo: str = "SET_4_completada.docx") -> Path:
    carpeta_salida = BASE_DIR / "salida"
    carpeta_archivo = carpeta_salida / "historial_set4"
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    carpeta_archivo.mkdir(parents=True, exist_ok=True)

    try:
        ruta_docx = generar_set4(datos, etiqueta_archivo)
    except PermissionError:
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        ruta_docx = generar_set4(datos, f"SET_4_completada_{marca}.docx")

    sello = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug_per = nombre_archivo_seguro(datos.get("periodo", "periodo"))
    copia_hist = carpeta_archivo / f"SET4_{slug_per}_{sello}.docx"
    shutil.copy2(ruta_docx, copia_hist)

    archivo_json = carpeta_archivo / "archivo_set4.json"
    registros_json = []
    if archivo_json.exists():
        try:
            registros_json = json.loads(archivo_json.read_text(encoding="utf-8"))
        except Exception:
            registros_json = []

    registros_json.insert(
        0,
        {
            "guardado_en": datetime.now().isoformat(timespec="seconds"),
            "archivo_docx": copia_hist.name,
            "datos": datos,
        },
    )
    archivo_json.write_text(
        json.dumps(registros_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return ruta_docx


def combinar_datos_set4(perfil: dict, planilla: dict) -> dict:
    return {
        "periodo": planilla.get("periodo", ""),
        "apellido_nombre": perfil.get("apellido_nombre", ""),
        "cargo_titular": perfil.get("cargo_titular", ""),
        "escuela_num": perfil.get("escuela_num", ""),
        "distrito": perfil.get("distrito", ""),
        "cargo_actual": perfil.get("cargo_actual", ""),
        "organismo": perfil.get("organismo", ""),
        "desde_fecha": perfil.get("desde_fecha", ""),
        "titulos_docentes": perfil.get("titulos_docentes", ""),
        "otros_titulos": perfil.get("otros_titulos", ""),
        "estudios_actuales": perfil.get("estudios_actuales", ""),
        "obras_publicadas": perfil.get("obras_publicadas", ""),
        "comisiones_oficiales": perfil.get("comisiones_oficiales", ""),
        "actos_culturales": perfil.get("actos_culturales", ""),
        "iniciativa": perfil.get("iniciativa", ""),
        "perfeccionamiento": perfil.get("perfeccionamiento", ""),
        "asistencias": planilla.get("asistencias", 0),
        "inasist_enfermedad": planilla.get("inasist_enfermedad", 0),
        "inasist_privadas": planilla.get("inasist_privadas", 0),
        "inasist_otras": planilla.get("inasist_otras", 0),
        "inasist_injustificadas": planilla.get("inasist_injustificadas", 0),
        "lugar_fecha": planilla.get("lugar_fecha", ""),
    }


def bloque_selector_y_alta_curso(supabase, perfil, prefijo: str):
    cursos = cargar_cursos(supabase)
    curso_seleccionado = None

    if cursos:
        opciones = {
            f"{c['nombre']} ({c['institucion']})" if c.get("institucion") else c["nombre"]: c
            for c in cursos
        }
        etiqueta_elegida = st.selectbox(
            "Curso / Grupo activo",
            list(opciones.keys()),
            key=f"{prefijo}_select_curso",
        )
        curso_seleccionado = opciones[etiqueta_elegida]
    else:
        st.info("Todavía no hay cursos creados. Creá el primero acá abajo.")

    with st.expander("➕ Crear nuevo curso"):
        with st.form(f"{prefijo}_form_nuevo_curso"):
            nombre_curso = st.text_input("Nombre del curso / categoría (ej: 4° 1ª · Ed. Física)")
            institucion_curso = st.text_input("Escuela / CEF / Club (ej: E.E.S. N° 8)")
            horario_curso = st.text_input("Día / Turno / Horario (opcional)")
            crear_c = st.form_submit_button("Guardar curso", use_container_width=True)

        if crear_c:
            if not nombre_curso.strip():
                st.warning("Ingresá un nombre de curso.")
            else:
                res = ejecutar_seguro(
                    lambda: supabase.table("cursos")
                    .insert(
                        {
                            "perfil_id": perfil["id"] if perfil else None,
                            "nombre": nombre_curso.strip(),
                            "institucion": institucion_curso.strip(),
                            "turno_horario": horario_curso.strip(),
                        }
                    )
                    .execute(),
                    "No se pudo crear el curso",
                )
                if res:
                    st.success("Curso creado.")
                    st.rerun()

    return curso_seleccionado


def bloque_agregar_estudiantes(supabase, curso_id: str, prefijo: str):
    with st.expander("👥 Cargar estudiantes en este curso"):
        with st.form(f"{prefijo}_form_alumnos_{curso_id}"):
            lista_texto = st.text_area(
                "Nombres (uno por línea)",
                placeholder="Pérez, Juan\nGómez, María\nLópez, Lucas",
                height=110,
            )
            agregar_al = st.form_submit_button("Agregar estudiantes al curso", use_container_width=True)

        if agregar_al:
            nombres = [ln.strip() for ln in lista_texto.splitlines() if ln.strip()]
            if not nombres:
                st.warning("Escribí al menos un nombre.")
            else:
                filas = [{"curso_id": curso_id, "nombre_completo": n} for n in nombres]
                res = ejecutar_seguro(
                    lambda: supabase.table("estudiantes").insert(filas).execute(),
                    "No se pudieron agregar los estudiantes",
                )
                if res:
                    st.success(f"Se agregaron {len(filas)} estudiante(s) a este curso.")
                    st.rerun()


supabase = obtener_cliente_supabase()
if supabase is None:
    st.error("Falta configurar `SUPABASE_URL` o `SUPABASE_KEY` en el archivo `.env`.")
    st.stop()

perfil = cargar_perfil_reciente(supabase)
planillas_set4 = cargar_todas_planillas_set4(supabase)
ultima_planilla = planillas_set4[0] if planillas_set4 else {}

docente_etiqueta = (perfil or {}).get("apellido_nombre") or "Modo Docente"
organismo_etiqueta = (perfil or {}).get("organismo") or "Gestión Escolar y CEF"

st.markdown(
    f"""
    <div class="app-header">
        <div class="app-header-top">
            <h1 class="app-title">📋 DocenteÁgil</h1>
            <span class="app-badge">{docente_etiqueta}</span>
        </div>
        <p class="app-subtitle">{organismo_etiqueta} · SET 4 · Actuaciones · Actas · Informes · Cursos</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if not perfil:
    st.warning("Completá tus datos base en la pestaña **Perfil** para autocompletar planillas y documentos.")

tab_set4, tab_cuaderno, tab_actas, tab_informes, tab_asist, tab_calif, tab_perfil = st.tabs(
    [
        "📄 SET 4",
        "📓 Actuaciones",
        "⚖️ Actas",
        "📝 Informes",
        "✅ Asistencia",
        "🎯 Calificación",
        "👤 Perfil",
    ]
)

# 1. SET 4 + ARCHIVO HISTÓRICO
with tab_set4:
    with st.form("form_planilla_movil"):
        periodo = st.text_input(
            "Período",
            value=ultima_planilla.get("periodo") or "01/03/2026 al 30/11/2026",
        )
        asistencias = st.number_input(
            "14- Asistencias",
            min_value=0,
            step=1,
            value=int(ultima_planilla.get("asistencias") or 0),
        )
        st.markdown("**Inasistencias**")
        c1, c2 = st.columns(2)
        with c1:
            enfermedad = st.number_input(
                "Enfermedad",
                min_value=0,
                step=1,
                value=int(ultima_planilla.get("inasist_enfermedad") or 0),
            )
            privadas = st.number_input(
                "Causas privadas",
                min_value=0,
                step=1,
                value=int(ultima_planilla.get("inasist_privadas") or 0),
            )
        with c2:
            otras = st.number_input(
                "Otras causas",
                min_value=0,
                step=1,
                value=int(ultima_planilla.get("inasist_otras") or 0),
            )
            injustificadas = st.number_input(
                "Injustificadas",
                min_value=0,
                step=1,
                value=int(ultima_planilla.get("inasist_injustificadas") or 0),
            )

        total_inasist = int(enfermedad) + int(privadas) + int(otras) + int(injustificadas)
        st.metric("Suma total de inasistencias", total_inasist)

        lugar_fecha = st.text_input(
            "Lugar y fecha",
            value=ultima_planilla.get("lugar_fecha") or f"Chacabuco, {datetime.now().strftime('%d/%m/%Y')}",
        )
        guardar_y_generar = st.form_submit_button("💾 Guardar y generar Word", use_container_width=True)

    if guardar_y_generar:
        if not perfil:
            st.error("Primero guardá tu perfil docente en la pestaña **Perfil**.")
        else:
            registro = {
                "perfil_id": perfil["id"],
                "periodo": periodo.strip(),
                "asistencias": int(asistencias),
                "inasist_enfermedad": int(enfermedad),
                "inasist_privadas": int(privadas),
                "inasist_otras": int(otras),
                "inasist_injustificadas": int(injustificadas),
                "lugar_fecha": lugar_fecha.strip(),
                "estado": "generado",
            }
            res = ejecutar_seguro(
                lambda: supabase.table("planillas_set4").insert(registro).execute(),
                "No se pudo guardar en planillas_set4",
            )
            if res:
                datos_finales = combinar_datos_set4(perfil, registro)
                ruta_docx = generar_y_archivar_set4(datos_finales)
                st.success(f"Guardado, archivado y generado: `{ruta_docx.name}`")
                with open(ruta_docx, "rb") as archivo:
                    st.download_button(
                        label=f"⬇️ Descargar {ruta_docx.name}",
                        data=archivo.read(),
                        file_name=ruta_docx.name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )

    if planillas_set4:
        st.divider()
        st.markdown("### 📚 Archivo completo de SET 4")
        st.caption(f"Registros archivados: {len(planillas_set4)}")

        filas_archivo_set4 = []
        for p_item in planillas_set4:
            enf = int(p_item.get("inasist_enfermedad") or 0)
            priv = int(p_item.get("inasist_privadas") or 0)
            otr = int(p_item.get("inasist_otras") or 0)
            inj = int(p_item.get("inasist_injustificadas") or 0)
            filas_archivo_set4.append(
                {
                    "periodo": p_item.get("periodo", ""),
                    "asistencias": int(p_item.get("asistencias") or 0),
                    "enfermedad": enf,
                    "privadas": priv,
                    "otras": otr,
                    "injustificadas": inj,
                    "total_inasistencias": enf + priv + otr + inj,
                    "lugar_fecha": p_item.get("lugar_fecha", ""),
                    "estado": p_item.get("estado", ""),
                }
            )

        st.dataframe(filas_archivo_set4, use_container_width=True, hide_index=True)

        csv_set4 = construir_csv(
            [
                "periodo",
                "asistencias",
                "enfermedad",
                "privadas",
                "otras",
                "injustificadas",
                "total_inasistencias",
                "lugar_fecha",
                "estado",
            ],
            filas_archivo_set4,
        )
        st.download_button(
            label="⬇️ Exportar archivo SET 4 (.csv)",
            data=csv_set4,
            file_name="archivo_historico_set4.csv",
            mime="text/csv",
            use_container_width=True,
        )

        with st.expander("📄 Regenerar Word de un registro histórico"):
            for idx_p, item in enumerate(planillas_set4[:15]):
                etq = f"{item.get('periodo') or 'Sin período'} · Asist.: {item.get('asistencias', 0)} · {item.get('lugar_fecha') or ''}"
                if st.button(f"Generar .docx · {etq}", key=f"regen_set4_{item.get('id', idx_p)}", use_container_width=True):
                    if not perfil:
                        st.error("Falta perfil docente.")
                    else:
                        ruta_reg = generar_y_archivar_set4(combinar_datos_set4(perfil, item))
                        with open(ruta_reg, "rb") as f_reg:
                            st.download_button(
                                label=f"⬇️ Descargar {ruta_reg.name}",
                                data=f_reg.read(),
                                file_name=ruta_reg.name,
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"dl_regen_{item.get('id', idx_p)}",
                                use_container_width=True,
                            )

# 2. CUADERNO DE ACTUACIONES
with tab_cuaderno:
    inst_def = (perfil or {}).get("organismo") or ""
    with st.form("form_cuaderno_actuacion"):
        ca1, ca2 = st.columns(2)
        with ca1:
            fecha_act = st.text_input("Fecha", value=datetime.now().strftime("%d/%m/%Y"))
        with ca2:
            tipo_act = st.selectbox(
                "Tipo de actuación",
                [
                    "Intervención / Novedad diaria",
                    "Notificación / Citación",
                    "Entrevista / Diálogo",
                    "Derivación / Seguimiento",
                    "Disposición / Constancia",
                ],
            )
        inst_curso_act = st.text_input("Establecimiento / Curso / Espacio", value=inst_def)
        asunto_act = st.text_input("Asunto breve", placeholder="Ej: Notificación de salida / Novedad en patio / Seguimiento")
        detalle_act = st.text_area("Detalle de la actuación", height=95)
        resol_act = st.text_input("Resolución / Notificación / Firma", value="")
        guardar_act = st.form_submit_button("💾 Registrar en cuaderno", use_container_width=True)

    if guardar_act:
        if not asunto_act.strip() and not detalle_act.strip():
            st.warning("Completá el asunto o el detalle de la actuación.")
        else:
            payload_act = {
                "perfil_id": perfil["id"] if perfil else None,
                "fecha_actuacion": fecha_act.strip(),
                "institucion_curso": inst_curso_act.strip(),
                "tipo_actuacion": tipo_act,
                "asunto": asunto_act.strip(),
                "detalle": detalle_act.strip(),
                "resolucion_notificacion": resol_act.strip(),
            }
            res = ejecutar_seguro(
                lambda: supabase.table("cuaderno_actuaciones").insert(payload_act).execute(),
                "No se pudo guardar en cuaderno_actuaciones",
            )
            if res:
                st.success("Actuación asentada en el cuaderno.")

    actuaciones = cargar_actuaciones(supabase)
    if actuaciones:
        st.divider()
        st.markdown("### 🗂️ Registro del cuaderno")
        filtro_inst = st.text_input("Filtrar por institución / curso / palabra clave", value="", key="filtro_cuaderno")
        filtradas = (
            actuaciones
            if not filtro_inst.strip()
            else [
                a
                for a in actuaciones
                if filtro_inst.strip().lower()
                in f"{a.get('institucion_curso', '')} {a.get('tipo_actuacion', '')} {a.get('asunto', '')} {a.get('detalle', '')}".lower()
            ]
        )

        for act in filtradas:
            st.write(
                f"- **{act.get('fecha_actuacion', '')}** · *{act.get('tipo_actuacion', '')}* "
                f"({act.get('institucion_curso') or 'General'}): **{act.get('asunto') or 'Sin asunto'}** — {act.get('detalle', '')}"
                + (f" [Res.: {act['resolucion_notificacion']}]" if act.get("resolucion_notificacion") else "")
            )

        csv_act = construir_csv(
            [
                "fecha_actuacion",
                "institucion_curso",
                "tipo_actuacion",
                "asunto",
                "detalle",
                "resolucion_notificacion",
            ],
            filtradas,
        )
        st.download_button(
            label="⬇️ Exportar cuaderno de actuaciones (.csv)",
            data=csv_act,
            file_name=f"cuaderno_actuaciones_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

# 3. ACTAS
with tab_actas:
    docente_nombre = (perfil or {}).get("apellido_nombre") or "Docente a cargo"
    establecimiento_def = (perfil or {}).get("organismo") or ""
    with st.form("form_acta"):
        tipo_acta = st.selectbox(
            "Tipo de acta",
            [
                "Acta de incidente / accidente escolar",
                "Acta de salida / actividad en el entorno",
                "Acta de reunión / notificación institucional",
                "Otra acta",
            ],
        )
        establecimiento = st.text_input("Establecimiento / Dependencia", value=establecimiento_def)
        ca, cb = st.columns(2)
        with ca:
            fecha_hora = st.text_input("Fecha y hora", value=datetime.now().strftime("%d/%m/%Y %H:%M"))
        with cb:
            lugar = st.text_input("Lugar exacto", value="")
        involucrados = st.text_area("Personas involucradas / testigos", height=65)
        relato = st.text_area("Relato objetivo de los hechos", height=100)
        medidas = st.text_area("Medidas adoptadas / primeros auxilios / intervención", height=80)
        aviso = st.text_input("Aviso a familia / dirección / servicio médico", value="")
        guardar_acta = st.form_submit_button("💾 Guardar acta", use_container_width=True)

    if guardar_acta:
        payload_acta = {
            "perfil_id": perfil["id"] if perfil else None,
            "tipo_acta": tipo_acta,
            "establecimiento": establecimiento.strip(),
            "fecha_hora": fecha_hora.strip(),
            "lugar": lugar.strip(),
            "personas_involucradas": involucrados.strip(),
            "relato_hechos": relato.strip(),
            "medidas_adoptadas": medidas.strip(),
            "intervencion_medica_familia": aviso.strip(),
        }
        ejecutar_seguro(
            lambda: supabase.table("actas_escolares").insert(payload_acta).execute(),
            "No se pudo guardar en actas_escolares",
        )
        texto_acta = (
            f"{tipo_acta.upper()}\n"
            f"Fecha y hora: {payload_acta['fecha_hora']}\n"
            f"Establecimiento: {payload_acta['establecimiento']}\n"
            f"Lugar: {payload_acta['lugar']}\n"
            f"Docente interviniente: {docente_nombre}\n"
            f"Involucrados / testigos: {payload_acta['personas_involucradas']}\n\n"
            f"HECHOS:\n{payload_acta['relato_hechos']}\n\n"
            f"MEDIDAS ADOPTADAS:\n{payload_acta['medidas_adoptadas']}\n\n"
            f"AVISO / INTERVENCIÓN: {payload_acta['intervencion_medica_familia']}\n"
        )
        st.success("Acta registrada.")
        st.download_button(
            "⬇️ Descargar borrador de acta (.txt)",
            data=texto_acta.encode("utf-8"),
            file_name=f"acta_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

# 4. INFORMES
with tab_informes:
    with st.form("form_informe"):
        tipo_informe = st.selectbox(
            "Tipo de informe",
            [
                "Informe pedagógico / seguimiento",
                "Informe de actividad / jornada / salida",
                "Informe de situación / observación",
            ],
        )
        ci1, ci2 = st.columns(2)
        with ci1:
            curso_grupo = st.text_input("Curso / División / Categoría", value="")
        with ci2:
            periodo_inf = st.text_input("Período / Fecha", value=datetime.now().strftime("%d/%m/%Y"))
        sintesis = st.text_area("Síntesis general de desempeño", height=85)
        fortalezas = st.text_area("Fortalezas / logros observados", height=70)
        a_fortalecer = st.text_area("Aspectos a fortalecer / propuestas", height=70)
        obs_inf = st.text_input("Observaciones adicionales", value="")
        guardar_informe = st.form_submit_button("💾 Guardar informe", use_container_width=True)

    if guardar_informe:
        payload_inf = {
            "perfil_id": perfil["id"] if perfil else None,
            "tipo_informe": tipo_informe,
            "curso_grupo": curso_grupo.strip(),
            "periodo": periodo_inf.strip(),
            "sintesis_desempeno": sintesis.strip(),
            "fortalezas": fortalezas.strip(),
            "aspectos_a_fortalecer": a_fortalecer.strip(),
            "observaciones": obs_inf.strip(),
        }
        ejecutar_seguro(
            lambda: supabase.table("informes_docentes").insert(payload_inf).execute(),
            "No se pudo guardar en informes_docentes",
        )
        texto_inf = (
            f"{payload_inf['tipo_informe'].upper()}\n"
            f"Grupo / Curso: {payload_inf['curso_grupo']} | Período: {payload_inf['periodo']}\n\n"
            f"Síntesis:\n{payload_inf['sintesis_desempeno']}\n\n"
            f"Fortalezas:\n{payload_inf['fortalezas']}\n\n"
            f"Aspectos a fortalecer:\n{payload_inf['aspectos_a_fortalecer']}\n\n"
            f"Observaciones: {payload_inf['observaciones']}\n"
        )
        st.success("Informe guardado.")
        st.download_button(
            "⬇️ Descargar informe (.txt)",
            data=texto_inf.encode("utf-8"),
            file_name=f"informe_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

# 5. ASISTENCIA POR CURSO + RESUMEN + CSV
with tab_asist:
    curso_asist = bloque_selector_y_alta_curso(supabase, perfil, "asist")
    if curso_asist:
        curso_id = curso_asist["id"]
        slug_curso_a = nombre_archivo_seguro(curso_asist["nombre"])
        bloque_agregar_estudiantes(supabase, curso_id, "asist")
        alumnos_curso = cargar_estudiantes_curso(supabase, curso_id)

        fecha_clase = st.text_input(
            "Fecha de clase",
            value=datetime.now().strftime("%d/%m/%Y"),
            key=f"fecha_asist_{curso_id}",
        )

        if alumnos_curso:
            st.caption(f"Lista de **{curso_asist['nombre']}** ({len(alumnos_curso)} estudiantes)")
            estados = {}
            for al in alumnos_curso:
                estados[al["id"]] = st.radio(
                    al["nombre_completo"],
                    ["Presente", "Ausente", "Tarde"],
                    horizontal=True,
                    key=f"est_asist_{curso_id}_{al['id']}",
                )
            novedades_asist = st.text_input("Novedades / justificativos", key=f"nov_asist_{curso_id}")
            if st.button("💾 Guardar asistencia de este curso", key=f"btn_save_asist_{curso_id}", use_container_width=True):
                vals = list(estados.values())
                cant_p = sum(1 for v in vals if v == "Presente")
                cant_a = sum(1 for v in vals if v == "Ausente")
                cant_t = sum(1 for v in vals if v == "Tarde")
                aus_nombres = [
                    al["nombre_completo"]
                    for al in alumnos_curso
                    if estados.get(al["id"]) in ("Ausente", "Tarde")
                ]
                res = ejecutar_seguro(
                    lambda: supabase.table("asistencia_curso")
                    .insert(
                        {
                            "curso_id": curso_id,
                            "fecha_clase": fecha_clase.strip(),
                            "presentes": cant_p,
                            "ausentes": cant_a,
                            "tarde": cant_t,
                            "ausentes_detalle": ", ".join(aus_nombres),
                            "novedades": novedades_asist.strip(),
                        }
                    )
                    .execute(),
                    "No se pudo guardar asistencia del curso",
                )
                if res:
                    st.success(f"Asistencia guardada para {curso_asist['nombre']}: {cant_p} P · {cant_a} A · {cant_t} T.")
                    st.rerun()
        else:
            st.caption("Sin lista cargada todavía: podés registrar el parte numérico directo de este curso.")
            with st.form(f"form_asist_rapida_{curso_id}"):
                cp1, cp2, cp3 = st.columns(3)
                with cp1:
                    p_rap = st.number_input("Presentes", min_value=0, step=1, value=0)
                with cp2:
                    a_rap = st.number_input("Ausentes", min_value=0, step=1, value=0)
                with cp3:
                    t_rap = st.number_input("Tarde", min_value=0, step=1, value=0)
                nov_rap = st.text_input("Novedades / observaciones")
                g_rap = st.form_submit_button("💾 Guardar asistencia", use_container_width=True)
            if g_rap:
                res = ejecutar_seguro(
                    lambda: supabase.table("asistencia_curso")
                    .insert(
                        {
                            "curso_id": curso_id,
                            "fecha_clase": fecha_clase.strip(),
                            "presentes": int(p_rap),
                            "ausentes": int(a_rap),
                            "tarde": int(t_rap),
                            "novedades": nov_rap.strip(),
                        }
                    )
                    .execute(),
                    "No se pudo guardar asistencia",
                )
                if res:
                    st.success("Asistencia guardada.")
                    st.rerun()

        hist_asist = cargar_asistencias_curso(supabase, curso_id)
        if hist_asist:
            st.divider()
            st.markdown(f"### 📊 Planilla resumen · {curso_asist['nombre']}")
            sum_p = sum(int(h.get("presentes", 0) or 0) for h in hist_asist)
            sum_a = sum(int(h.get("ausentes", 0) or 0) for h in hist_asist)
            sum_t = sum(int(h.get("tarde", 0) or 0) for h in hist_asist)
            tot_marcas = sum_p + sum_a + sum_t
            pct_gral = (sum_p / tot_marcas * 100) if tot_marcas > 0 else 0.0

            rm1, rm2, rm3 = st.columns(3)
            rm1.metric("Clases cargadas", len(hist_asist))
            rm2.metric("Total presentes", sum_p)
            rm3.metric("% Asistencia", f"{pct_gral:.1f}%")

            filas_resumen_asist = []
            for h in reversed(hist_asist):
                p_v = int(h.get("presentes", 0) or 0)
                a_v = int(h.get("ausentes", 0) or 0)
                t_v = int(h.get("tarde", 0) or 0)
                tot_v = p_v + a_v + t_v
                pct_v = f"{(p_v / tot_v * 100):.1f}%" if tot_v > 0 else "0.0%"
                filas_resumen_asist.append(
                    {
                        "curso": curso_asist["nombre"],
                        "fecha": h.get("fecha_clase", ""),
                        "presentes": p_v,
                        "ausentes": a_v,
                        "tarde": t_v,
                        "pct_asistencia": pct_v,
                        "ausentes_tarde_detalle": h.get("ausentes_detalle", ""),
                        "novedades": h.get("novedades", ""),
                    }
                )

            st.dataframe(filas_resumen_asist, use_container_width=True, hide_index=True)

            csv_asist = construir_csv(
                [
                    "curso",
                    "fecha",
                    "presentes",
                    "ausentes",
                    "tarde",
                    "pct_asistencia",
                    "ausentes_tarde_detalle",
                    "novedades",
                ],
                filas_resumen_asist,
            )
            st.download_button(
                label=f"⬇️ Exportar asistencia CSV ({slug_curso_a}.csv)",
                data=csv_asist,
                file_name=f"asistencia_{slug_curso_a}.csv",
                mime="text/csv",
                key=f"dl_csv_asist_{curso_id}",
                use_container_width=True,
            )

# 6. CALIFICACIÓN POR CURSO + PLANILLA CIERRE CUATRIMESTRE + CSV
with tab_calif:
    curso_calif = bloque_selector_y_alta_curso(supabase, perfil, "calif")
    if curso_calif:
        curso_id = curso_calif["id"]
        slug_curso_c = nombre_archivo_seguro(curso_calif["nombre"])
        bloque_agregar_estudiantes(supabase, curso_id, "calif")
        alumnos_calif = cargar_estudiantes_curso(supabase, curso_id)

        with st.form(f"form_calif_{curso_id}"):
            if alumnos_calif:
                mapa_al = {a["nombre_completo"]: a["id"] for a in alumnos_calif}
                nombre_elegido = st.selectbox("Estudiante de este curso", list(mapa_al.keys()))
                est_id = mapa_al[nombre_elegido]
            else:
                nombre_elegido = st.text_input("Estudiante o grupo de este curso", value="")
                est_id = None

            instancia = st.text_input("Instancia / Cuatrimestre", value="1.er Cuatrimestre")
            st.caption("Criterios numéricos (0 a 10)")
            k1, k2, k3 = st.columns(3)
            with k1:
                crit1 = st.number_input("Criterio 1", min_value=0.0, max_value=10.0, step=0.5, value=7.0)
            with k2:
                crit2 = st.number_input("Criterio 2", min_value=0.0, max_value=10.0, step=0.5, value=7.0)
            with k3:
                crit3 = st.number_input("Criterio 3", min_value=0.0, max_value=10.0, step=0.5, value=7.0)

            nota_calc = round((float(crit1) + float(crit2) + float(crit3)) / 3.0, 2)
            st.metric("Promedio / Nota final", nota_calc)
            fundamentacion = st.text_area("Fundamentación / devolución", height=75)
            guardar_calif = st.form_submit_button("💾 Guardar calificación en este curso", use_container_width=True)

        if guardar_calif:
            if not nombre_elegido.strip():
                st.warning("Indicá o seleccioná un estudiante.")
            else:
                res = ejecutar_seguro(
                    lambda: supabase.table("calificaciones_curso")
                    .insert(
                        {
                            "curso_id": curso_id,
                            "estudiante_id": est_id,
                            "estudiante_nombre": nombre_elegido.strip(),
                            "instancia": instancia.strip(),
                            "criterio_1": float(crit1),
                            "criterio_2": float(crit2),
                            "criterio_3": float(crit3),
                            "nota_final": nota_calc,
                            "fundamentacion": fundamentacion.strip(),
                        }
                    )
                    .execute(),
                    "No se pudo guardar calificación",
                )
                if res:
                    st.success(f"Calificación guardada para {nombre_elegido} ({nota_calc}).")
                    st.rerun()

        hist_calif = cargar_calificaciones_curso(supabase, curso_id)
        if hist_calif:
            st.divider()
            st.markdown(f"### 📑 Planilla resumen para cierre · {curso_calif['nombre']}")
            instancias_disp = sorted({str(r.get("instancia") or "").strip() for r in hist_calif if str(r.get("instancia") or "").strip()})
            filtro_inst = st.selectbox(
                "Filtrar por instancia / cuatrimestre",
                ["Todas las instancias"] + instancias_disp,
                key=f"filtro_inst_{curso_id}",
            )

            registros_filtrados = (
                hist_calif
                if filtro_inst == "Todas las instancias"
                else [r for r in hist_calif if str(r.get("instancia") or "").strip() == filtro_inst]
            )

            if registros_filtrados:
                notas_num = [float(r.get("nota_final") or 0) for r in registros_filtrados]
                prom_curso = round(sum(notas_num) / len(notas_num), 2)
                cm1, cm2 = st.columns(2)
                cm1.metric("Registros en planilla", len(registros_filtrados))
                cm2.metric("Promedio del curso", prom_curso)

                filas_planilla_cierre = [
                    {
                        "curso": curso_calif["nombre"],
                        "estudiante": r.get("estudiante_nombre", ""),
                        "instancia": r.get("instancia", ""),
                        "criterio_1": r.get("criterio_1", 0),
                        "criterio_2": r.get("criterio_2", 0),
                        "criterio_3": r.get("criterio_3", 0),
                        "nota_final": r.get("nota_final", 0),
                        "fundamentacion": r.get("fundamentacion", ""),
                    }
                    for r in registros_filtrados
                ]

                st.dataframe(filas_planilla_cierre, use_container_width=True, hide_index=True)

                csv_calif = construir_csv(
                    [
                        "curso",
                        "estudiante",
                        "instancia",
                        "criterio_1",
                        "criterio_2",
                        "criterio_3",
                        "nota_final",
                        "fundamentacion",
                    ],
                    filas_planilla_cierre,
                )
                st.download_button(
                    label=f"⬇️ Exportar planilla CSV ({slug_curso_c}.csv)",
                    data=csv_calif,
                    file_name=f"calificaciones_{slug_curso_c}.csv",
                    mime="text/csv",
                    key=f"dl_csv_calif_{curso_id}",
                    use_container_width=True,
                )

# 7. PERFIL
with tab_perfil:
    st.caption("Próxima etapa planificada: módulo de apoyo para trámites jubilatorios (como Anexo 354) con tus datos de trayectoria y cargos.")
    p = perfil or {}
    with st.form("form_perfil_movil"):
        apellido_nombre = st.text_input("1- Apellido y Nombre", value=p.get("apellido_nombre") or "")
        cargo_titular = st.text_input("2- Cargo del que es titular", value=p.get("cargo_titular") or "")
        c_esc, c_dist = st.columns(2)
        with c_esc:
            escuela_num = st.text_input("Escuela Nº", value=p.get("escuela_num") or "")
        with c_dist:
            distrito = st.text_input("Distrito", value=p.get("distrito") or "Chacabuco")
        cargo_actual = st.text_input("3- Cargo que desempeña actualmente", value=p.get("cargo_actual") or "")
        organismo = st.text_input("4- Organismo / Repartición", value=p.get("organismo") or "")
        desde_fecha = st.text_input("5- ¿Desde qué fecha?", value=p.get("desde_fecha") or "")
        titulos_docentes = st.text_area("6- Títulos docentes que posee", value=p.get("titulos_docentes") or "", height=70)
        otros_titulos = st.text_area("7- Otros títulos o estudios", value=p.get("otros_titulos") or "", height=70)
        estudios_actuales = st.text_area("8- Estudios o trabajos actuales", value=p.get("estudios_actuales") or "", height=70)
        obras_publicadas = st.text_input("9- Obras publicadas o ejecutadas", value=p.get("obras_publicadas") or "—")
        comisiones_oficiales = st.text_input("10- Comisiones oficiales", value=p.get("comisiones_oficiales") or "—")
        actos_culturales = st.text_input("11- Actos culturales", value=p.get("actos_culturales") or "")
        iniciativa = st.text_input("12- Iniciativa", value=p.get("iniciativa") or "")
        perfeccionamiento = st.text_input("13- Perfeccionamiento docente", value=p.get("perfeccionamiento") or "")
        guardar_perfil = st.form_submit_button("💾 Guardar perfil en Supabase", use_container_width=True)

    if guardar_perfil:
        nuevo_perfil = {
            "apellido_nombre": apellido_nombre.strip(),
            "cargo_titular": cargo_titular.strip(),
            "escuela_num": escuela_num.strip(),
            "distrito": distrito.strip(),
            "cargo_actual": cargo_actual.strip(),
            "organismo": organismo.strip(),
            "desde_fecha": desde_fecha.strip(),
            "titulos_docentes": titulos_docentes.strip(),
            "otros_titulos": otros_titulos.strip(),
            "estudios_actuales": estudios_actuales.strip(),
            "obras_publicadas": obras_publicadas.strip(),
            "comisiones_oficiales": comisiones_oficiales.strip(),
            "actos_culturales": actos_culturales.strip(),
            "iniciativa": iniciativa.strip(),
            "perfeccionamiento": perfeccionamiento.strip(),
        }
        res = ejecutar_seguro(
            lambda: supabase.table("perfil_docente").insert(nuevo_perfil).execute(),
            "No se pudo guardar el perfil",
        )
        if res:
            st.success("Perfil actualizado en Supabase.")
