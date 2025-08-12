import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
import re
from difflib import SequenceMatcher

# Configuración inicial de la app
st.set_page_config(page_title="Acuerdos Aucca", layout="wide")

# Aplicar estilos personalizados inspirados en la naturaleza
eco_css = """
<style>
body {
    background-color: #FAF9F6;
    color: #3E4E2C;
    font-family: "Georgia", serif;
}
[data-testid="stAppViewContainer"] > .main {
    background-color: #FAF9F6;
    padding: 2rem;
    max-width: 900px;
    margin: auto;
}
.stSelectbox > div, .stMarkdown, .stCaption {
    color: #3E4E2C;
}
h3 {
    margin-bottom: 0.2rem;
    font-size: 0.95rem;
    color: #4C3D29;
}
p, .markdown-text-container {
    margin-top: 0.05rem;
    margin-bottom: 0.5rem;
    line-height: 1.2;
}
hr {
    margin: 0.6rem 0;
    border: none;
    border-top: 1px solid #ccc;
}
</style>
"""
st.markdown(eco_css, unsafe_allow_html=True)

def _approx_contains_text(value, ql: str, thr: float = 0.8) -> bool:
    """Búsqueda aproximada tolerante a errores de tipeo."""
    try:
        import pandas as pd  # por si el módulo se evalúa en otro archivo
    except Exception:
        pass

    s = "" if value is None else str(value)
    s = s.lower()

    # 1) Substring directo
    if ql in s:
        return True

    # 2) Aproximación por tokens (palabras)
    tokens = re.findall(r"\w+", s)
    for t in tokens:
        if SequenceMatcher(None, ql, t).ratio() >= thr:
            return True

    # 3) Aproximación por ventana deslizante (frases)
    L = len(ql)
    if L >= 4 and len(s) >= L:
        for i in range(len(s) - L + 1):
            frag = s[i:i+L]
            if SequenceMatcher(None, ql, frag).ratio() >= thr:
                return True

    return False

# Mostrar logo y cabecera
top1, top2 = st.columns([2, 9])
with top1:
    st.image("images/logo_aucca.png", width=120)
with top2:
    st.title("Acuerdos")

st.caption("Corazón = Mente = Espíritu = Conciencia 👂🏾🧠🫀")
# st.caption("Esta aplicación es una herramienta comunitaria para quienes habitamos el centro eco-pedagógico AUCCA")

# Función para cargar datos desde Google Sheets
def cargar_datos(sheet_name):
    creds = Credentials.from_service_account_info(
        st.secrets["gspread"],
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)
    sh = client.open_by_key("1C8njkp0RQMdXnxuJvPvfK_pNZHQSi7q7dUPeUg-2624")
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# Botón para borrar la caché
if st.button("Actualizar Base de datos"):
    st.cache_data.clear()
    st.success("Caché borrada correctamente. La base de datos está actualizada")

# Navegación principal sin sidebar
seccion = st.selectbox("🌿 Explorar secciones", [
    "",
    "Checklist de semanerx",
    "Acuerdos de convivencia (internos)",
    "Acuerdos Comunicación Externa",
    "Links claves"
])

if seccion == "":
    colq1, colq2 = st.columns([1, 10])
    with colq1:
        st.image("images/queltehue.png", width=70)
    with colq2:
        st.markdown("""
        #### ¿Qué encontrarás aquí?

        - **Acuerdos de convivencia (internos)**: lo que hemos decidido como comunidad para convivir mejor.
        - **Acuerdos de comunicación externa**: cómo nos relacionamos con organizaciones, visitas y talleres.
        - **Check List semanerxs**: sistema de registro de avances en actividades de semanerxs. 
        - **Links claves**: repositorio de links claves sobre Aucca y lo que aquí ocurre. 

        Usa los menús desplegables arriba para explorar cada sección. 🌱
        """)


