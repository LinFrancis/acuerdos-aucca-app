import time

import pandas as pd
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError

SHEET_KEY = "1C8njkp0RQMdXnxuJvPvfK_pNZHQSi7q7dUPeUg-2624"
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]


@st.cache_resource
def _get_client():
    creds = Credentials.from_service_account_info(st.secrets["gspread"], scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource
def _get_spreadsheet():
    return _get_client().open_by_key(SHEET_KEY)


def get_worksheet(sheet_name: str):
    """Handle de una pestaña del spreadsheet. No cachea contenido, solo evita
    reabrir el spreadsheet completo (open_by_key) en cada llamada."""
    return _get_spreadsheet().worksheet(sheet_name)


def with_retry(fn, attempts: int = 3, base_delay: float = 1.5):
    """Ejecuta `fn` reintentando ante errores transitorios de la API de Google
    (cuota excedida, 5xx). Si se agotan los intentos, relanza el último error."""
    last_exc = None
    for i in range(attempts):
        try:
            return fn()
        except APIError as e:
            last_exc = e
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (429, 500, 502, 503) and i < attempts - 1:
                time.sleep(base_delay * (i + 1))
                continue
            raise
    raise last_exc


@st.cache_data(ttl=300)
def cargar_datos(sheet_name: str) -> pd.DataFrame:
    ws = get_worksheet(sheet_name)
    data = with_retry(lambda: ws.get_all_records())
    df = pd.DataFrame(data)
    df.columns = [c.strip() for c in df.columns]
    return df


def invalidate_sheet(sheet_name: str):
    """Limpia SOLO el caché de esta pestaña (no borra el caché de las demás
    hojas). Úsalo después de escribir en `sheet_name`."""
    try:
        cargar_datos.clear(sheet_name)
    except Exception:
        pass


def append_row(sheet_name: str, values: list, value_input_option: str = None):
    """Agrega una fila con reintentos automáticos ante errores transitorios,
    e invalida el caché de esa hoja (y solo esa) al terminar."""
    ws = get_worksheet(sheet_name)
    kwargs = {"value_input_option": value_input_option} if value_input_option else {}
    with_retry(lambda: ws.append_row(values, **kwargs))
    invalidate_sheet(sheet_name)
