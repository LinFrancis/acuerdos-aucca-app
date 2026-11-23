"""Capa de datos de la Cooperativa de Trabajo.

* Con credenciales de Google (st.secrets["gspread"]) guarda en hojas `coop_*` del
  mismo spreadsheet de la plataforma. Crea las hojas que falten.
* Sin credenciales (desarrollo local) guarda en `data/local_coop/*.json`.

NUNCA lee ni escribe la hoja «finanzas» de AUCCA.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st

TABLAS: dict[str, list[str]] = {
    "coop_proyectos": ["ID", "Nombre", "Tipo", "Fecha", "Estado", "Cliente", "Asistentes", "IVA",
                       "Escenario", "Descripcion", "Simulado"],
    "coop_items": ["ID", "ProyectoID", "Tipo", "Categoria", "Nombre", "Unidad", "Precio", "CostoUnit",
                   "CantidadPlan", "CantidadReal", "HorasPlan", "Productores", "Vendedor",
                   "PctProductor", "PctVendedor"],
    "coop_ventas": ["ID", "ProyectoID", "ItemID", "Cantidad", "PrecioUnit", "Vendedor", "Productor",
                    "Medio", "Fecha", "Simulado"],
    "coop_produccion": ["ID", "ProyectoID", "ItemID", "Persona", "Cantidad", "Simulado"],
    "coop_costos": ["ID", "ProyectoID", "Fecha", "Concepto", "Monto", "PagadoPor", "ItemID",
                    "ConBoleta", "Reembolsado", "Simulado"],
    "coop_registro": ["ID", "ProyectoID", "Persona", "Tarea", "ItemID", "Horas", "Nivel", "Esfuerzo",
                      "Origen", "Evidencia"],
    "coop_personas": ["Persona", "ValorHora", "Ofrece", "HorasMes", "Nivel", "Notas", "Simulado"],
    "coop_parametros": ["ID", "Nombre", "Estado", "Notas", "Parametros", "Actualizado"],
    "coop_pagos": ["ID", "ProyectoID", "Persona", "Concepto", "Monto", "Pagado", "FechaPago", "Medio", "Nota"],
    "coop_fondos": ["ID", "ProyectoID", "Fecha", "Tipo", "Monto", "Custodia", "Nota"],
    "coop_gobernanza": ["ID", "Tipo", "Titulo", "Circulo", "Descripcion", "Estado", "Responsable",
                        "Fecha", "Revision", "Objeciones", "Resultado"],
}

_LOCAL = Path(__file__).resolve().parent.parent / "data" / "local_coop"


def nuevo_id(prefijo: str = "x") -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:8]}"


def usa_sheets() -> bool:
    try:
        return "gspread" in st.secrets
    except Exception:
        return False


def modo_datos() -> str:
    return "Google Sheets" if usa_sheets() else "archivo local de prueba"


# ------------------------------------------------------------------ lectura
def _vacio(tabla: str) -> pd.DataFrame:
    return pd.DataFrame(columns=TABLAS[tabla])


def _normalizar(tabla: str, df: pd.DataFrame) -> pd.DataFrame:
    cols = TABLAS[tabla]
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols].fillna("").astype(str)


def _ws(tabla: str):
    from data.google import _get_spreadsheet, with_retry
    sh = _get_spreadsheet()
    try:
        return sh.worksheet(tabla)
    except Exception:
        ws = with_retry(lambda: sh.add_worksheet(title=tabla, rows=200, cols=len(TABLAS[tabla]) + 2))
        with_retry(lambda: ws.update(values=[TABLAS[tabla]], range_name="A1", value_input_option="RAW"))
        return ws


@st.cache_data(ttl=20, show_spinner=False)
def _leer_sheets(tabla: str) -> pd.DataFrame:
    from data.google import with_retry
    ws = _ws(tabla)
    vals = with_retry(lambda: ws.get_all_values())
    if not vals:
        return _vacio(tabla)
    cab = [h.strip() for h in vals[0]]
    filas = [r + [""] * (len(cab) - len(r)) for r in vals[1:] if any(str(c).strip() for c in r)]
    return _normalizar(tabla, pd.DataFrame(filas, columns=cab))


def _leer_local(tabla: str) -> pd.DataFrame:
    f = _LOCAL / f"{tabla}.json"
    if not f.exists():
        return _vacio(tabla)
    return _normalizar(tabla, pd.DataFrame(json.loads(f.read_text(encoding="utf-8"))))


def cargar(tabla: str, fresco: bool = False) -> pd.DataFrame:
    if usa_sheets():
        if fresco:
            _leer_sheets.clear(tabla)
        return _leer_sheets(tabla).copy()
    return _leer_local(tabla)


def cargar_proyecto(tabla: str, proyecto_id: str) -> pd.DataFrame:
    df = cargar(tabla)
    return df[df["ProyectoID"] == proyecto_id].reset_index(drop=True)


# ---------------------------------------------------------------- escritura
def _escribir_todo(tabla: str, df: pd.DataFrame) -> None:
    df = _normalizar(tabla, df.copy())
    if usa_sheets():
        from data.google import with_retry
        ws = _ws(tabla)
        valores = [TABLAS[tabla]] + df.values.tolist()
        with_retry(lambda: ws.clear())
        with_retry(lambda: ws.update(values=valores, range_name="A1", value_input_option="RAW"))
        _leer_sheets.clear(tabla)
    else:
        _LOCAL.mkdir(parents=True, exist_ok=True)
        (_LOCAL / f"{tabla}.json").write_text(
            json.dumps(df.to_dict("records"), ensure_ascii=False, indent=1), encoding="utf-8")


def _con_ids(tabla: str, df: pd.DataFrame, prefijo: str) -> pd.DataFrame:
    df = df.copy()
    if "ID" in TABLAS[tabla]:
        if "ID" not in df.columns:
            df["ID"] = ""
        df["ID"] = [i if str(i).strip() else nuevo_id(prefijo) for i in df["ID"].fillna("")]
    return df


def guardar_tabla(tabla: str, df: pd.DataFrame, prefijo: str = "x") -> None:
    """Reemplaza TODA la tabla (personas, parámetros, gobernanza)."""
    df = _con_ids(tabla, df, prefijo)
    df = df.dropna(how="all")
    _escribir_todo(tabla, df)


def guardar_proyecto(tabla: str, proyecto_id: str, df: pd.DataFrame, prefijo: str = "x") -> None:
    """Reemplaza solo las filas de un proyecto, leyendo antes lo último guardado."""
    actual = cargar(tabla, fresco=True)
    resto = actual[actual["ProyectoID"] != proyecto_id]
    nuevo = _con_ids(tabla, df, prefijo)
    nuevo["ProyectoID"] = proyecto_id
    nuevo = nuevo[[c for c in nuevo.columns]].replace({None: ""})
    nuevo = nuevo[~(nuevo.drop(columns=["ID", "ProyectoID"], errors="ignore").astype(str)
                    .apply(lambda r: "".join(r).strip(), axis=1) == "")]
    _escribir_todo(tabla, pd.concat([resto, _normalizar(tabla, nuevo)], ignore_index=True))


def guardar_fila(tabla: str, fila: dict, clave: str = "ID") -> None:
    """Inserta o actualiza una fila (por `clave`)."""
    actual = cargar(tabla, fresco=True)
    fila = {c: str(fila.get(c, "")) for c in TABLAS[tabla]}
    if clave == "ID" and not fila["ID"]:
        fila["ID"] = nuevo_id(tabla.split("_")[1][:2])
    mask = actual[clave] == fila[clave]
    if mask.any():
        for c, v in fila.items():
            actual.loc[mask, c] = v
    else:
        actual = pd.concat([actual, pd.DataFrame([fila])], ignore_index=True)
    _escribir_todo(tabla, actual)


def borrar_proyecto(proyecto_id: str) -> None:
    for t in ("coop_items", "coop_ventas", "coop_produccion", "coop_costos", "coop_registro", "coop_pagos", "coop_fondos"):
        act = cargar(t, fresco=True)
        _escribir_todo(t, act[act["ProyectoID"] != proyecto_id])
    act = cargar("coop_proyectos", fresco=True)
    _escribir_todo("coop_proyectos", act[act["ID"] != proyecto_id])


def cargar_ejemplo() -> None:
    """Carga el proyecto de ejemplo (viernes 13). Solo agrega; no borra nada."""
    from secciones.coop_ejemplo import datos_ejemplo
    for tabla, filas in datos_ejemplo().items():
        actual = cargar(tabla, fresco=True)
        nuevas = _normalizar(tabla, pd.DataFrame(filas))
        clave = "Persona" if tabla == "coop_personas" else "ID"
        nuevas = nuevas[~nuevas[clave].isin(actual[clave])]
        if not nuevas.empty:
            _escribir_todo(tabla, pd.concat([actual, nuevas], ignore_index=True))
