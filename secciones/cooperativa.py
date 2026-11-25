"""Pestaña «Cooperativa de Trabajo»: proyectos, registro, resultados, simulador,
parámetros, planificación, pagos y fondos, perfiles, círculos y manual.

Toda la plata de un proyecto vive acá (hojas coop_*). Esta pestaña NO escribe en
la hoja «finanzas» de AUCCA: solo informa cuánto debe ingresarse a mano.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd
import streamlit as _st


class _ST:
    """Proxy de streamlit: escapa «$» en los textos para que los montos
    ($1.000 … $2.000) no se interpreten como fórmulas matemáticas."""

    def __getattr__(self, nombre):
        return getattr(_st, nombre)


def _escapar(nombre):
    def f(cuerpo, *a, **k):
        if isinstance(cuerpo, str):
            cuerpo = cuerpo.replace(r"\$", "$").replace("$", r"\$")
        return getattr(_st, nombre)(cuerpo, *a, **k)
    return staticmethod(f)


for _n in ("caption", "markdown", "warning", "info", "error", "success"):
    setattr(_ST, _n, _escapar(_n))
st = _ST()

from secciones import coop_datos as D
from secciones import coop_motor as M
from secciones import coop_observaciones as OBS
from secciones.finanzas_aucca import AUCCANES

ESTADOS = ["Diseño", "En ejecución", "En cierre", "Cerrado", "Anulado"]
ESTADOS_ESC = ["Borrador", "Propuesto para votar", "Acordado"]
MEDIOS = ["", "Efectivo", "Transferencia", "Pendiente de cobro"]
TIPOS_FONDO_INGRESO = ["Pago del cliente", "Venta en efectivo", "Venta por transferencia", "Otro ingreso"]
TIPOS_FONDO_EGRESO = ["Pago a persona", "Reembolso de gasto", "Costo pagado desde la caja del proyecto",
                      "Aporte entregado a AUCCA"]
TODAS_CATEGORIAS = M.CATEGORIAS_SERVICIO + M.CATEGORIAS_PRODUCTO
DOCS = Path(__file__).resolve().parent.parent / "docs"


# ------------------------------------------------------------------- helpers
def clp(x) -> str:
    try:
        v = int(round(float(x)))
        return ("-" if v < 0 else "") + "$" + f"{abs(v):,}".replace(",", ".")
    except Exception:
        return "$0"


def _bool(x) -> bool:
    return M.verdadero(x)


def _personas_opciones() -> list[str]:
    extra = [p for p in D.cargar("coop_personas")["Persona"].tolist() if p and p not in AUCCANES]
    return [""] + AUCCANES + extra


def _fila_proyecto(pid: str) -> dict:
    df = D.cargar("coop_proyectos")
    f = df[df["ID"] == pid]
    return f.iloc[0].to_dict() if not f.empty else {}


def _params_de(esc_id: str) -> dict:
    if esc_id:
        df = D.cargar("coop_parametros")
        f = df[df["ID"] == esc_id]
        if not f.empty:
            try:
                return M.params_completos(json.loads(f.iloc[0]["Parametros"]))
            except Exception:
                pass
    return M.params_completos({})


def _calcular(pid: str, params: dict) -> dict:
    return M.calcular(
        _fila_proyecto(pid), D.cargar_proyecto("coop_items", pid), D.cargar_proyecto("coop_ventas", pid),
        D.cargar_proyecto("coop_produccion", pid), D.cargar_proyecto("coop_registro", pid),
        D.cargar_proyecto("coop_costos", pid), D.cargar("coop_personas"), params)


def _selector_escenario(pid: str, key: str, proyecto: dict) -> tuple[str, dict, str]:
    esc = D.cargar("coop_parametros")
    ops = ["(parámetros base)"] + esc["Nombre"].tolist()
    ids = [""] + esc["ID"].tolist()
    idx = ids.index(proyecto.get("Escenario", "")) if proyecto.get("Escenario", "") in ids else 0
    sel = st.selectbox("Escenario de reparto", ops, index=idx, key=key,
                       help="Conjunto de parámetros (porcentajes, método, factores). Se administran en «Parámetros».")
    eid = ids[ops.index(sel)]
    estado = esc[esc["ID"] == eid]["Estado"].iloc[0] if eid else ""
    return eid, _params_de(eid), estado


def _pendientes(pid: str) -> dict:
    """Cuenta los datos que aún son estimaciones («por confirmar») en el proyecto."""
    def n(tabla):
        df = D.cargar_proyecto(tabla, pid)
        return sum(1 for v in df["PorConfirmar"] if _bool(v)) if "PorConfirmar" in df else 0
    reg = D.cargar_proyecto("coop_registro", pid)
    per = D.cargar("coop_personas")
    # se cuenta con Python y no con .sum() de pandas: en una tabla vacía .sum() devuelve texto vacío
    return {"horas": sum(1 for v in reg["Origen"] if str(v).lower().startswith(("sim", "estim"))),
            "ventas": n("coop_ventas"), "producción": n("coop_produccion"), "costos": n("coop_costos"),
            "tarifas de personas": sum(1 for v in per["PorConfirmar"] if _bool(v))}


def _aviso_por_confirmar(pid: str) -> None:
    pend = {k: v for k, v in _pendientes(pid).items() if v}
    if pend:
        detalle = ", ".join(f"{v} de {k}" for k, v in pend.items())
        st.warning(f"**Hay datos por confirmar** ({detalle}). Los montos de esta pantalla son estimaciones y cambiarán "
                   "cuando cada persona confirme lo suyo. Conviene no pagar antes de confirmarlos. "
                   "Se corrigen en «Registro» y «Personas».")


# ----------------------------------------------------- editores de tabla
def _tabla_editable(titulo: str, tabla: str, pid: str, spec: list, items: pd.DataFrame,
                    key: str, ayuda: str = "", prefijo: str = "x", solo_productos: bool = False) -> None:
    """Editor genérico. spec = [(columna, tipo, etiqueta, opciones)] con tipo
    num | bool | text | sel | persona | item."""
    df = D.cargar_proyecto(tabla, pid)
    it = items if not solo_productos else items[items["Tipo"] == "Producto"]
    nombres = it["Nombre"].tolist()
    id2n = dict(zip(items["ID"], items["Nombre"]))
    n2id = {v: k for k, v in id2n.items()}
    view = pd.DataFrame({"ID": df["ID"]})
    cfg = {"ID": None}
    for col, tipo, etiqueta, opciones in spec:
        if tipo == "num":
            view[col] = pd.to_numeric(df[col], errors="coerce")
            cfg[col] = st.column_config.NumberColumn(etiqueta)
        elif tipo == "bool":
            view[col] = df[col].map(_bool)
            cfg[col] = st.column_config.CheckboxColumn(etiqueta)
        elif tipo == "item":
            view[col] = df[col].map(lambda i: id2n.get(i, ""))
            cfg[col] = st.column_config.SelectboxColumn(etiqueta, options=[""] + nombres)
        elif tipo == "persona":
            view[col] = df[col]
            cfg[col] = st.column_config.SelectboxColumn(etiqueta, options=_personas_opciones())
        elif tipo == "sel":
            view[col] = df[col]
            cfg[col] = st.column_config.SelectboxColumn(etiqueta, options=opciones)
        else:
            view[col] = df[col]
            cfg[col] = st.column_config.TextColumn(etiqueta)
    st.markdown(f"##### {titulo}")
    if ayuda:
        st.caption(ayuda)
    editado = st.data_editor(view, column_config=cfg, num_rows="dynamic", hide_index=True,
                             use_container_width=True, key=key)
    if st.button(f"💾 Guardar {titulo.lower()}", key=f"{key}_guardar", type="primary"):
        out = pd.DataFrame({"ID": editado["ID"].fillna("")})
        for col, tipo, _, _ in spec:
            s = editado[col]
            if tipo == "bool":
                out[col] = s.map(lambda v: "TRUE" if v is True else "FALSE")
            elif tipo == "item":
                out[col] = s.map(lambda n: n2id.get(n, "") if isinstance(n, str) else "")
            elif tipo == "num":
                out[col] = s.map(lambda v: "" if pd.isna(v) else (str(int(v)) if float(v).is_integer() else str(v)))
            else:
                out[col] = s.fillna("").astype(str)
        D.guardar_proyecto(tabla, pid, out, prefijo)
        st.success("Guardado.")
        st.rerun()


# ------------------------------------------------------------- sub-secciones
def _nuevo_proyecto() -> None:
    proy = D.cargar("coop_proyectos")
    if st.toggle("➕ Crear proyecto nuevo", value=proy.empty, key="np_toggle"):
        with st.form("form_nuevo_proyecto"):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre del proyecto")
            tipo = c2.selectbox("Tipo", ["Visita / jornada", "Taller o curso", "Feria / mercadito",
                                         "Arriendo de espacio", "Asesoría", "Venta de productos", "Otro"])
            c3, c4, c5 = st.columns(3)
            fecha = c3.date_input("Fecha", value=dt.date.today())
            cliente = c4.text_input("Cliente / organizador")
            asistentes = c5.number_input("Asistentes esperados", min_value=0, step=1, value=0)
            c6, c7 = st.columns(2)
            iva = c6.selectbox("IVA", ["Por definir", "Exento", "Afecto 19%"])
            copiar = c7.selectbox("Copiar la oferta de otro proyecto (opcional)", [""] + proy["Nombre"].tolist())
            desc = st.text_area("Descripción", height=70)
            if st.form_submit_button("Crear proyecto", type="primary"):
                if not nombre.strip():
                    st.error("Ponle un nombre al proyecto.")
                else:
                    pid = D.nuevo_id("p")
                    D.guardar_fila("coop_proyectos", {
                        "ID": pid, "Nombre": nombre.strip(), "Tipo": tipo, "Fecha": str(fecha), "Estado": "Diseño",
                        "Cliente": cliente, "Asistentes": asistentes, "IVA": iva, "Descripcion": desc,
                        "Escenario": ""})
                    if copiar:
                        src = proy[proy["Nombre"] == copiar]["ID"].iloc[0]
                        _copiar_oferta(src, pid, asistentes or None, 1.0)
                    st.session_state["coop_pid"] = pid
                    st.success("Proyecto creado.")
                    st.rerun()


def _copiar_oferta(origen: str, destino: str, asistentes, escala: float) -> None:
    """Copia líneas de oferta y costos (no horas, ventas ni pagos) a un proyecto nuevo."""
    items = D.cargar_proyecto("coop_items", origen)
    nuevo_map = {i: D.nuevo_id("i") for i in items["ID"]}
    its = items.copy()
    its["ID"] = its["ID"].map(nuevo_map)
    for idx, r in its.iterrows():
        if r["Tipo"] == "Servicio":
            if asistentes:
                its.at[idx, "CantidadPlan"] = str(asistentes)
            its.at[idx, "CantidadReal"] = ""
        else:
            its.at[idx, "CantidadPlan"] = str(round(M.num(r["CantidadPlan"]) * escala, 2))
    D.guardar_proyecto("coop_items", destino, its)
    cost = D.cargar_proyecto("coop_costos", origen).copy()
    cost["ID"] = ""
    cost["ItemID"] = cost["ItemID"].map(lambda i: nuevo_map.get(i, ""))
    cost["PagadoPor"], cost["Reembolsado"], cost["PorConfirmar"] = "", "FALSE", "TRUE"
    D.guardar_proyecto("coop_costos", destino, cost, "c")


def _sec_resumen(pid: str) -> None:
    p = _fila_proyecto(pid)
    st.markdown(f"### {p['Nombre']}")
    st.caption(f"{p['Fecha']} · {p['Cliente']} · estado: **{p['Estado']}**")
    with st.form(f"ficha_{pid}"):
        c1, c2, c3 = st.columns([3, 2, 2])
        nombre = c1.text_input("Nombre", p["Nombre"])
        estado = c2.selectbox("Estado", ESTADOS, index=ESTADOS.index(p["Estado"]) if p["Estado"] in ESTADOS else 0)
        fecha = c3.text_input("Fecha (AAAA-MM-DD)", p["Fecha"])
        c4, c5, c6 = st.columns(3)
        cliente = c4.text_input("Cliente / organizador", p["Cliente"])
        asistentes = c5.number_input("Asistentes", min_value=0, step=1, value=int(M.num(p["Asistentes"])))
        ivas = ["Por definir", "Exento", "Afecto 19%"]
        iva = c6.selectbox("IVA", ivas, index=ivas.index(p["IVA"]) if p["IVA"] in ivas else 0)
        desc = st.text_area("Descripción y aprendizajes", p["Descripcion"], height=100)
        if st.form_submit_button("💾 Guardar perfil", type="primary"):
            p.update({"Nombre": nombre, "Estado": estado, "Fecha": fecha, "Cliente": cliente, "Asistentes": asistentes,
                      "IVA": iva, "Descripcion": desc})
            D.guardar_fila("coop_proyectos", p)
            st.success("Guardado.")
            st.rerun()
    items = D.cargar_proyecto("coop_items", pid)
    res = _calcular(pid, _params_de(p.get("Escenario", "")))
    r = res["resumen"]
    _checklist_proyecto(pid, p, r)
    c = st.columns(4)
    c[0].metric("Líneas de oferta", len(items))
    c[1].metric("Ingreso del proyecto", clp(r["ingreso_total"]))
    c[2].metric("Costos", clp(r["costos_total"]))
    c[3].metric("Horas registradas", f"{r['horas_totales']:g}")
    if st.toggle("⚠️ Zona de eliminación", key=f"zona_del_{pid}"):
        st.caption("Borra el proyecto y todos sus registros (oferta, ventas, horas, costos, pagos). No se puede deshacer.")
        if st.checkbox("Entiendo que es permanente", key=f"del_ok_{pid}") and st.button("Eliminar proyecto", key=f"del_{pid}"):
            D.borrar_proyecto(pid)
            st.session_state.pop("coop_pid", None)
            st.rerun()


def _checklist_proyecto(pid: str, p: dict, r: dict) -> None:
    """Qué falta para dejar el proyecto cerrado y pagado."""
    st.markdown("#### Para dejar el proyecto listo")
    pend = {k: v for k, v in _pendientes(pid).items() if v}
    esc = D.cargar("coop_parametros")
    e = esc[esc["ID"] == p.get("Escenario", "")]
    estado_esc = e.iloc[0]["Estado"] if not e.empty else ""
    pagos = D.cargar_proyecto("coop_pagos", pid)
    por_pagar = pd.to_numeric(pagos[~pagos["Pagado"].map(_bool)]["Monto"], errors="coerce").sum() if not pagos.empty else 0
    fondos = D.cargar_proyecto("coop_fondos", pid)
    entregado = pd.to_numeric(fondos[fondos["Tipo"] == "Aporte entregado a AUCCA"]["Monto"], errors="coerce").sum()
    pasos = [
        (not pend, "Confirmar los datos estimados" + (": " + ", ".join(f"{v} de {k}" for k, v in pend.items()) if pend else ""),
         "Registro / Personas"),
        (estado_esc == "Acordado", "Acordar la forma de repartir" + (f" (hoy: «{estado_esc}»)" if estado_esc else " (aún sin escenario elegido)"),
         "Simulador → Parámetros"),
        (not pagos.empty and por_pagar == 0, "Pagar a las personas" + (f" (faltan {clp(por_pagar)})" if por_pagar else ""),
         "Pagos y fondos"),
        (r["aporte_a_aucca"] > 0 and entregado >= r["aporte_a_aucca"],
         f"Entregar el aporte a AUCCA e ingresarlo en Finanzas (corresponde {clp(r['aporte_a_aucca'])}, entregado {clp(entregado)})",
         "Pagos y fondos"),
    ]
    for ok, texto_, donde in pasos:
        st.markdown(f"{'✅' if ok else '⬜'} {texto_}  \n<small>→ {donde}</small>", unsafe_allow_html=True)


def _abrir(pid: str) -> None:
    st.session_state["coop_pid"] = pid
    st.session_state["coop_sec"] = "Resumen"


def _sec_proyectos() -> None:
    st.markdown("### Proyectos de la cooperativa")
    st.caption("Cada actividad es un proyecto: se diseña, se ejecuta, se reparte y se cierra. "
               "Abre uno para ver su resumen, registrar lo que pasó y calcular los pagos.")
    proy = D.cargar("coop_proyectos")
    if not D.proyecto_inicial_presente():
        st.info("El proyecto de la **visita del viernes 13 de noviembre** no está en la hoja de datos.")
        if st.button("Cargar el proyecto de la visita del 13 de noviembre", type="primary", key="restaurar_13"):
            D.restaurar_proyecto_inicial()
            st.rerun()
    for _, p in proy.iterrows():
        res = _calcular(p["ID"], _params_de(p["Escenario"]))
        r = res["resumen"]
        pend = sum(_pendientes(p["ID"]).values())
        with st.container(border=True):
            a, b = st.columns([4, 1])
            a.markdown(f"#### {p['Nombre']}")
            a.caption(f"{p['Fecha']} · {p['Cliente'] or 'sin cliente'} · {p['Asistentes']} asistentes · "
                      f"**{p['Estado']}**" + (f" · {pend} datos por confirmar" if pend else ""))
            b.button("Abrir proyecto", key=f"abrir_{p['ID']}", type="primary", on_click=_abrir, args=(p["ID"],))
            c = st.columns(4)
            c[0].metric("Ingreso", clp(r["ingreso_total"]))
            c[1].metric("Aporte a AUCCA", clp(r["aporte_a_aucca"]))
            c[2].metric("Pago a personas", clp(r["pagos_trabajo"]))
            c[3].metric("Horas registradas", f"{r['horas_totales']:g}")
    _nuevo_proyecto()


def _sec_registro(pid: str) -> None:
    st.markdown("### Registro: qué se ofreció, vendió, produjo, gastó y trabajó")
    st.caption("Parte por «Oferta»: define las líneas del proyecto. Luego registra ventas, producción, costos y horas. "
               "Usa los mismos nombres de línea en todas las tablas.")
    items = D.cargar_proyecto("coop_items", pid)
    t = st.tabs(["Oferta", "Ventas", "Producción", "Costos", "Horas de trabajo"])
    with t[0]:
        _tabla_editable("Oferta", "coop_items", pid, [
            ("Tipo", "sel", "Tipo", ["Servicio", "Producto"]),
            ("Categoria", "sel", "Categoría", TODAS_CATEGORIAS),
            ("Nombre", "text", "Nombre de la línea", None),
            ("Unidad", "text", "Unidad (persona, unidad…)", None),
            ("Precio", "num", "Precio unitario $", None),
            ("CostoUnit", "num", "Costo unitario estimado $ (solo planificación)", None),
            ("CantidadPlan", "num", "Cantidad planificada", None),
            ("CantidadReal", "num", "Cantidad real (servicios; vacío = asistentes)", None),
            ("HorasPlan", "num", "Horas planificadas", None),
            ("Productores", "text", "Productores/as por defecto (separados por coma)", None),
            ("Vendedor", "persona", "Vendedor/a por defecto", None),
            ("PctProductor", "num", "% productor (vacío = según escenario)", None),
            ("PctVendedor", "num", "% vendedor (vacío = según escenario)", None),
        ], items, f"ed_items_{pid}", prefijo="i",
            ayuda="Servicio = se cobra al cliente y va a la bolsa de trabajo. Producto = venta directa con reparto "
                  "productor / vendedor / espacio (AUCCA). Los nombres deben ser únicos.")
        if items["Nombre"].duplicated().any():
            st.error("Hay nombres de línea repetidos. Hazlos únicos para evitar confusiones.")
    with t[1]:
        _tabla_editable("Ventas", "coop_ventas", pid, [
            ("ItemID", "item", "Producto", None), ("Cantidad", "num", "Cantidad", None),
            ("PrecioUnit", "num", "Precio unitario (vacío = el de la línea)", None),
            ("Vendedor", "persona", "Vendió", None), ("Productor", "persona", "Productor/a (vacío = según producción)", None),
            ("Medio", "sel", "Medio de pago", MEDIOS), ("Fecha", "text", "Fecha", None),
            ("PorConfirmar", "bool", "¿Por confirmar?", None)], items, f"ed_ventas_{pid}", prefijo="v", solo_productos=True,
            ayuda="Una fila por venta o grupo de ventas. Ej.: «Plantas vivas · 9 · Diego · Efectivo».")
    with t[2]:
        _tabla_editable("Producción", "coop_produccion", pid, [
            ("ItemID", "item", "Producto", None), ("Persona", "persona", "Quién lo produjo", None),
            ("Cantidad", "num", "Unidades producidas", None), ("PorConfirmar", "bool", "¿Por confirmar?", None)],
            items, f"ed_prod_{pid}", prefijo="pr", solo_productos=True,
            ayuda="Define quién hizo cuántas unidades. El % de productor se reparte según estas unidades.")
    with t[3]:
        _tabla_editable("Costos", "coop_costos", pid, [
            ("Fecha", "text", "Fecha", None), ("Concepto", "text", "Concepto", None),
            ("Monto", "num", "Monto $", None), ("PagadoPor", "persona", "Lo pagó", None),
            ("ItemID", "item", "Línea (vacío = todo el proyecto)", None),
            ("ConBoleta", "bool", "¿Con boleta/factura?", None), ("Reembolsado", "bool", "¿Ya reembolsado?", None),
            ("PorConfirmar", "bool", "¿Por confirmar?", None)], items, f"ed_costos_{pid}", prefijo="c",
            ayuda="Los costos de una línea se descuentan antes de repartir esa línea. Los del proyecto se descuentan "
                  "de la bolsa de servicios. Quien pagó de su bolsillo recibe reembolso aparte.")
    with t[4]:
        _tabla_editable("Horas de trabajo", "coop_registro", pid, [
            ("Persona", "persona", "Persona", None), ("Tarea", "text", "Tarea", None),
            ("ItemID", "item", "Línea (vacío = tarea de base: baños, orden, logística…)", None),
            ("Horas", "num", "Horas", None), ("Nivel", "sel", "Nivel (1–4)", ["1", "2", "3", "4"]),
            ("Esfuerzo", "sel", "Esfuerzo (1–5, opcional)", ["", "1", "2", "3", "4", "5"]),
            ("Origen", "sel", "Origen del dato", ["Real", "Estimado"]), ("Evidencia", "text", "Evidencia (enlace a audio/foto)", None)],
            items, f"ed_reg_{pid}", prefijo="r",
            ayuda="Incluye TODO: preparar, comprar, cocinar, guiar, ordenar, limpiar, difundir. Nivel: 1 operación · "
                  "2 técnico · 3 diseño/facilitación · 4 dirección. Las horas en líneas de producto no entran a la bolsa: "
                  "se pagan por el % productor/vendedor.")


def _describir_escenario(prm: dict, notas: str = "") -> str:
    """Texto corto y claro de qué configura un escenario."""
    m = prm["metodo"]
    if m == "A":
        met = "La bolsa de trabajo se reparte según las **horas** que trabajó cada persona, sin distinguir el tipo de tarea."
    elif m == "B":
        fac = ", ".join(f"nivel {n} ×{f:g}".replace(".", ",") for n, f in prm["factores_nivel"].items())
        met = ("Las horas se multiplican por un factor según el **nivel de responsabilidad** de la tarea "
               f"({fac}) y la bolsa se reparte según esos puntos.")
    elif m == "C":
        mz = prm["mezcla_c"]
        tot = sum(mz.values()) or 1
        met = (f"Mezcla de tres criterios: **{mz['igual'] / tot * 100:.0f}% en partes iguales**, "
               f"**{mz['horas'] / tot * 100:.0f}% por horas** y **{mz['puntos'] / tot * 100:.0f}% por puntos** de responsabilidad.")
    elif m == "D":
        met = ("Cada **línea de servicio** aporta su propio resultado a la bolsa: "
               f"el {prm['pct_bolsa_base_d']:g}% se comparte entre todas las personas según las horas de tareas de base "
               "y el resto va a quienes trabajaron en esa línea.")
    elif m == "E":
        met = "La bolsa se reparte en **partes iguales** entre las personas que tienen horas registradas."
    else:
        met = ("La bolsa se reparte según **horas × valor de hora declarado** de cada persona "
               f"({clp(prm['tarifa_defecto'])} por hora si alguien no declaró el suyo).")
    res_ = (f" Antes de repartir, el {prm['pct_espacio']:g}% del margen de servicios va al espacio (AUCCA) y el "
            f"{prm['pct_fondo_comun']:g}% al fondo común.")
    pr = {(v["prod"], v["vend"], v["espacio"]) for v in prm["productos"].values()}
    if len(pr) == 1:
        a, b, c = next(iter(pr))
        prod = f" Las plantas y productos se reparten aparte: {a:g}% quien produjo, {b:g}% quien vendió y {c:g}% el espacio (AUCCA)."
    else:
        prod = " Las plantas y productos se reparten aparte, con porcentajes que varían según la categoría."
    extra = f" Idea del grupo: {notas.strip()}" if notas and notas.strip() else ""
    return met + res_ + prod + extra


def _explicar_columnas() -> None:
    st.markdown("#### Cómo leer las tablas")
    col = pd.DataFrame([
        ("Horas", "Horas declaradas en tareas de servicios y de base (preparar, guiar, cocinar, ordenar). Las horas en el puesto "
                  "de plantas no cuentan aquí: se reconocen con el % de quien produjo y de quien vendió."),
        ("Recibe por su trabajo", "Lo que le toca de la bolsa de trabajo según el método del escenario, más lo que le corresponde "
                                  "como productor/a o vendedor/a de plantas. No incluye reembolsos."),
        ("Reembolso de gastos", "Plata que puso de su bolsillo y todavía no le devuelven. Se le devuelve entera; no es ganancia."),
        ("Total a recibir", "Recibe por su trabajo + reembolso de gastos."),
        ("Aportó ($)", "Valor en ventas de lo que ayudó a generar: el ingreso de cada línea de servicio en que trabajó, "
                       "repartido según sus horas, más el valor de las plantas que produjo. Las tareas de base no suman. "
                       "Quien tiene horas sin línea asignada o sin producción registrada aparece con un aporte menor al real."),
        ("% de lo generado", "Su «Aportó» dividido por el ingreso total del proyecto (servicios más plantas)."),
        ("Ingreso de servicios en que trabajó", "Parte del ingreso de las líneas de servicio (recorrido, snack, talleres, "
                                                "empanadas) que corresponde a sus horas en ellas."),
        ("Ingreso de productos que produjo", "Valor de las plantas y productos vendidos que esa persona produjo."),
        ("Vendió ($)", "Total de plantas y productos que vendió, sin importar quién los produjo."),
        ("Gastos que puso", "Compras o traslados que pagó de su bolsillo para la actividad."),
        ("Para AUCCA", "Dinero que corresponde al espacio: reserva sobre los servicios más su parte de las plantas. "
                       "Se ingresa a mano en Finanzas."),
        ("Fondo común", "Reserva del proyecto para imprevistos; queda en custodia hasta que el grupo decida su uso."),
        ("Sin asignar", "Dinero de plantas cuyo productor/a o vendedor/a todavía no está registrado."),
    ], columns=["Columna", "Qué significa"])
    st.dataframe(col, hide_index=True, use_container_width=True)


def _observaciones(lista: list[str]) -> None:
    """Notas para entender la tabla de arriba."""
    if lista:
        st.markdown("**Observaciones para entender los datos**\n\n" + "\n".join(f"- {t}" for t in lista))


def _resumen_ingresado(pid: str, personas: pd.DataFrame, r: dict) -> None:
    """Contexto: lo que ingresó y puso cada persona, antes de comparar escenarios."""
    st.markdown("#### Contexto: lo que ingresó y puso cada persona")
    if personas.empty:
        st.info("Aún no hay personas con horas, ventas o producción registradas.")
        return
    gastos: dict[str, float] = {}
    for _, f in D.cargar_proyecto("coop_costos", pid).iterrows():
        quien = str(f["PagadoPor"]).strip()
        if quien:
            gastos[quien] = gastos.get(quien, 0.0) + M.num(f["Monto"])
    v = personas[["Persona", "Horas", "Aporte en servicios ($)", "Aporte en productos ($)", "Vendió ($)",
                  "Aporte total ($)", "Reembolso de gastos"]].copy()
    v.insert(6, "Gastos que puso", v["Persona"].map(lambda x: round(gastos.get(x, 0.0))))
    num_cols = [c for c in v.columns if c != "Persona"]
    v = v[(v[num_cols] != 0).any(axis=1)]
    tot = {c: v[c].sum() for c in num_cols}
    v = pd.concat([v, pd.DataFrame([{"Persona": "TOTAL", **tot}])], ignore_index=True)
    for c in num_cols:
        v[c] = v[c].map(lambda x: f"{x:g}") if c == "Horas" else v[c].map(clp)
    v = v.rename(columns={"Aporte en servicios ($)": "Ingreso de servicios en que trabajó",
                          "Aporte en productos ($)": "Ingreso de productos que produjo",
                          "Aporte total ($)": "Aportó ($)", "Reembolso de gastos": "Pendiente de devolver"})
    st.dataframe(v, hide_index=True, use_container_width=True)
    st.caption("Es el punto de partida, igual en todos los escenarios: lo que cada persona trabajó, generó, vendió y puso de su "
               "bolsillo. Más abajo se ve cómo cambia lo que recibe según cada forma de repartir.")
    _observaciones(OBS.obs_contexto(personas, r, D.cargar_proyecto("coop_registro", pid),
                                    D.cargar_proyecto("coop_costos", pid)))


def _resultados_todos(pid: str, p: dict) -> None:
    """Una tabla por escenario: cuánto recibe cada persona y cuánto aportó, para comparar lado a lado."""
    esc = D.cargar("coop_parametros")
    if esc.empty:
        escenarios = [("", "Parámetros base", "")]
    else:
        escenarios = [(r["ID"], r["Nombre"], r["Estado"]) for _, r in esc.iterrows()]
    notas_esc = dict(zip(esc["ID"], esc["Notas"])) if not esc.empty else {}
    calculos = []
    for eid, nombre, estado in escenarios:
        prm = _params_de(eid)
        calculos.append((eid, nombre, estado, prm, _calcular(pid, prm)))

    _resumen_ingresado(pid, calculos[0][4]["personas"], calculos[0][4]["resumen"])
    _explicar_columnas()

    # comparación rápida: total que recibiría cada persona en cada escenario
    st.markdown("#### Resumen: cuánto recibiría cada persona según el escenario")
    base = {}
    for _, nombre, _e, _prm, res in calculos:
        for _, f in res["personas"].iterrows():
            base.setdefault(f["Persona"], {})[nombre] = f["Total a recibir"]
    if base:
        comp = pd.DataFrame(base).T.fillna(0)
        comp = comp.loc[(comp != 0).any(axis=1)]
        comp_num = comp.copy()
        comp.loc["TOTAL"] = comp.sum()
        comp = comp.reset_index().rename(columns={"index": "Persona"})
        for c in comp.columns[1:]:
            comp[c] = comp[c].map(clp)
        st.dataframe(comp, hide_index=True, use_container_width=True)
        st.caption("Incluye reembolsos de gastos. Abajo está el detalle de cada escenario.")
        _observaciones(OBS.obs_comparativo(comp_num, [c[4]["resumen"]["pagos_trabajo"] for c in calculos]))
    else:
        st.info("Aún no hay personas con horas, ventas o producción registradas.")

    largo = []
    for eid, nombre, estado, prm, res in calculos:
        r = res["resumen"]
        pers = res["personas"]
        with st.container(border=True):
            st.markdown(f"#### {nombre}")
            st.markdown(_describir_escenario(prm, notas_esc.get(eid, "")))
            st.caption(f"{('Estado: **' + estado + '** · ') if estado else ''}método: **{M.METODOS[r['metodo']]}**")
            if pers.empty:
                st.info("Sin personas con horas, ventas o producción.")
            else:
                v = pers[["Persona", "Horas", "Pago por trabajo", "Reembolso de gastos", "Total a recibir",
                          "Aporte total ($)", "% del ingreso generado"]].copy()
                v = v[(v[["Horas", "Pago por trabajo", "Reembolso de gastos", "Total a recibir", "Aporte total ($)"]] != 0)
                      .any(axis=1)]
                for _, f in v.iterrows():
                    largo.append({"Escenario": nombre, **f.to_dict()})
                tot = {c: v[c].sum() for c in v.columns if c != "Persona"}
                v = pd.concat([v, pd.DataFrame([{"Persona": "TOTAL", **tot}])], ignore_index=True)
                for c in ("Pago por trabajo", "Reembolso de gastos", "Total a recibir", "Aporte total ($)"):
                    v[c] = v[c].map(clp)
                v["Horas"] = v["Horas"].map(lambda x: f"{x:g}")
                v["% del ingreso generado"] = v["% del ingreso generado"].map(lambda x: f"{x:.1f} %")
                v = v.rename(columns={"Pago por trabajo": "Recibe por su trabajo", "Aporte total ($)": "Aportó ($)",
                                      "% del ingreso generado": "% de lo generado"})
                st.dataframe(v, hide_index=True, use_container_width=True)
            est = D.cargar("coop_personas")
            est = est[est["PorConfirmar"].map(_bool)]["Persona"].tolist()
            _observaciones(OBS.obs_escenario(prm, res, [x for x in est if x in pers["Persona"].tolist()
                                                         and pers.set_index("Persona").loc[x, "Horas"] > 0]))
            st.caption(f"Para AUCCA: **{clp(r['aporte_a_aucca'])}** · fondo común: **{clp(r['fondo_comun'])}**"
                       + (f" · sin asignar: **{clp(r['sin_asignar'])}**" if r["sin_asignar"] else "")
                       + ("" if res["balance_ok"] else " · ⚠️ la cuadratura no cierra"))
    if largo:
        st.download_button("⬇️ Descargar todos los escenarios (CSV)",
                           pd.DataFrame(largo).to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"escenarios_{p['Nombre']}.csv", mime="text/csv")
    st.caption("Para ver las cascadas del dinero y las líneas de un escenario, elige «Un escenario en detalle».")


def _sec_resultados(pid: str) -> None:
    p = _fila_proyecto(pid)
    st.markdown("### Resultados: cuánto recibe cada persona y cuánto aportó")
    modo = st.radio("Ver", ["Todos los escenarios", "Un escenario en detalle"], horizontal=True,
                    label_visibility="collapsed", key=f"res_modo_{pid}")
    if modo == "Todos los escenarios":
        _aviso_por_confirmar(pid)
        _resultados_todos(pid, p)
        return
    eid, params, estado = _selector_escenario(pid, f"esc_res_{pid}", p)
    res = _calcular(pid, params)
    r = res["resumen"]
    _aviso_por_confirmar(pid)
    if estado:
        st.caption(f"Escenario «{estado}» · método: **{M.METODOS[r['metodo']]}**")
    else:
        st.caption(f"Parámetros base · método: **{M.METODOS[r['metodo']]}**")
    for a in res["alertas"]:
        st.warning(a)
    c = st.columns(4)
    c[0].metric("Ingreso total", clp(r["ingreso_total"]), help="Servicios al cliente + ventas de productos")
    c[1].metric("Costos directos", clp(r["costos_total"]))
    c[2].metric("Pago por trabajo a personas", clp(r["pagos_trabajo"]))
    c[3].metric("Reembolsos de gastos", clp(r["reembolsos"]))

    with st.container(border=True):
        st.markdown("#### 💜 Para ingresar manualmente a AUCCA")
        st.metric("Dinero que corresponde a AUCCA", clp(r["aporte_a_aucca"]))
        st.caption(f"= reserva de espacio sobre servicios **{clp(r['reserva_espacio'])}** + parte «espacio» de las ventas de "
                   f"productos **{clp(r['productos_a_espacio'])}**. Esta plataforma **no** modifica Finanzas: cuando el dinero "
                   "llegue efectivamente a AUCCA, regístralo tú en la pestaña Finanzas. El resto del dinero del proyecto "
                   "no es de AUCCA.")
        st.caption(f"El fondo común de {clp(r['fondo_comun'])} queda en custodia del proyecto hasta que el grupo decida su uso.")

    st.markdown("#### Cascada del dinero")
    casc = pd.DataFrame([
        ("Ingresos por servicios al cliente", r["ingreso_servicios"]),
        ("− Costos de los servicios y del proyecto", -(r["ingreso_servicios"] - r["margen_servicios"])),
        ("= Margen de servicios", r["margen_servicios"]),
        (f"→ Reserva de espacio (AUCCA) {params['pct_espacio']:g}%", r["reserva_espacio"]),
        (f"→ Fondo común {params['pct_fondo_comun']:g}%", r["fondo_comun"]),
        ("→ Bolsa de trabajo (se reparte por el método)", r["excedente_bolsa"]),
    ], columns=["Concepto", "Monto"])
    casc["Monto"] = casc["Monto"].map(clp)
    st.dataframe(casc, hide_index=True, use_container_width=True)
    st.caption("El margen de servicios ya descuenta los costos de proyecto que no pertenecen a una línea. "
               "Los productos se reparten aparte, venta a venta (tabla de líneas más abajo).")

    pers = res["personas"]
    t = st.tabs(["Cuánto recibe", "Cuánto aportó", "Líneas del proyecto"])
    with t[0]:
        if pers.empty:
            st.info("Aún no hay personas con horas, ventas o producción registradas.")
        else:
            v = pers[["Persona", "Horas", "Bolsa de trabajo", "Como productor/a", "Como vendedor/a", "Pago por trabajo",
                      "Reembolso de gastos", "Total a recibir"]].copy()
            tot = {c: v[c].sum() for c in v.columns if c not in ("Persona",)}
            v = pd.concat([v, pd.DataFrame([{"Persona": "TOTAL", **tot}])], ignore_index=True)
            for c in v.columns[2:]:
                v[c] = v[c].map(clp)
            st.dataframe(v, hide_index=True, use_container_width=True)
            st.caption("«Bolsa de trabajo» sale del método elegido. «Como productor/a» y «Como vendedor/a» salen de las "
                       "ventas de productos. El reembolso devuelve lo que alguien puso de su bolsillo; no es ganancia.")
    with t[1]:
        if not pers.empty:
            v = pers[["Persona", "Horas", "Horas en productos", "Unidades producidas", "Unidades vendidas",
                      "Aporte en servicios ($)", "Aporte en productos ($)", "Aporte total ($)",
                      "% del ingreso generado", "Vendió ($)"]].copy()
            st.dataframe(v, hide_index=True, use_container_width=True,
                         column_config={"% del ingreso generado": st.column_config.NumberColumn(format="%.1f %%")})
            st.caption("Aporte = valor de lo que generó con su trabajo: ingreso de las líneas de servicio en que trabajó "
                       "(según sus horas) + ingreso de los productos que produjo. Las tareas de base (baños, orden, "
                       "logística) no generan ingreso directo: se ven en las horas.")
            graf = pers.set_index("Persona")[["Pago por trabajo", "Aporte total ($)"]]
            st.bar_chart(graf)
    with t[2]:
        l = res["lineas"].drop(columns=["ID"], errors="ignore")
        for c in ["Ingreso", "Costo", "A productores", "A vendedores", "A AUCCA (espacio)"]:
            if c in l.columns:
                l[c] = l[c].map(lambda x: clp(x) if pd.notna(x) else "")
        st.dataframe(l, hide_index=True, use_container_width=True)
    if not res["balance_ok"]:
        st.error(f"La cuadratura no cierra (diferencia {clp(r['diferencia_cuadratura'])}). Revisa los datos.")
    else:
        st.caption(f"✅ Cuadratura: AUCCA {clp(r['aporte_a_aucca'])} + fondo común {clp(r['fondo_comun'])} + pagos a personas "
                   f"{clp(r['pagos_trabajo'])} + sin asignar {clp(r['sin_asignar'])} = ingresos − costos "
                   f"({clp(r['ingreso_total'] - r['costos_total'])}).")
    if not pers.empty:
        st.download_button("⬇️ Descargar resultados (CSV)", pers.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"resultados_{p['Nombre']}.csv", mime="text/csv")


def _form_parametros(base: dict, key: str) -> dict:
    p = M.params_completos(base)
    c1, c2 = st.columns(2)
    metodos = list(M.METODOS)
    metodo = c1.selectbox("Método de reparto de la bolsa de trabajo", metodos, index=metodos.index(p["metodo"]),
                          format_func=lambda k: M.METODOS[k], key=f"{key}_m")
    c2.markdown("&nbsp;")
    c3, c4 = st.columns(2)
    pe = c3.slider("% del margen de servicios para AUCCA (espacio e infraestructura)", 0.0, 50.0,
                   float(p["pct_espacio"]), 0.5, key=f"{key}_pe")
    pf = c4.slider("% para fondo común / imprevistos", 0.0, 40.0, float(p["pct_fondo_comun"]), 0.5, key=f"{key}_pf")
    if pe + pf >= 100:
        st.error("Las reservas no pueden sumar 100% o más.")
    st.markdown("**Mezcla del método C** (se normaliza a 100)")
    d1, d2, d3 = st.columns(3)
    mi = d1.slider("Partes iguales", 0, 100, int(p["mezcla_c"]["igual"]), key=f"{key}_mi")
    mh = d2.slider("Por horas", 0, 100, int(p["mezcla_c"]["horas"]), key=f"{key}_mh")
    mp = d3.slider("Por puntos", 0, 100, int(p["mezcla_c"]["puntos"]), key=f"{key}_mp")
    st.markdown("**Factor por nivel de responsabilidad** (puntos = horas × factor)")
    f = st.columns(4)
    fac = {n: f[i].number_input(M.NIVELES[n], 0.5, 3.0, float(p["factores_nivel"][n]), 0.05, key=f"{key}_f{n}")
           for i, n in enumerate(["1", "2", "3", "4"])}
    g1, g2, g3 = st.columns(3)
    bb = g1.slider("Método D: % de cada línea que se comparte entre todas las personas", 0, 60,
                   int(p["pct_bolsa_base_d"]), key=f"{key}_bb")
    td = g2.number_input("Método F: tarifa/hora por defecto $", 0, 100000, int(p["tarifa_defecto"]), 500, key=f"{key}_td")
    vr = g3.number_input("Tarifa/hora de referencia (planificación) $", 0, 100000, int(p["valor_hora_ref"]), 500,
                         key=f"{key}_vr", help="Piso pedagógico propuesto: $20.000 por hora.")
    st.markdown("**Reparto de productos por categoría** (venta directa)")
    dfp = pd.DataFrame([{"Categoría": c, "% productor/es": v["prod"], "% vendedor/a": v["vend"], "% espacio (AUCCA)": v["espacio"]}
                        for c, v in p["productos"].items()])
    ed = st.data_editor(dfp, hide_index=True, use_container_width=True, key=f"{key}_prod",
                        disabled=["Categoría"])
    prods = {}
    for _, r in ed.iterrows():
        prods[r["Categoría"]] = {"prod": float(r["% productor/es"]), "vend": float(r["% vendedor/a"]),
                                 "espacio": float(r["% espacio (AUCCA)"])}
        if abs(r["% productor/es"] + r["% vendedor/a"] + r["% espacio (AUCCA)"] - 100) > 0.01:
            st.warning(f"«{r['Categoría']}»: los porcentajes no suman 100. El resto queda como espacio (AUCCA).")
    return {"metodo": metodo, "pct_espacio": pe, "pct_fondo_comun": pf,
            "mezcla_c": {"igual": mi, "horas": mh, "puntos": mp}, "factores_nivel": fac,
            "pct_bolsa_base_d": bb, "tarifa_defecto": td, "valor_hora_ref": vr, "productos": prods}


def _sec_parametros(pid: str) -> None:
    st.markdown("### Panel de parámetros y escenarios")
    st.caption("Un escenario es una forma de repartir (porcentajes, método, factores). Crea varios (Opción 1, 2, 3…), "
               "compáralos en «Simulador» y marca como «Acordado» el que el grupo elija.")
    esc = D.cargar("coop_parametros")
    ops = ["➕ Nuevo escenario"] + esc["Nombre"].tolist()
    sel = st.selectbox("Escenario", ops, key=f"pa_sel_{pid}")
    fila = esc[esc["Nombre"] == sel].iloc[0].to_dict() if sel in esc["Nombre"].values else {}
    base = _params_de(fila.get("ID", "")) if fila else M.params_completos({})
    k = f"pa_{fila.get('ID', 'nuevo')}"
    c1, c2 = st.columns([3, 2])
    nombre = c1.text_input("Nombre del escenario", fila.get("Nombre", ""), key=f"{k}_n")
    estado = c2.selectbox("Estado", ESTADOS_ESC, index=ESTADOS_ESC.index(fila["Estado"]) if fila.get("Estado") in ESTADOS_ESC else 0,
                          key=f"{k}_e")
    notas = st.text_input("Notas (por qué esta opción, quién la propuso)", fila.get("Notas", ""), key=f"{k}_no")
    params = _form_parametros(base, k)
    b1, b2, b3, b4 = st.columns(4)
    if b1.button("💾 Guardar escenario", type="primary", key=f"{k}_save"):
        if not nombre.strip():
            st.error("Ponle un nombre.")
        else:
            D.guardar_fila("coop_parametros", {"ID": fila.get("ID", ""), "Nombre": nombre.strip(), "Estado": estado,
                                               "Notas": notas, "Parametros": json.dumps(params, ensure_ascii=False),
                                               "Actualizado": dt.datetime.now().strftime("%Y-%m-%d %H:%M")})
            st.success("Escenario guardado.")
            st.rerun()
    if fila and b2.button("📄 Duplicar", key=f"{k}_dup"):
        D.guardar_fila("coop_parametros", {"ID": "", "Nombre": f"{fila['Nombre']} (copia)", "Estado": "Borrador",
                                           "Notas": notas, "Parametros": json.dumps(params, ensure_ascii=False),
                                           "Actualizado": dt.datetime.now().strftime("%Y-%m-%d %H:%M")})
        st.rerun()
    if fila and b3.button("✅ Usar en este proyecto", key=f"{k}_use"):
        p = _fila_proyecto(pid)
        p["Escenario"] = fila["ID"]
        D.guardar_fila("coop_proyectos", p)
        st.success("Escenario asignado al proyecto.")
        st.rerun()
    if fila:
        if b4.checkbox("Eliminar este escenario", key=f"{k}_delok"):
            if st.button("🗑️ Confirmo: eliminar escenario", key=f"{k}_del"):
                D.guardar_tabla("coop_parametros", esc[esc["ID"] != fila["ID"]])
                st.rerun()


def _sec_simulador(pid: str) -> None:
    p = _fila_proyecto(pid)
    st.markdown("### Simulador: compara formas de repartir")
    st.caption("Mueve los parámetros y mira al instante cuánto recibiría cada persona con cada método. "
               "Nada se guarda hasta que lo guardas como escenario.")
    eid, base, _ = _selector_escenario(pid, f"esc_sim_{pid}", p)
    params = base
    if st.toggle("Ajustar parámetros de esta simulación", key=f"sim_tog_{pid}"):
        params = _form_parametros(base, f"sim_{pid}_{eid}")
    res = _calcular(pid, params)
    _aviso_por_confirmar(pid)
    comp = res["comparacion"]
    if comp.empty:
        st.info("Registra horas, ventas o producción para simular.")
        return
    etiquetas = {"A": "A · Horas", "B": "B · Puntos", "C": "C · Mixta", "D": "D · Por línea",
                 "E": "E · Iguales", "F": "F · Tarifa"}
    c = comp.set_index("Persona").rename(columns=etiquetas)
    c["Mínimo"] = c.min(axis=1)
    c["Máximo"] = c.max(axis=1)
    c["Diferencia máx. entre métodos"] = c["Máximo"] - c["Mínimo"]
    st.markdown("#### Pago por trabajo según cada método")
    show = c.copy().drop(columns=["Mínimo", "Máximo"])
    tot = show.sum().to_frame().T
    tot.index = ["TOTAL"]
    show = pd.concat([show, tot]).map(clp)
    st.dataframe(show, use_container_width=True)
    graf = c.drop(columns=["Mínimo", "Máximo", "Diferencia máx. entre métodos"])
    try:
        st.bar_chart(graf, stack=False)
    except TypeError:
        st.bar_chart(graf)
    prom = c["Diferencia máx. entre métodos"].mean()
    st.caption(f"La diferencia promedio entre el método más favorable y el menos favorable por persona es {clp(prom)}. "
               "Eso es lo que está en juego al elegir el criterio.")
    with st.container(border=True):
        nom = st.text_input("Guardar esta simulación como escenario nuevo", placeholder="Ej.: Opción 3 · 60% horas, 40% igual",
                            key=f"sim_nom_{pid}")
        if st.button("💾 Guardar como escenario", key=f"sim_save_{pid}") and nom.strip():
            D.guardar_fila("coop_parametros", {"ID": "", "Nombre": nom.strip(), "Estado": "Borrador", "Notas": "Desde el simulador",
                                               "Parametros": json.dumps(params, ensure_ascii=False),
                                               "Actualizado": dt.datetime.now().strftime("%Y-%m-%d %H:%M")})
            st.success("Guardado en «Parámetros».")


def _sec_planificar(pid: str) -> None:
    p = _fila_proyecto(pid)
    st.markdown("### Planificar una actividad futura")
    st.caption("Usa la oferta y los costos de este proyecto como plantilla. Cambia asistentes y cantidades y mira "
               "ingresos, costos, valor por hora y qué conviene ofrecer. Para cambiar precios o costos edita «Registro → Oferta».")
    eid, params, _ = _selector_escenario(pid, f"esc_plan_{pid}", p)
    c1, c2 = st.columns(2)
    asis = c1.slider("Asistentes", 0, 150, int(M.num(p["Asistentes"])) or 20, key=f"pl_a_{pid}")
    escala = c2.slider("Escala de productos (1,0 = cantidades planificadas)", 0.0, 3.0, 1.0, 0.1, key=f"pl_e_{pid}")
    items = D.cargar_proyecto("coop_items", pid)
    if items.empty:
        st.info("Define primero la oferta en «Registro → Oferta».")
        return
    plan = M.calcular_plan(p, items, D.cargar_proyecto("coop_costos", pid), D.cargar("coop_personas"), params, asis, escala)
    r = plan["resumen"]
    c = st.columns(4)
    c[0].metric("Ingreso proyectado", clp(r["ingreso_total"]))
    c[1].metric("Costos proyectados", clp(r["costos_total"]))
    c[2].metric("Aporte a AUCCA", clp(r["aporte_a_aucca"]))
    c[3].metric("Bolsa de trabajo", clp(r["excedente_bolsa"]))
    c = st.columns(3)
    c[0].metric("Horas planificadas", f"{r['horas_plan']:g}")
    c[1].metric("Valor por hora estimado", clp(r["valor_hora_estimado"]),
                delta=clp(r["valor_hora_estimado"] - r["valor_hora_ref"]) + " vs referencia")
    c[2].metric("Tarifa/hora de referencia", clp(r["valor_hora_ref"]))
    if r["horas_plan"] and r["valor_hora_estimado"] < r["valor_hora_ref"]:
        st.warning("Con estos supuestos la hora de trabajo queda por debajo de la tarifa de referencia: "
                   "sube precios, baja costos o reduce horas.")
    st.markdown("#### ¿Conviene ofrecerlo? (resultado por línea)")
    rt = plan["rentabilidad"].copy()
    for c_ in ["Ingreso", "Costos directos", "Horas a tarifa de referencia", "Resultado"]:
        rt[c_] = rt[c_].map(clp)
    st.dataframe(rt, hide_index=True, use_container_width=True)
    st.caption("Resultado = ingreso − costos directos − horas valoradas a la tarifa de referencia. "
               "Negativo = esa línea no se paga sola con estos supuestos (puede ser aceptable si tiene otros fines).")
    eq = plan["equilibrio"]
    if not eq.empty:
        st.markdown("#### Punto de equilibrio de los servicios")
        eq = eq.copy()
        for c_ in ("Precio por persona", "Costos de la línea"):
            eq[c_] = eq[c_].map(clp)
        st.dataframe(eq, hide_index=True, use_container_width=True)
        st.caption("«Asistentes mínimos» = personas necesarias para que la línea pague sus costos y sus horas a la tarifa de "
                   "referencia, después de las reservas de espacio y fondo común.")
    if st.toggle("➕ Crear un proyecto nuevo con estos supuestos", key=f"pl_tog_{pid}"):
        nom = st.text_input("Nombre del nuevo proyecto", value=f"{p['Nombre']} (próxima versión)", key=f"pl_n_{pid}")
        if st.button("Crear proyecto", key=f"pl_c_{pid}", type="primary"):
            nid = D.nuevo_id("p")
            D.guardar_fila("coop_proyectos", {"ID": nid, "Nombre": nom, "Tipo": p["Tipo"], "Fecha": "", "Estado": "Diseño",
                                              "Cliente": "", "Asistentes": asis, "IVA": p["IVA"],
                                              "Descripcion": f"Basado en «{p['Nombre']}».", "Escenario": eid})
            _copiar_oferta(pid, nid, asis, escala)
            st.session_state["coop_pid"] = nid
            st.rerun()


def _sec_pagos(pid: str) -> None:
    p = _fila_proyecto(pid)
    st.markdown("### Pagos y fondos del proyecto")
    st.info("**El dinero de un proyecto NO es dinero de AUCCA.** Vive acá, en custodia, hasta que se paga a las personas. "
            "Solo el «Aporte a AUCCA» pasa a ser de AUCCA, y eso lo ingresas tú manualmente en Finanzas.")
    eid, params, _ = _selector_escenario(pid, f"esc_pag_{pid}", p)
    res = _calcular(pid, params)
    r = res["resumen"]
    t = st.tabs(["Pagos a personas", "Caja del proyecto", "Aporte a AUCCA"])
    with t[0]:
        pagos = D.cargar_proyecto("coop_pagos", pid)
        if st.button("🔄 Generar / actualizar pagos desde el escenario", key=f"pg_gen_{pid}"):
            nuevos = []
            for _, f in res["personas"].iterrows():
                for concepto, monto in (("Pago por trabajo", f["Pago por trabajo"]), ("Reembolso de gastos", f["Reembolso de gastos"])):
                    if monto > 0:
                        nuevos.append({"ID": "", "Persona": f["Persona"], "Concepto": concepto, "Monto": str(int(monto)),
                                       "Pagado": "FALSE", "FechaPago": "", "Medio": "", "Nota": ""})
            nu = pd.DataFrame(nuevos)
            if not pagos.empty and not nu.empty:
                hechos = pagos[pagos["Pagado"].map(_bool)]
                for _, h in hechos.iterrows():
                    nu = nu[~((nu["Persona"] == h["Persona"]) & (nu["Concepto"] == h["Concepto"]))]
                nu = pd.concat([hechos[nu.columns.intersection(hechos.columns)], nu], ignore_index=True)
            D.guardar_proyecto("coop_pagos", pid, nu if not nu.empty else pd.DataFrame(columns=D.TABLAS["coop_pagos"]), "pg")
            st.rerun()
        pagos = D.cargar_proyecto("coop_pagos", pid)
        view = pagos[["ID", "Persona", "Concepto", "Monto", "Pagado", "FechaPago", "Medio", "Nota"]].copy()
        view["Monto"] = pd.to_numeric(view["Monto"], errors="coerce")
        view["Pagado"] = view["Pagado"].map(_bool)
        ed = st.data_editor(view, hide_index=True, use_container_width=True, num_rows="dynamic", key=f"pg_ed_{pid}", column_config={
            "ID": None, "Persona": st.column_config.SelectboxColumn(options=_personas_opciones()),
            "Concepto": st.column_config.SelectboxColumn(options=["Pago por trabajo", "Reembolso de gastos", "Otro"]),
            "Monto": st.column_config.NumberColumn("Monto $"), "Pagado": st.column_config.CheckboxColumn("¿Pagado?"),
            "FechaPago": st.column_config.TextColumn("Fecha de pago"),
            "Medio": st.column_config.SelectboxColumn(options=["", "Efectivo", "Transferencia"])})
        if st.button("💾 Guardar pagos", type="primary", key=f"pg_save_{pid}"):
            o = ed.copy()
            o["Pagado"] = o["Pagado"].map(lambda v: "TRUE" if v is True else "FALSE")
            o["Monto"] = o["Monto"].map(lambda v: "" if pd.isna(v) else str(int(v)))
            D.guardar_proyecto("coop_pagos", pid, o.fillna(""), "pg")
            st.success("Guardado.")
            st.rerun()
        tot = pd.to_numeric(ed["Monto"], errors="coerce").fillna(0)
        pagado = tot[ed["Pagado"] == True].sum()  # noqa: E712
        c = st.columns(3)
        c[0].metric("Total a pagar", clp(tot.sum()))
        c[1].metric("Ya pagado", clp(pagado))
        c[2].metric("Pendiente", clp(tot.sum() - pagado))
        if not pagos.empty and abs(tot.sum() - (r["pagos_trabajo"] + r["reembolsos"])) > 1:
            st.warning("La suma de pagos no coincide con el escenario actual. Usa «Generar / actualizar pagos» o revisa los cambios.")
    with t[1]:
        fondos = D.cargar_proyecto("coop_fondos", pid)
        v = fondos[["ID", "Fecha", "Tipo", "Monto", "Custodia", "Nota"]].copy()
        v["Monto"] = pd.to_numeric(v["Monto"], errors="coerce")
        st.caption("Registra aquí cada movimiento real de dinero del proyecto: cuándo pagó el cliente, ventas cobradas, "
                   "pagos a personas, reembolsos y el aporte entregado a AUCCA. «Custodia» = quién tiene la plata.")
        ed = st.data_editor(v, hide_index=True, use_container_width=True, num_rows="dynamic", key=f"fo_ed_{pid}", column_config={
            "ID": None, "Tipo": st.column_config.SelectboxColumn(options=TIPOS_FONDO_INGRESO + TIPOS_FONDO_EGRESO),
            "Monto": st.column_config.NumberColumn("Monto $"),
            "Custodia": st.column_config.SelectboxColumn("Quién lo tiene", options=_personas_opciones() + ["Cuenta bancaria de AUCCA"])})
        if st.button("💾 Guardar movimientos", type="primary", key=f"fo_save_{pid}"):
            o = ed.copy()
            o["Monto"] = o["Monto"].map(lambda x: "" if pd.isna(x) else str(int(x)))
            D.guardar_proyecto("coop_fondos", pid, o.fillna(""), "fo")
            st.success("Guardado.")
            st.rerun()
        m = pd.to_numeric(ed["Monto"], errors="coerce").fillna(0)
        ingresos = m[ed["Tipo"].isin(TIPOS_FONDO_INGRESO)].sum()
        egresos = m[ed["Tipo"].isin(TIPOS_FONDO_EGRESO)].sum()
        c = st.columns(4)
        c[0].metric("Ingresos esperados (según registro)", clp(r["ingreso_total"]))
        c[1].metric("Ingresos recibidos (movimientos)", clp(ingresos))
        c[2].metric("Egresos registrados", clp(egresos))
        c[3].metric("Saldo en custodia del proyecto", clp(ingresos - egresos))
        if r["ingreso_total"] - ingresos > 0:
            st.caption(f"Faltan por registrar o cobrar {clp(r['ingreso_total'] - ingresos)} de lo esperado.")
        ventas = D.cargar_proyecto("coop_ventas", pid)
        if not ventas.empty:
            items = D.cargar_proyecto("coop_items", pid).set_index("ID")["Precio"].to_dict()
            vv = ventas.copy()
            vv["Total"] = [M.num(a) * (M.num(b) if str(b).strip() else M.num(items.get(i))) for a, b, i in
                           zip(vv["Cantidad"], vv["PrecioUnit"], vv["ItemID"])]
            vv["Medio"] = vv["Medio"].replace("", "Sin medio")
            tabla = vv.pivot_table(index="Vendedor", columns="Medio", values="Total", aggfunc="sum", fill_value=0)
            st.markdown("**Ventas de productos: quién debería tener qué (efectivo/transferencia)**")
            st.dataframe(tabla.map(clp), use_container_width=True)
    with t[2]:
        fondos = D.cargar_proyecto("coop_fondos", pid)
        entregado = pd.to_numeric(fondos[fondos["Tipo"] == "Aporte entregado a AUCCA"]["Monto"], errors="coerce").sum()
        st.metric("Aporte a AUCCA que corresponde", clp(r["aporte_a_aucca"]))
        st.caption(f"Reserva de espacio {clp(r['reserva_espacio'])} + espacio de productos {clp(r['productos_a_espacio'])}.")
        c = st.columns(2)
        c[0].metric("Entregado a AUCCA (registrado en «Caja del proyecto»)", clp(entregado))
        c[1].metric("Falta entregar / ingresar", clp(r["aporte_a_aucca"] - entregado))
        st.info("Cuando entregues el dinero a AUCCA: 1) regístralo en «Caja del proyecto» como «Aporte entregado a AUCCA» y "
                "2) ingrésalo tú en la pestaña **Finanzas** de AUCCA. Esta plataforma no escribe en Finanzas.")


def _sec_personas(pid: str) -> None:
    st.markdown("### Perfiles de las personas")
    st.caption("Cada persona declara qué ofrece y cuánto valora su hora. Esto alimenta el método F y la planificación. "
               "Los valores con «Por confirmar» marcado son estimaciones: cada persona debe confirmar el suyo.")
    df = D.cargar("coop_personas")
    if df.empty:
        df = pd.DataFrame({"Persona": AUCCANES})
        df = D._normalizar("coop_personas", df)
    v = df.copy()
    for c in ("ValorHora", "HorasMes"):
        v[c] = pd.to_numeric(v[c], errors="coerce")
    v["PorConfirmar"] = v["PorConfirmar"].map(_bool)
    ed = st.data_editor(v, hide_index=True, use_container_width=True, num_rows="dynamic", key="per_ed", column_config={
        "Persona": st.column_config.TextColumn("Persona"), "ValorHora": st.column_config.NumberColumn("Valor de mi hora $"),
        "Ofrece": st.column_config.TextColumn("Qué puedo ofrecer (talleres, cocina, difusión, mantención…)"),
        "HorasMes": st.column_config.NumberColumn("Horas al mes disponibles"),
        "Nivel": st.column_config.SelectboxColumn("Nivel habitual", options=["1", "2", "3", "4"]),
        "Notas": st.column_config.TextColumn("Notas"), "PorConfirmar": st.column_config.CheckboxColumn("¿Por confirmar?")})
    if st.button("💾 Guardar perfiles", type="primary", key="per_save"):
        o = ed.copy()
        o["PorConfirmar"] = o["PorConfirmar"].map(lambda x: "TRUE" if x is True else "FALSE")
        for c in ("ValorHora", "HorasMes"):
            o[c] = o[c].map(lambda x: "" if pd.isna(x) else str(int(x)))
        D.guardar_tabla("coop_personas", o.fillna(""))
        st.success("Guardado.")
        st.rerun()
    st.markdown("#### Ficha de una persona")
    nombres = [p for p in ed["Persona"].tolist() if p]
    if nombres:
        quien = st.selectbox("Persona", nombres, key="per_sel")
        reg = D.cargar("coop_registro")
        r = reg[reg["Persona"] == quien].copy()
        r["Horas"] = pd.to_numeric(r["Horas"], errors="coerce").fillna(0)
        proy = D.cargar("coop_proyectos").set_index("ID")["Nombre"].to_dict()
        c = st.columns(3)
        c[0].metric("Horas registradas (todos los proyectos)", f"{r['Horas'].sum():g}")
        c[1].metric("Proyectos en que participó", r["ProyectoID"].nunique())
        c[2].metric("Valor de su hora declarado", clp(M.num(ed[ed["Persona"] == quien]["ValorHora"].iloc[0])))
        if not r.empty:
            r["Proyecto"] = r["ProyectoID"].map(proy)
            st.dataframe(r.groupby(["Proyecto", "Tarea"], as_index=False)["Horas"].sum(), hide_index=True,
                         use_container_width=True)
        res = _calcular(pid, _params_de(_fila_proyecto(pid).get("Escenario", "")))["personas"]
        f = res[res["Persona"] == quien]
        if not f.empty:
            st.markdown(f"**En el proyecto seleccionado:** recibe {clp(f.iloc[0]['Total a recibir'])} "
                        f"(aportó {clp(f.iloc[0]['Aporte total ($)'])} de valor generado).")


def _sec_circulos() -> None:
    st.markdown("### Círculos, acuerdos y tensiones")
    if st.toggle("Cómo usar esta sección", key="gob_tog"):
        st.markdown(
            "- **Círculo**: un área de trabajo con personas responsables (Producción, Educación, Cocina, Espacio, Difusión…). "
            "Cada círculo decide sobre su trabajo dentro de lo acordado por todos.\n"
            "- **Propuesta**: algo que alguien quiere cambiar o iniciar. Se presenta, se aclara, se escuchan reacciones y se "
            "pregunta: *¿hay alguna objeción razonada?* Una objeción es información para mejorar la propuesta, no un veto.\n"
            "- **Tensión**: la distancia entre cómo están las cosas y cómo podrían estar (p. ej. «el trabajo invisible no se "
            "registra»). Visibilizarla es el primer paso; no hace falta tener la solución.\n"
            "- **Acuerdo**: decisión tomada, con responsable y **fecha de revisión**. Todo acuerdo se vuelve a mirar.\n\n"
            "Regla simple: decidimos lo suficientemente bien para avanzar, lo probamos, medimos y lo ajustamos.")
    df = D.cargar("coop_gobernanza")
    f1, f2 = st.columns(2)
    ft = f1.multiselect("Filtrar por tipo", ["Círculo", "Propuesta", "Tensión", "Acuerdo"])
    fe = f2.multiselect("Filtrar por estado", ["Abierta", "En conversación", "Objeción pendiente", "Acordada", "Revisar", "Cerrada"])
    mask = pd.Series(True, index=df.index)
    if ft:
        mask &= df["Tipo"].isin(ft)
    if fe:
        mask &= df["Estado"].isin(fe)
    ed = st.data_editor(df[mask], hide_index=True, use_container_width=True, num_rows="dynamic", key="gob_ed", column_config={
        "ID": None, "Tipo": st.column_config.SelectboxColumn(options=["Círculo", "Propuesta", "Tensión", "Acuerdo"]),
        "Estado": st.column_config.SelectboxColumn(options=["Abierta", "En conversación", "Objeción pendiente", "Acordada", "Revisar", "Cerrada"]),
        "Titulo": "Título", "Circulo": "Círculo / área", "Descripcion": "Descripción", "Responsable": "Responsable(s)",
        "Fecha": "Fecha", "Revision": "Revisar el", "Objeciones": "Objeciones y cómo se resolvieron", "Resultado": "Resultado / aprendizaje"})
    if st.button("💾 Guardar", type="primary", key="gob_save"):
        resto = df[~mask]
        D.guardar_tabla("coop_gobernanza", pd.concat([resto, ed.fillna("")], ignore_index=True), "g")
        st.success("Guardado.")
        st.rerun()
    hoy = dt.date.today().isoformat()
    venc = df[(df["Revision"] != "") & (df["Revision"] <= hoy) & (df["Estado"] != "Cerrada")]
    if not venc.empty:
        st.warning(f"{len(venc)} acuerdo(s) con revisión vencida: " + ", ".join(venc["Titulo"].tolist()))


def _sec_manual() -> None:
    opciones = {"Manual de uso": "manual_cooperativa.md", "Supuestos y fórmulas": "supuestos_y_formulas.md",
                "Reglamento interno (borrador)": "reglamento_interno_borrador.md",
                "Notas legales y tributarias": "notas_legales_tributarias.md"}
    sel = st.radio("Documento", list(opciones), horizontal=True, key="coop_doc")
    f = DOCS / opciones[sel]
    if f.exists():
        st.markdown(f.read_text(encoding="utf-8"))
    else:
        st.info("Documento no disponible.")


# ----------------------------------------------------------------------- main
def render() -> None:
    st.markdown("## Cooperativa de Trabajo")
    st.caption("Proyectos, reparto justo del trabajo y claridad del dinero. Datos en: " + D.modo_datos() + ".")
    if not D.usa_sheets():
        st.info("Modo de prueba: los datos se guardan en un archivo local, no en Google Sheets.")
    if D.instalacion_nueva():
        # primera vez: queda registrado el primer proyecto de la cooperativa (la visita del 13 de noviembre)
        D.sembrar_proyecto_inicial()
        st.rerun()
    D.completar_gobernanza_inicial()
    if D.migrar_talleres_diego_camilu():
        st.rerun()
    if D.migrar_productores_plantas():
        st.rerun()
    if D.migrar_a_datos_reales():
        # instalaciones que ya tenían las estimaciones de la primera carga: pasan a los datos declarados
        st.rerun()
    proy = D.cargar("coop_proyectos")
    secciones = ["Proyectos", "Resumen", "Registro", "Resultados", "Simulador", "Parámetros", "Planificar",
                 "Pagos y fondos", "Personas", "Círculos", "Manual"]
    sec = st.radio("Sección", secciones, horizontal=True, label_visibility="collapsed", key="coop_sec")
    if sec == "Proyectos" or proy.empty:
        st.markdown("---")
        _sec_proyectos()
        return
    ids = proy["ID"].tolist()
    nombres = {r["ID"]: f"{r['Nombre']} · {r['Fecha']} · {r['Estado']}" for _, r in proy.iterrows()}
    actual = st.session_state.get("coop_pid", ids[0])
    if actual not in ids:
        actual = ids[0]
    if sec in ("Círculos", "Manual"):
        pid = actual
    else:
        pid = st.selectbox("Proyecto", ids, index=ids.index(actual), format_func=lambda i: nombres[i])
        st.session_state["coop_pid"] = pid
    st.markdown("---")
    if sec == "Resumen":
        _sec_resumen(pid)
    elif sec == "Registro":
        _sec_registro(pid)
    elif sec == "Resultados":
        _sec_resultados(pid)
    elif sec == "Simulador":
        _sec_simulador(pid)
    elif sec == "Parámetros":
        _sec_parametros(pid)
    elif sec == "Planificar":
        _sec_planificar(pid)
    elif sec == "Pagos y fondos":
        _sec_pagos(pid)
    elif sec == "Personas":
        _sec_personas(pid)
    elif sec == "Círculos":
        _sec_circulos()
    else:
        _sec_manual()
