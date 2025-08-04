import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

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

# Mostrar logo y cabecera
top1, top2 = st.columns([1, 10])
with top1:
    st.image("images/logo_aucca.png", width=120)
with top2:
    st.title("Acuerdos")

st.caption("Corazón = Mente = Espíritu = Conciencia 👂🏾🧠🫀")
st.markdown("""
Esta aplicación es una herramienta comunitaria para quienes habitamos el centro eco-pedagógico AUCCA.
Nace de nuestra intención de construir un mejor día a día, reconociendo que el buen vivir también se cultiva
en lo cotidiano: en el cuidado del espacio, de las relaciones, de las confianzas y de los acuerdos.
""")

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

# Navegación principal sin sidebar
seccion = st.selectbox("🌿 Explorar secciones", [
    "",
    "Tareas por zona (semanerxs)",
    "Acuerdos de convivencia (internos)",
    "Acuerdos Comunicación Externa",
    "Videos y recursos",
    "✅ Checklist de semanero"
])

if seccion == "":
    colq1, colq2 = st.columns([1, 10])
    with colq1:
        st.image("images/queltehue.png", width=70)
    with colq2:
        st.markdown("""
        ### ¿Qué encontrarás aquí?
        Esta aplicación contiene acuerdos y tareas organizadas por temas, zonas y tipo de convivencia.

        - **Tareas por zona (semanerxs)**: responsabilidades de limpieza y mantenimiento profundo.
        - **Acuerdos de convivencia (internos)**: lo que hemos decidido como comunidad para convivir mejor.
        - **Acuerdos de comunicación externa**: cómo nos relacionamos con organizaciones, visitas y talleres.
        - **Videos y recursos**: materiales visuales de apoyo.

        Usa los menús desplegables para explorar cada sección. 🌱
        """)

elif seccion == "Tareas por zona (semanerxs)":
    df = cargar_datos("tareas_semaneros")
    df = df.rename(columns={
        "Tema": "Área de responsabilidad semanal",
        "Zona": "Elemento o espacio específico",
        "Tarea": "Detalle de lo que debe realizarse"
    })
    temas = df['Área de responsabilidad semanal'].unique()
    tema = st.selectbox("🌱 Selecciona un área de responsabilidad semanal:", [""] + list(temas))
    if tema:
        subset = df[df['Área de responsabilidad semanal'] == tema]
        for _, row in subset.iterrows():
            st.markdown(f"#### {row['Elemento o espacio específico']}")
            st.markdown(f"{row['Detalle de lo que debe realizarse']}")
    for _, row in subset.iterrows():
        st.markdown(f"#### {row['Elemento o espacio específico']}")
        st.markdown(f"{row['Detalle de lo que debe realizarse']}")

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

elif seccion == "Videos y recursos":
    st.subheader("🔌 Funcionamiento de la electricidad en AUCCA")
    st.video("luz_solar_chalo.mp4")
    st.markdown("Este video explica cómo funciona la electricidad solar en AUCCA. Pronto agregaremos nuevos videos para cada tema.")

elif seccion == "✅ Checklist de semanero":
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
        df_pendientes = df_tareas[~df_tareas["Tarea"].isin(tareas_realizadas)]
    else:
        df_pendientes = pd.DataFrame(columns=df_tareas.columns)

    for tema in df_pendientes["Tema"].unique():
        st.markdown(f"#### 🌱 {tema}")
        subtareas = df_pendientes[df_pendientes["Tema"] == tema]

        for _, row in subtareas.iterrows():
            tarea_id = f"{row['Zona']} - {row['Tarea']}"
            completada = st.checkbox(
                f"**{row['Zona']}**: {row['Tarea']}", key=tarea_id
            )

            if completada:
                st.markdown(f"#### {row['Zona']}: {row['Tarea']}")
            
                with st.expander("✏️ Completa los detalles para esta tarea:", expanded=True):
                    porcentaje = st.slider(
                        "¿Cuánto se completó esta tarea?",
                        min_value=0,
                        max_value=100,
                        value=100,
                        step=10,
                        key=f"porc_{tarea_id}"
                    )
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

        st.markdown("**✅ Tareas realizadas:**")
        if 'completadas_tema' in locals():
            st.dataframe(completadas_tema[["Fecha", "Usuario", "Zona", "Tarea"]].sort_values("Fecha", ascending=False))
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
            st.markdown("### ✅ Tareas completadas (100%)")
            st.dataframe(
                completadas_100[["Fecha", "Auccane", "Zona", "Tarea", "Observaciones"]]
                .sort_values("Fecha", ascending=False)
                .style.set_properties(subset=["Observaciones"], **{"white-space": "pre-wrap"})
            )
        
        # Mostrar tareas en proceso
        if not en_proceso.empty:
            st.markdown("### 🟠 Tareas comenzadas pero no finalizadas")
            st.dataframe(
                en_proceso[["Fecha", "Auccane", "Zona", "Tarea", "Porcentaje", "Observaciones"]]
                .sort_values("Fecha", ascending=False)
                .style.set_properties(subset=["Observaciones"], **{"white-space": "pre-wrap"})
            )
        
        # Filtrar tareas que no han sido registradas
        realizadas = completadas_100["Tarea"].unique().tolist()
        pendientes_tema = tareas_tema[~tareas_tema["Tarea"].isin(realizadas)]
        
        # Mostrar tareas pendientes
        st.markdown("### ⬜ Tareas pendientes")
        st.dataframe(pendientes_tema[["Zona", "Tarea"]].reset_index(drop=True))

        
        
        
        
        
        
    # Gráfico de barras interactivo
    import plotly.express as px
    completadas = df_estado[(pd.to_datetime(df_estado["Fecha"], format='%Y-%m-%d %H:%M') >= fecha_inicio) & (pd.to_datetime(df_estado["Fecha"], format='%Y-%m-%d %H:%M') <= fecha_fin)]
    resumen_tema = completadas.groupby("Tema")["Tarea"].count()
    total_por_tema = df_tareas.groupby("Tema")["Tarea"].count()
    resumen = pd.DataFrame({
        "Completadas": resumen_tema,
        "Total": total_por_tema
    }).fillna(0).astype(int)
    resumen["% completado"] = ((resumen["Completadas"] / resumen["Total"]) * 100).round(1).astype(str) + "%"

    chart_data = resumen.reset_index()
    fig = px.bar(
        chart_data,
        x="Tema",
        y="% completado",
        text=resumen["% completado"].astype(str) + "%",
        color_discrete_sequence=["#4C9A2A"],
        hover_data={"Total": True, "% completado": True, "Completadas": True},
        labels={"% completado": "% Completado"},
        title="Porcentaje de tareas completadas por tema"
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(yaxis_range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)

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










