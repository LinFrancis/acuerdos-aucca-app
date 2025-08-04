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
top1, top2 = st.columns([2, 9])
with top1:
    st.image("images/logo_aucca.png", width=120)
with top2:
    st.title("Acuerdos")

st.caption("Corazón = Mente = Espíritu = Conciencia 👂🏾🧠🫀")
st.markdown("""
Esta aplicación es una herramienta comunitaria para quienes habitamos el centro eco-pedagógico AUCCA.
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

# Botón para borrar la caché
if st.button("Actualizar Base de datos"):
    st.cache_data.clear()
    st.success("Caché borrada correctamente. La base de datos está actualizada")

# Navegación principal sin sidebar
seccion = st.selectbox("🌿 Explorar secciones", [
    "",
    "Acuerdos de convivencia (internos)",
    "Acuerdos Comunicación Externa",
    "Videos y recursos",
    "Tareas semanerxs por zona",
    "Checklist de semanerx",
    "Links claves"
])

if seccion == "":
    colq1, colq2 = st.columns([1, 10])
    with colq1:
        st.image("images/queltehue.png", width=70)
    with colq2:
        st.markdown("""
        #### ¿Qué encontrarás aquí?
        Esta aplicación contiene acuerdos y tareas organizadas por temas, zonas y tipo de convivencia.

        - **Tareas semanerxs por zona**: responsabilidades de limpieza y mantenimiento profundo.
        - **Acuerdos de convivencia (internos)**: lo que hemos decidido como comunidad para convivir mejor.
        - **Acuerdos de comunicación externa**: cómo nos relacionamos con organizaciones, visitas y talleres.
        - **Videos y recursos**: materiales visuales de apoyo.
        - **Check List semanerxs**: sistema de registro de avances en actividades de semanerxs. 
        - **Links claves**: repositorio de links claves sobre Aucca y lo que aquí ocurre. 

        Usa los menús desplegables arriba para explorar cada sección. 🌱
        """)

elif seccion == "Links claves":
    df = cargar_datos("links")
    df = df.rename(columns={
        "Tema": "Tema",
        "Nombre": "Nombre",
        "Descripción": "Descripción",
        "url": "URL"
    })
    temas = df["Tema"].unique()
    ver_todo = st.checkbox("📋 Ver todos los enlaces")
    
    if ver_todo:
        for tema in temas:
            st.subheader(f"🔸 {tema}")
            subset = df[df["Tema"] == tema]
            for _, row in subset.iterrows():
                st.markdown(f"**{row['Nombre']}**")
                st.markdown(f"{row['Descripción']}")
                st.markdown(f"[Abrir enlace]({row['URL']})")
    else:
        tema = st.selectbox("Selecciona un tema:", [""] + list(temas))
        if tema:
            subset = df[df["Tema"] == tema]
            for _, row in subset.iterrows():
                st.markdown(f"### 🔗 {row['Nombre']}")
                st.markdown(f"{row['Descripción']}")
                st.markdown(f"[Abrir enlace]({row['URL']})")


elif seccion == "Tareas semanerxs por zona":
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





























