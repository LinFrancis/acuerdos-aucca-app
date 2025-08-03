import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2.service_account import Credentials

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

# Conexión a Google Sheets desde credenciales
@st.cache_data
def cargar_datos(sheet_name):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    

    creds = Credentials.from_service_account_info(
        st.secrets["gspread"],
        scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    client = gspread.authorize(creds)
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
    "Videos y recursos"
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
    tema = st.selectbox("🌱 Selecciona un área de responsabilidad semanal:", temas)
    subset = df[df['Área de responsabilidad semanal'] == tema]
    for _, row in subset.iterrows():
        st.markdown(f"#### {row['Elemento o espacio específico']}")
        st.markdown(f"{row['Detalle de lo que debe realizarse']}")
        #st.markdown("---")

elif seccion == "Acuerdos de convivencia (internos)":
    df = cargar_datos("acuerdos_internos")
    df = df.rename(columns={
        "Tema": "Tema",
        "Orden": "Número de orden",
        "Acuerdo": "Acuerdo"
    })
    temas = df['Tema'].unique()
    ver_todo = st.checkbox("📜 Ver todos los acuerdos por tema")

    if ver_todo:
        for tema in temas:
            st.subheader(f"🟢 {tema}")
            subset = df[df['Tema'] == tema].sort_values("Número de orden")
            for _, row in subset.iterrows():
                st.markdown(f"{row['Número de orden']}. {row['Acuerdo']}")
    else:
        tema = st.selectbox("🪴 Selecciona un tema:", temas)
        subset = df[df['Tema'] == tema].sort_values("Número de orden")
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
    tipo = st.selectbox("🤝 Selecciona un tipo de acuerdo:", tipos)
    subset = df[df['Tipo de acuerdo'] == tipo]
    for _, row in subset.iterrows():
        st.markdown(f"#### {row['Aspecto específico']}")
        st.markdown(f"{row['Detalle del acuerdo']}")
        #st.markdown("---")

elif seccion == "Videos y recursos":
    st.subheader("🔌 Funcionamiento de la electricidad en AUCCA")
    st.video("luz_solar_chalo.mp4")
    st.markdown("Este video explica cómo funciona la electricidad solar en AUCCA. Pronto agregaremos nuevos videos para cada tema.")