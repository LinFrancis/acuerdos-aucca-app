"""Capa de datos de la Cooperativa de Trabajo.

* Con credenciales de Google (st.secrets["gspread"]) guarda en hojas `coop_*` del
  mismo spreadsheet de la plataforma. Crea las hojas que falten.
* Sin credenciales (desarrollo local) guarda en `data/local_coop/*.json`.

NUNCA lee ni escribe la hoja «finanzas» de AUCCA.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st

TABLAS: dict[str, list[str]] = {
    "coop_proyectos": ["ID", "Nombre", "Tipo", "Fecha", "Estado", "Cliente", "Asistentes", "IVA",
                       "Escenario", "Descripcion"],
    "coop_items": ["ID", "ProyectoID", "Tipo", "Categoria", "Nombre", "Unidad", "Precio", "CostoUnit",
                   "CantidadPlan", "CantidadReal", "HorasPlan", "Productores", "Vendedor",
                   "PctProductor", "PctVendedor"],
    "coop_ventas": ["ID", "ProyectoID", "ItemID", "Cantidad", "PrecioUnit", "Vendedor", "Productor",
                    "Medio", "Fecha", "PorConfirmar"],
    "coop_produccion": ["ID", "ProyectoID", "ItemID", "Persona", "Cantidad", "PorConfirmar"],
    "coop_costos": ["ID", "ProyectoID", "Fecha", "Concepto", "Monto", "PagadoPor", "ItemID",
                    "ConBoleta", "Reembolsado", "PorConfirmar"],
    "coop_registro": ["ID", "ProyectoID", "Persona", "Tarea", "ItemID", "Horas", "Nivel", "Esfuerzo",
                      "Origen", "Evidencia"],
    "coop_personas": ["Persona", "ValorHora", "Ofrece", "HorasMes", "Nivel", "Notas", "PorConfirmar"],
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


# Google limita las lecturas (60 por minuto para toda la app). Por eso todas las hojas coop_* se leen
# juntas con UNA sola llamada y se guardan en memoria; al escribir, la copia en memoria se actualiza
# sin volver a leer.
_LOCK = threading.RLock()
_CACHE: dict = {"t": 0.0, "datos": {}, "ws": {}}
_TTL = 90          # segundos que se reutiliza lo leído
_TTL_FRESCO = 5    # al pedir «fresco» antes de escribir, se acepta lo leído hace menos de esto


def _reintentar(fn):
    """Reintenta ante cuota excedida (429) o fallas del servidor, esperando lo suficiente
    para que la cuota por minuto se libere."""
    from gspread.exceptions import APIError
    esperas = (5, 15, 30)
    for k in range(len(esperas) + 1):
        try:
            return fn()
        except APIError as e:
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (429, 500, 502, 503) and k < len(esperas):
                time.sleep(esperas[k])
                continue
            raise


def _refrescar() -> None:
    """Lee todas las hojas coop_* de una vez (2 llamadas), creando las que falten."""
    from data.google import _get_spreadsheet
    sh = _get_spreadsheet()
    ws = {w.title: w for w in _reintentar(lambda: sh.worksheets())}
    for t in TABLAS:
        if t not in ws:
            w = _reintentar(lambda: sh.add_worksheet(title=t, rows=200, cols=len(TABLAS[t]) + 2))
            _reintentar(lambda: w.update(values=[TABLAS[t]], range_name="A1", value_input_option="RAW"))
            ws[t] = w
    resp = _reintentar(lambda: sh.values_batch_get(list(TABLAS)))
    datos = {}
    for t, rango in zip(TABLAS, resp.get("valueRanges", [])):
        vals = rango.get("values", [])
        if not vals:
            datos[t] = _vacio(t)
            continue
        cab = [h.strip() for h in vals[0]]
        filas = [r + [""] * (len(cab) - len(r)) for r in vals[1:] if any(str(c).strip() for c in r)]
        datos[t] = _normalizar(t, pd.DataFrame(filas, columns=cab))
    _CACHE.update(t=time.time(), datos=datos, ws=ws)


def _leer_sheets(tabla: str, fresco: bool = False) -> pd.DataFrame:
    with _LOCK:
        edad = time.time() - _CACHE["t"]
        if not _CACHE["datos"] or edad > (_TTL_FRESCO if fresco else _TTL):
            try:
                _refrescar()
            except Exception:
                if not _CACHE["datos"]:
                    raise
                # sin cuota: se sigue con lo último leído y se reintenta en 15 s
                _CACHE["t"] = time.time() - _TTL + 15
        return _CACHE["datos"][tabla].copy()


def _leer_local(tabla: str) -> pd.DataFrame:
    f = _LOCAL / f"{tabla}.json"
    if not f.exists():
        return _vacio(tabla)
    return _normalizar(tabla, pd.DataFrame(json.loads(f.read_text(encoding="utf-8"))))


def cargar(tabla: str, fresco: bool = False) -> pd.DataFrame:
    if usa_sheets():
        return _leer_sheets(tabla, fresco)
    return _leer_local(tabla)


def cargar_proyecto(tabla: str, proyecto_id: str) -> pd.DataFrame:
    df = cargar(tabla)
    return df[df["ProyectoID"] == proyecto_id].reset_index(drop=True)


# ---------------------------------------------------------------- escritura
def _escribir_todo(tabla: str, df: pd.DataFrame) -> None:
    df = _normalizar(tabla, df.copy())
    if usa_sheets():
        with _LOCK:
            if tabla not in _CACHE["ws"]:
                _refrescar()
            ws = _CACHE["ws"][tabla]
            valores = [TABLAS[tabla]] + df.values.tolist()
            _reintentar(lambda: ws.clear())
            _reintentar(lambda: ws.update(values=valores, range_name="A1", value_input_option="RAW"))
            _CACHE["datos"][tabla] = df.reset_index(drop=True)
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


def sembrar_proyecto_inicial() -> None:
    """Crea el primer proyecto de la plataforma (visita del viernes 13) con lo que dicen las actas
    y estimaciones marcadas «por confirmar». Solo agrega; no borra ni pisa nada."""
    from secciones.coop_inicial import datos_proyecto_inicial
    for tabla, filas in datos_proyecto_inicial().items():
        actual = cargar(tabla, fresco=True)
        nuevas = _normalizar(tabla, pd.DataFrame(filas))
        clave = "Persona" if tabla == "coop_personas" else "ID"
        nuevas = nuevas[~nuevas[clave].isin(actual[clave])]
        if not nuevas.empty:
            _escribir_todo(tabla, pd.concat([actual, nuevas], ignore_index=True))


def instalacion_nueva() -> bool:
    """True si todavía no hay proyectos, escenarios ni horas (primera vez que se abre el módulo)."""
    return all(cargar(t).empty for t in ("coop_proyectos", "coop_parametros", "coop_registro"))


def migrar_a_datos_reales() -> bool:
    """Reemplaza las estimaciones de la primera carga por los datos reales de la visita del 13 de nov.

    Solo actúa si el registro de horas del proyecto sigue siendo exactamente el de la primera carga
    (mismos IDs y todo «Estimado»): así nunca pisa lo que alguien haya editado. Devuelve True si cambió algo.
    """
    from secciones.coop_inicial import IDS_REGISTRO_ESTIMADO, PID, datos_proyecto_inicial
    reg = cargar_proyecto("coop_registro", PID)
    if reg.empty or not set(reg["ID"]) <= IDS_REGISTRO_ESTIMADO:
        return False
    if not reg["Origen"].str.lower().str.startswith(("sim", "estim")).all():
        return False
    nuevos = datos_proyecto_inicial()
    for tabla in ("coop_items", "coop_ventas", "coop_produccion", "coop_costos", "coop_registro"):
        actual = cargar(tabla, fresco=True)
        resto = actual[actual["ProyectoID"] != PID]
        propios = _normalizar(tabla, pd.DataFrame(nuevos[tabla])) if nuevos[tabla] else _vacio(tabla)
        _escribir_todo(tabla, pd.concat([resto, propios], ignore_index=True))
    personas = cargar("coop_personas", fresco=True)
    nuevas = _normalizar("coop_personas", pd.DataFrame(nuevos["coop_personas"]))
    personas = pd.concat([personas[~personas["Persona"].isin(nuevas["Persona"])], nuevas], ignore_index=True)
    _escribir_todo("coop_personas", personas)
    proy = cargar("coop_proyectos", fresco=True)
    proy.loc[proy["ID"] == PID, "Descripcion"] = nuevos["coop_proyectos"][0]["Descripcion"]
    _escribir_todo("coop_proyectos", proy)
    completar_gobernanza_inicial()
    return True


def completar_gobernanza_inicial() -> bool:
    """Agrega las dos tensiones/propuestas surgidas de las respuestas del 24 nov (semanero y jornadas
    regulares) si el proyecto ya tiene los datos reales y todavía no están."""
    from secciones.coop_inicial import PID, datos_proyecto_inicial
    reg = cargar_proyecto("coop_registro", PID)
    if reg.empty or not reg["ID"].str.startswith("rh").any():
        return False
    gob = cargar("coop_gobernanza")
    if gob["ID"].isin(["g9", "g10"]).any():
        return False
    nuevas = _normalizar("coop_gobernanza", pd.DataFrame(datos_proyecto_inicial()["coop_gobernanza"]))
    nuevas = nuevas[nuevas["ID"].isin(["g9", "g10"])]
    _escribir_todo("coop_gobernanza", pd.concat([gob, nuevas], ignore_index=True))
    return True


def proyecto_inicial_presente() -> bool:
    from secciones.coop_inicial import PID
    return PID in cargar("coop_proyectos")["ID"].tolist()


def restaurar_proyecto_inicial() -> None:
    """Vuelve a crear el proyecto de la visita del 13 de noviembre si no está en la hoja.

    Solo agrega: si el proyecto ya tiene horas, ventas, costos u otras filas, las conserva; solo
    completa lo que falta con los datos declarados. No toca otros proyectos."""
    from secciones.coop_inicial import PID, datos_proyecto_inicial
    semilla = datos_proyecto_inicial()
    proy = cargar("coop_proyectos", fresco=True)
    if PID not in proy["ID"].tolist():
        fila = _normalizar("coop_proyectos", pd.DataFrame(semilla["coop_proyectos"]))
        _escribir_todo("coop_proyectos", pd.concat([proy, fila], ignore_index=True))
    migrar_a_datos_reales()   # si solo había estimaciones de la primera carga, las reemplaza
    for tabla in ("coop_items", "coop_ventas", "coop_produccion", "coop_costos", "coop_registro"):
        if semilla[tabla] and cargar_proyecto(tabla, PID).empty:
            actual = cargar(tabla, fresco=True)
            nuevas = _normalizar(tabla, pd.DataFrame(semilla[tabla]))
            _escribir_todo(tabla, pd.concat([actual, nuevas], ignore_index=True))
    for tabla, clave in (("coop_personas", "Persona"), ("coop_parametros", "ID"), ("coop_gobernanza", "ID")):
        actual = cargar(tabla, fresco=True)
        nuevas = _normalizar(tabla, pd.DataFrame(semilla[tabla]))
        nuevas = nuevas[~nuevas[clave].isin(actual[clave])]
        if not nuevas.empty:
            _escribir_todo(tabla, pd.concat([actual, nuevas], ignore_index=True))


def migrar_talleres_diego_camilu() -> bool:
    """Separa del bloque de horas de Diego su taller (1 h) y del de Camilú su recorrido (2 h), con la misma
    duración que declaró Tais. Solo actúa si esas dos filas siguen tal como se cargaron (8 h y 6 h)."""
    from secciones.coop_inicial import PID, datos_proyecto_inicial
    reg = cargar_proyecto("coop_registro", PID)
    if reg.empty or "rh21" in reg["ID"].tolist():
        return False
    horas = {r["ID"]: M_num(r["Horas"]) for _, r in reg.iterrows()}
    if horas.get("rh14") != 8 or horas.get("rh20") != 6:
        return False
    semilla = {r["ID"]: r for r in datos_proyecto_inicial()["coop_registro"]}
    actual = cargar("coop_registro", fresco=True)
    for rid in ("rh14", "rh20"):
        for col, val in semilla[rid].items():
            actual.loc[actual["ID"] == rid, col] = str(val)
    nuevas = _normalizar("coop_registro", pd.DataFrame([semilla["rh21"], semilla["rh22"]]))
    _escribir_todo("coop_registro", pd.concat([actual, nuevas], ignore_index=True))
    return True


def M_num(x) -> float:
    from secciones.coop_motor import num
    return num(x)


def migrar_productores_plantas() -> bool:
    """Registra quién produjo las plantas vendidas el 13: vivas → Diego, secas → Cala. Solo completa
    lo que está vacío en la hoja (ventas v1 y v2 y las líneas de plantas); no pisa lo que ya se cargó."""
    from secciones.coop_inicial import PID, datos_proyecto_inicial
    ventas = cargar("coop_ventas")
    mis = ventas[(ventas["ProyectoID"] == PID) & ventas["ID"].isin(["v1", "v2"])]
    if len(mis) != 2 or (mis["Productor"].astype(str).str.strip() != "").any():
        return False
    semilla = datos_proyecto_inicial()
    prod = {v["ID"]: v["Productor"] for v in semilla["coop_ventas"]}
    ventas = cargar("coop_ventas", fresco=True)
    for vid, quien in prod.items():
        m = (ventas["ProyectoID"] == PID) & (ventas["ID"] == vid)
        ventas.loc[m, "Productor"] = quien
        ventas.loc[m, "PorConfirmar"] = "FALSE"
    _escribir_todo("coop_ventas", ventas)
    items = cargar("coop_items", fresco=True)
    for it in semilla["coop_items"]:
        if it["ID"] in ("p-viva", "p-seca"):
            m = (items["ProyectoID"] == PID) & (items["ID"] == it["ID"]) & (items["Productores"].astype(str).str.strip() == "")
            items.loc[m, "Productores"] = it["Productores"]
    _escribir_todo("coop_items", items)
    return True