elif seccion == "Links claves":
    # --- mejoras de UI/UX para links claves ---
    import datetime
    from urllib.parse import urlparse

    df = cargar_datos("links")

    # Normalizar nombres de columnas (acepta variaciones)
    rename_map = {
        "Petalo": "Pétalo", "Pétalo": "Pétalo",
        "Tema": "Tema",
        "Detalle": "Detalle",
        "Tipo": "Tipo",
        "Fecha creación": "Fecha creación", "Fecha creacion": "Fecha creación",
        "Año": "Año", "Anio": "Año",
        "Nombre": "Nombre",
        "Descripción": "Descripción", "Descripcion": "Descripción",
        "url": "URL", "Url": "URL", "URL": "URL",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Asegurar columnas esperadas
    expected_cols = ["Pétalo","Tema","Detalle","Tipo","Fecha creación","Año","Nombre","Descripción","URL"]
    for c in expected_cols:
        if c not in df.columns:
            df[c] = ""

    # Limpieza básica
    for c in expected_cols:
        df[c] = df[c].astype(str).str.strip()

    # Unificar formato de Pétalo
    df["Pétalo"] = df["Pétalo"].str.title()

    # Parseo de Año
    def _to_int(x):
        try:
            return int(float(str(x).strip()))
        except:
            return None
    df["Año_int"] = df["Año"].apply(_to_int)

    # Parseo de "Fecha creación" con meses en español (p.ej., "25 julio 2025")
    meses = {
        "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
        "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,
        "noviembre":11,"diciembre":12,
    }
    def _parse_fecha_es(s):
        s = str(s).strip().lower()
        if not s:
            return None
        parts = s.replace("de ", "").split()
        # Formatos típicos: "25 julio 2025" / "2 marzo 2025"
        try:
            if len(parts) >= 3:
                d = int(parts[0]); m = meses.get(parts[1]); y = int(parts[2])
                if m:
                    return datetime.datetime(y, m, d)
        except:
            pass
        return None

    df["Fecha_dt"] = df["Fecha creación"].apply(_parse_fecha_es)
    # Si no hay fecha, usar 1-enero del año (si existe)
    faltan_fecha = df["Fecha_dt"].isna() & df["Año_int"].notna()
    df.loc[faltan_fecha, "Fecha_dt"] = df.loc[faltan_fecha, "Año_int"].apply(lambda y: datetime.datetime(y,1,1))

    # Dominio del enlace (estético/informativo)
    def _domain(u):
        try:
            d = urlparse(u).netloc
            return d.replace("www.", "")
        except:
            return ""
    df["Dominio"] = df["URL"].apply(_domain)

    st.subheader("🔗 Links claves")

    # —— Filtros + búsqueda
    c0, c1, c2, c3, c4 = st.columns([2, 2, 2, 2, 2])
    with c0:
        q = st.text_input("Buscar", placeholder="Nombre o descripción...")
    with c1:
        petalos = ["(Todos)"] + sorted([x for x in df["Pétalo"].unique() if x])
        f_petalo = st.selectbox("Pétalo", petalos, index=0)
    with c2:
        if f_petalo != "(Todos)":
            temas_opts = ["(Todos)"] + sorted([x for x in df.loc[df["Pétalo"] == f_petalo, "Tema"].unique() if x])
        else:
            temas_opts = ["(Todos)"] + sorted([x for x in df["Tema"].unique() if x])
        f_tema = st.selectbox("Tema", temas_opts, index=0)
    with c3:
        tipos_opts = sorted([x for x in df["Tipo"].unique() if x])
        f_tipos = st.multiselect("Tipo", tipos_opts, default=[])
    with c4:
        anos_opts = sorted([int(x) for x in df["Año_int"].dropna().unique()], reverse=True)
        f_anos = st.multiselect("Año", anos_opts, default=[])

    # Aplicar filtros
    dff = df.copy()
    if q:
        ql = q.strip().lower()
        # Busca en TODAS las columnas con aproximación
        mask = dff.apply(lambda row: any(_approx_contains_text(v, ql) for v in row.values), axis=1)
        dff = dff[mask]


    if f_petalo != "(Todos)":
        dff = dff[dff["Pétalo"] == f_petalo]
    if f_tema != "(Todos)":
        dff = dff[dff["Tema"] == f_tema]
    if f_tipos:
        dff = dff[dff["Tipo"].isin(f_tipos)]
    if f_anos:
        dff = dff[dff["Año_int"].isin(f_anos)]

    # Orden: primero por fecha (más nuevo), luego por año, luego por nombre
    dff = dff.sort_values(["Fecha_dt", "Año_int", "Nombre"], ascending=[False, False, True], na_position="last")

    ver_todo = st.checkbox("📋 Ver todos (agrupados por Tema)", value=False)

    # —— Render helpers (definidos aquí para mantener el bloque autocontenible)
    def _link_button(label, url):
        # Usa link_button si está disponible; si no, link normal
        try:
            st.link_button(label, url, use_container_width=True)
        except Exception:
            st.markdown(f"[{label}]({url})")

    def _render_card(row):
        nombre = row["Nombre"] or "(Sin nombre)"
        petalo = row["Pétalo"] or "—"
        tema = row["Tema"] or "—"
        detalle = row["Detalle"] or "—"
        tipo = row["Tipo"] or "—"
        anio = row["Año"] or ""
        dominio = row["Dominio"] or ""
        fecha_txt = ""
        if isinstance(row["Fecha_dt"], datetime.datetime):
            fecha_txt = row["Fecha_dt"].strftime("Creado el %d-%m-%Y")

        st.markdown(f"#### {nombre}")
        st.caption(f"{petalo} · {tema} · {detalle} · {tipo} · {anio}")
        if fecha_txt:
            st.caption(fecha_txt)
        if row["Descripción"]:
            st.markdown(row["Descripción"])
        if row["URL"]:
            _link_button("Abrir enlace", row["URL"])
            if dominio:
                st.caption(f"🌐 {dominio}")
        else:
            st.button("Sin URL", disabled=True, use_container_width=True)

    def _render_cards_grid(gdf):
        gdf = gdf.reset_index(drop=True)
        for i in range(0, len(gdf), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j >= len(gdf):
                    break
                with col:
                    _render_card(gdf.iloc[i + j])

    # —— Mostrar resultados
    if dff.empty:
        st.info("No hay enlaces que coincidan con los filtros.")
    else:
        if ver_todo:
            for tema_val, grupo in dff.groupby("Tema"):
                st.subheader(f"🔸 {tema_val or '(Sin tema)'}")
                _render_cards_grid(grupo)
        else:
            _render_cards_grid(dff.head(60))  # límite razonable para evitar scroll infinito



# elif seccion == "Tareas semanerxs por zona":
#     df = cargar_datos("tareas_semaneros")
#     df = df.rename(columns={
#         "Tema": "Área de responsabilidad semanal",
#         "Zona": "Elemento o espacio específico",
#         "Tarea": "Detalle de lo que debe realizarse"
#     })
#     temas = df['Área de responsabilidad semanal'].unique()
#     tema = st.selectbox("🌱 Selecciona un área de responsabilidad semanal:", [""] + list(temas))
#     if tema:
#         subset = df[df['Área de responsabilidad semanal'] == tema]
#         for _, row in subset.iterrows():
#             st.markdown(f"#### {row['Elemento o espacio específico']}")
#             st.markdown(f"{row['Detalle de lo que debe realizarse']}")




elif seccion == "Acuerdos de convivencia (internos)":
    df = cargar_datos("acuerdos_internos")
    df = df.rename(columns={
        "Tema": "Tema",
        "Orden": "Número de orden",
        "Acuerdo": "Acuerdo"
    })
    temas = df['Tema'].unique()
    ver_todo = st.checkbox("Ver todos los acuerdos por tema")

    if ver_todo:
        for tema in temas:
            subset = df[df['Tema'] == tema].sort_values("Número de orden")
            with st.expander(f"🟢 {tema}", expanded=False):
                for _, row in subset.iterrows():
                    st.markdown(f"{row['Número de orden']}. {row['Acuerdo']}")
    else:
        tema = st.selectbox("Selecciona un tema:", [""] + list(temas))
        if tema:
            subset = df[df['Tema'] == tema].sort_values("Número de orden")
            st.subheader(f"🟢 {tema}")
            for _, row in subset.iterrows():
                st.markdown(f"{row['Número de orden']}. {row['Acuerdo']}")

elif seccion == "Acuerdos Comunicación Externa":
    df = cargar_datos("actuerdos_externos")
    df = df.rename(columns={
        "Acuerdo": "Tipo de acuerdo",
        "Aspecto": "Aspecto específico",
        "Detalle": "Detalle del acuerdo"
    })
    tipos = df['Tipo de acuerdo'].unique()
    tipo = st.selectbox("Selecciona un tipo de acuerdo:", [""] + list(tipos))
    if tipo:
        subset = df[df['Tipo de acuerdo'] == tipo]
        for _, row in subset.iterrows():
            st.markdown(f"#### {row['Aspecto específico']}")
            st.markdown(f"{row['Detalle del acuerdo']}")
    for _, row in subset.iterrows():
        st.markdown(f"#### {row['Aspecto específico']}")
        st.markdown(f"{row['Detalle del acuerdo']}")


elif seccion == "Checklist de semanerx":
    inicio_semana = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
    fin_semana = inicio_semana + datetime.timedelta(days=6)
    inicio_semana = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
    fin_semana = inicio_semana + datetime.timedelta(days=6)

    
    inicio_semana = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
    fin_semana = inicio_semana + datetime.timedelta(days=6)
    rango_fecha = st.date_input(
        "Selecciona el rango de fechas para visualizar registros:",
        value=(inicio_semana, fin_semana)
    )

    
    
    fecha_inicio = datetime.datetime.combine(rango_fecha[0], datetime.datetime.min.time())
    fecha_fin = datetime.datetime.combine(rango_fecha[1], datetime.datetime.max.time())
    st.markdown(f"#### Hoy es {datetime.datetime.now().strftime('%A %d de %B de %Y, %H:%M')} 🗓️")
    
    st.markdown("✅ Checklist de semanerx ")
    st.caption("Revisa y marca las tareas que se han realizado durante la semana.")

    semaneros = ["Chalo", "Camilú", "Niko", "Diego", "Francis", "Tais", "Cala"]
    nombre = st.selectbox("Selecciona tu nombre:", [""] + semaneros)
    df_tareas = cargar_datos("tareas_semaneros")


    try:
        df_estado = cargar_datos("estado_tareas")
        if df_estado.empty:
            df_estado = pd.DataFrame(columns=["Fecha", "Usuario", "Tema", "Zona", "Tarea", "Completada"])
        else:
            df_estado.columns = [col.strip() for col in df_estado.columns]
    except:
        df_estado = pd.DataFrame(columns=["Fecha", "Usuario", "Tema", "Zona", "Tarea", "Completada"])

    hoy = datetime.datetime.now()
    semana_actual = hoy.isocalendar()[1]
    df_estado["Semana"] = pd.to_datetime(df_estado["Fecha"], format='%Y-%m-%d %H:%M')\
    .dt.isocalendar().week

    tareas_realizadas = df_estado[df_estado["Semana"] == semana_actual]["Tarea"].tolist()
    
    if nombre:
        # Convertir Porcentaje a numérico y filtrar tareas completadas al 100%
        df_estado["Porcentaje"] = pd.to_numeric(df_estado.get("Porcentaje", 0), errors="coerce").fillna(0).astype(int)
        completadas_100 = df_estado[
            (df_estado["Semana"] == semana_actual) & 
            (df_estado["Porcentaje"] == 100)
        ]["Tarea"].unique().tolist()
    
        # Mostrar solo tareas que no han sido completadas al 100%
        df_pendientes = df_tareas[~df_tareas["Tarea"].isin(completadas_100)]
    
        for tema in df_pendientes["Tema"].unique():
            st.markdown(f"### 🌱 {tema}")
            subtareas = df_pendientes[df_pendientes["Tema"] == tema]
    
            for _, row in subtareas.iterrows():
                tarea_id = f"{row['Zona']} - {row['Tarea']}"
                registro_previo = df_estado[
                    (df_estado["Tarea"] == row["Tarea"]) & 
                    (df_estado["Semana"] == semana_actual) &
                    (df_estado["Usuario"] == nombre)
                ]
                porcentaje_prev = registro_previo["Porcentaje"].max() if not registro_previo.empty else 0
    
                label_text = f"**{row['Zona']}**: {row['Tarea']}"
                if 0 < porcentaje_prev < 100:
                    label_text += f" (Avance: {porcentaje_prev}%)"
    
                completada = st.checkbox(label_text, key=tarea_id)
    
                if completada:
                    st.markdown(f"#### {row['Zona']}: {row['Tarea']}")
                    with st.expander("✏️ Completa los detalles para esta tarea:", expanded=True):
                        porcentaje = st.slider("¿Cuánto se completó esta tarea?", min_value=0, max_value=100, value=100, step=10, key=f"porc_{tarea_id}")
                        observacion = st.text_area("Observaciones", key=f"obs_{tarea_id}")
                        registrar = st.button("Registrar", key=f"btn_{tarea_id}")
    
                    if registrar:
                        estado = "Sí" if porcentaje == 100 else "En proceso"
                        creds = Credentials.from_service_account_info(
                            st.secrets["gspread"],
                            scopes=[
                                "https://spreadsheets.google.com/feeds",
                                "https://www.googleapis.com/auth/drive"
                            ]
                        )
                        client = gspread.authorize(creds)
                        sh = client.open_by_key("1C8njkp0RQMdXnxuJvPvfK_pNZHQSi7q7dUPeUg-2624")
                        worksheet = sh.worksheet("estado_tareas")
                        worksheet.append_row([
                            hoy.strftime("%Y-%m-%d %H:%M"),
                            nombre,
                            row["Tema"],
                            row["Zona"],
                            row["Tarea"],
                            estado,
                            porcentaje,
                            observacion
                        ])
                        st.success(f"✅ Tarea registrada: {row['Zona']} - {row['Tarea']} ({estado}, {porcentaje}%)")

        
   
        

    # Mostrar resumen por tema
    st.markdown("---")
    st.subheader("Resumen de tareas completadas por tema (esta semana)")

    # Calcular resumen antes de usarlo
    completadas = df_estado[(pd.to_datetime(df_estado["Fecha"], format='%Y-%m-%d %H:%M') >= fecha_inicio) & (pd.to_datetime(df_estado["Fecha"], format='%Y-%m-%d %H:%M') <= fecha_fin)]
    resumen_tema = completadas.groupby("Tema")["Tarea"].count()
    total_por_tema = df_tareas.groupby("Tema")["Tarea"].count()
    resumen = pd.DataFrame({
        "Completadas": resumen_tema,
        "Total": total_por_tema
    }).fillna(0).astype(int)
    resumen["% completado"] = ((resumen["Completadas"] / resumen["Total"]) * 100).round(1).astype(str) + "%"

    # Mostrar selector ahora que resumen está definido
    tema_seleccionado = st.selectbox("🔍 Selecciona un tema para ver detalles:", [""] + resumen.index.tolist())
    if tema_seleccionado:
        tareas_tema = df_tareas[df_tareas["Tema"] == tema_seleccionado]
        completadas_tema = completadas[completadas["Tema"] == tema_seleccionado]

        st.markdown("#### Tareas realizadas:")
        if 'completadas_tema' in locals():
            completadas_tema = completadas_tema.rename(columns={"Usuario": "Auccane"})
            st.dataframe(completadas_tema[["Zona", "Tarea", "Porcentaje","Auccane", "Observaciones","Fecha"]].sort_values("Fecha", ascending=False))

        else:
            st.info("Selecciona un tema para ver tareas completadas y pendientes.")
        
        # Convertir Porcentaje a número y renombrar columna Usuario → Auccane
        completadas_tema["Porcentaje"] = pd.to_numeric(completadas_tema["Porcentaje"], errors="coerce").fillna(0).astype(int)
        completadas_tema = completadas_tema.rename(columns={"Usuario": "Auccane"})
        
        # Dividir tareas completadas (100%) y en proceso
        completadas_100 = completadas_tema[completadas_tema["Porcentaje"] == 100]
        en_proceso = completadas_tema[(completadas_tema["Porcentaje"] > 0) & (completadas_tema["Porcentaje"] < 100)]
        
        # Mostrar tareas completadas
        if not completadas_100.empty:
            st.markdown("#### Tareas completadas (100%)")
            st.dataframe(
                completadas_100[["Zona","Fecha","Tarea","Auccane","Observaciones"]]
                .sort_values("Fecha", ascending=False)
                .style.set_properties(subset=["Observaciones"], **{"white-space": "pre-wrap"})
            )
        
        # Mostrar tareas en proceso
        if not en_proceso.empty:
            st.markdown("#### Tareas comenzadas pero no finalizadas")
            st.dataframe(
                en_proceso[["Fecha", "Auccane", "Zona", "Tarea", "Porcentaje", "Observaciones"]]
                .sort_values("Fecha", ascending=False)
                .style.set_properties(subset=["Observaciones"], **{"white-space": "pre-wrap"})
            )
        
        # Filtrar tareas que no han sido registradas
        realizadas = completadas_100["Tarea"].unique().tolist()
        pendientes_tema = tareas_tema[~tareas_tema["Tarea"].isin(realizadas)]
        
        # Mostrar tareas pendientes
        st.markdown("#### Tareas pendientes")
        st.dataframe(pendientes_tema[["Zona", "Tarea"]].reset_index(drop=True))



    import plotly.express as px
    # Convertir Porcentaje a número
    completadas = df_estado[
        (pd.to_datetime(df_estado["Fecha"], format='%Y-%m-%d %H:%M') >= fecha_inicio) &
        (pd.to_datetime(df_estado["Fecha"], format='%Y-%m-%d %H:%M') <= fecha_fin)
    ]
    completadas["Porcentaje"] = pd.to_numeric(completadas["Porcentaje"], errors="coerce").fillna(0).astype(int)
    
    completadas_100 = completadas[completadas["Porcentaje"] == 100]
    completadas_incompletas = completadas[(completadas["Porcentaje"] > 0) & (completadas["Porcentaje"] < 100)]
    completadas_total = pd.concat([completadas_100, completadas_incompletas])
    completadas_total_tareas = completadas_total["Tarea"].unique().tolist()
    
    # Gráfico de tareas completadas (100%)
    resumen_tema_100 = completadas_100.groupby("Tema")["Tarea"].count()
    total_por_tema = df_tareas.groupby("Tema")["Tarea"].count()
    resumen_100 = pd.DataFrame({
        "Completadas": resumen_tema_100,
        "Total": total_por_tema
    }).fillna(0).astype(int)
    resumen_100["% completado"] = (resumen_100["Completadas"] / resumen_100["Total"] * 100).round(1)
    
    chart_data_100 = resumen_100.reset_index()
    fig_100 = px.bar(
        chart_data_100,
        x="Tema",
        y="% completado",
        text=chart_data_100["% completado"].astype(str) + "%",
        color_discrete_sequence=["#4C9A2A"],
        hover_data={"Total": True, "% completado": True, "Completadas": True},
        labels={"% completado": "% Completado"},
        title="✅ Tareas completadas (100%) por tema"
    )
    fig_100.update_traces(textposition='outside')
    fig_100.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(fig_100, use_container_width=True)
            
        # # Gráfico de tareas en proceso
        # if not completadas_incompletas.empty:
        #     resumen_proceso = completadas_incompletas.groupby("Tema")["Tarea"].count()
        #     chart_data_proc = resumen_proceso.reset_index().rename(columns={"Tarea": "En proceso"})
        #     fig_proc = px.bar(
        #         chart_data_proc,
        #         x="Tema",
        #         y="En proceso",
        #         text="En proceso",
        #         color_discrete_sequence=["#FFA726"],
        #         title="🟠 Tareas en proceso por tema"
        #     )
        #     fig_proc.update_traces(textposition='outside')
        #     #st.plotly_chart(fig_proc, use_container_width=True)
        
        # # Gráfico de tareas no iniciadas
        # todas_tareas = df_tareas.copy()
        # no_iniciadas = todas_tareas[~todas_tareas["Tarea"].isin(completadas_total_tareas)]
        # if not no_iniciadas.empty:
        #     resumen_no_iniciadas = no_iniciadas.groupby("Tema")["Tarea"].count().reset_index().rename(columns={"Tarea": "No iniciadas"})
        #     fig_no = px.bar(
        #         resumen_no_iniciadas,
        #         x="Tema",
        #         y="No iniciadas",
        #         text="No iniciadas",
        #         color_discrete_sequence=["#B0BEC5"],
        #         title="⬜ Tareas no iniciadas por tema"
        #     )
        #     fig_no.update_traces(textposition='outside')
        #     #st.plotly_chart(fig_no, use_container_width=True)




    
    with st.expander("Ver registros detallados por aucane"):
        aucane = st.selectbox("Selecciona una persona:", [""] + sorted(completadas["Usuario"].unique().tolist()))
        if aucane:
            registros_aucane = completadas[completadas["Usuario"] == aucane].sort_values("Fecha", ascending=False)
            total_tareas = len(df_tareas)
            completadas_aucane = len(registros_aucane)
            porcentaje = round((completadas_aucane / total_tareas) * 100, 1) if total_tareas > 0 else 0
            st.markdown(f"**{aucane} completó {completadas_aucane} de {total_tareas} tareas esta semana ({porcentaje}%)**")
            if not registros_aucane.empty:
                resumen_aucane = registros_aucane.groupby("Tema")["Tarea"].count()
                resumen_aucane = resumen_aucane.reset_index().rename(columns={"Tarea": "Tareas completadas"})
                st.dataframe(registros_aucane[["Fecha", "Tema", "Zona", "Tarea"]])
                st.markdown("**Temas en los que más ha contribuido:**")
                st.dataframe(resumen_aucane.sort_values("Tareas completadas", ascending=False))

                fig_aucane = px.pie(
                    resumen_aucane,
                    names="Tema",
                    values="Tareas completadas",
                    title=f"Distribución de aportes de {aucane} por tema",
                    color_discrete_sequence=["#4C9A2A"]
                )
                st.plotly_chart(fig_aucane, use_container_width=True, key=f"plot_{aucane}")
            else:
                st.info("Esta persona no ha completado tareas en el rango de fechas seleccionado.")
            resumen_aucane = resumen_aucane.reset_index().rename(columns={"Tarea": "Tareas completadas"})
            # st.dataframe(registros_aucane[["Fecha", "Tema", "Zona", "Tarea"]])
            # st.markdown("**Temas en los que más ha contribuido:**")
            # st.dataframe(resumen_aucane.sort_values("Tareas completadas", ascending=False))

            # fig_aucane = px.pie(
            #     resumen_aucane,
            #     names="Tema",
            #     values="Tareas completadas",
            #     title=f"Distribución de aportes de {aucane} por tema",
            #     color_discrete_sequence=["#4C9A2A"]
            # )
            # st.plotly_chart(fig_aucane, use_container_width=True)
            # st.dataframe(completadas[["Fecha", "Usuario", "Tema", "Zona", "Tarea"]].sort_values("Fecha", ascending=False))

            completadas = df_estado[df_estado["Semana"] == semana_actual]
            resumen_tema = completadas.groupby("Tema")["Tarea"].count()
            total_por_tema = df_tareas.groupby("Tema")["Tarea"].count()
            resumen = pd.DataFrame({
                "Completadas": resumen_tema,
                "Total": total_por_tema
            }).fillna(0).astype(int)
            resumen["% completado"] = (resumen["Completadas"] / resumen["Total"] * 100).round(1)

            st.dataframe(resumen)
            st.caption("*Resumen de tareas completadas esta semana agrupadas por tema.*")



































