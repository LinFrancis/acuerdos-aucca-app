"""Observaciones en lenguaje simple para entender las tablas de Resultados.

Todo se calcula a partir de los datos del proyecto (nada está escrito a mano), así que cambia solo
cuando cambian las horas, ventas, gastos o parámetros. Sin dependencias de Streamlit.
"""
from __future__ import annotations

import pandas as pd

from secciones import coop_motor as M


def clp(x) -> str:
    try:
        v = int(round(float(x)))
        return ("-" if v < 0 else "") + "$" + f"{abs(v):,}".replace(",", ".")
    except Exception:
        return "$0"


def _lista(nombres: list[str]) -> str:
    nombres = [str(n) for n in nombres]
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


def _h(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def obs_contexto(personas: pd.DataFrame, r: dict, registro: pd.DataFrame, costos: pd.DataFrame) -> list[str]:
    obs: list[str] = []
    con_horas = personas[personas["Horas"] > 0]
    if not con_horas.empty:
        mx = con_horas.loc[con_horas["Horas"].idxmax()]
        mn = con_horas.loc[con_horas["Horas"].idxmin()]
        obs.append(f"Se declararon **{_h(con_horas['Horas'].sum())} h** en total. Declaró más horas {mx['Persona']} "
                   f"({_h(mx['Horas'])} h) y menos {mn['Persona']} ({_h(mn['Horas'])} h). Las horas son tiempo declarado; "
                   "no miden por sí solas cuánto aportó cada persona.")
    sin_aporte = con_horas[con_horas["Aporte total ($)"] == 0]["Persona"].tolist()
    if sin_aporte:
        obs.append(f"{_lista(sin_aporte)} tiene{'n' if len(sin_aporte) > 1 else ''} horas, pero ninguna asignada a una línea "
                   "de servicio ni producción registrada, por eso su «Aportó» aparece en $0. No significa que no haya "
                   "aportado: falta desglosar esas horas por tarea en «Registro».")
    if not registro.empty:
        est = registro[registro["Origen"].astype(str).str.lower().str.startswith(("sim", "estim"))]
        if not est.empty:
            por = est.groupby("Persona")["Horas"].apply(lambda s: sum(M.num(x) for x in s))
            det = ", ".join(f"{k} ({_h(v)} h)" for k, v in por.items())
            obs.append(f"Hay horas marcadas como estimadas o sin desglosar: {det}. Los resultados cambiarán cuando se confirmen.")
    vend = personas[personas["Vendió ($)"] > 0]["Persona"].tolist()
    if r["ingreso_productos"] > 0:
        obs.append(f"Las ventas de plantas registradas ({clp(r['ingreso_productos'])}) están a nombre de {_lista(vend) or 'nadie'}. "
                   "Si otra persona también vendió, esas ventas todavía no están cargadas.")
    if r["ingreso_productos"] > 0:
        prod = personas[personas["Como productor/a"] > 0]
        vend_ = personas[personas["Como vendedor/a"] > 0]
        if not prod.empty or not vend_.empty:
            obs.append("Reparto de las plantas vendidas (se calcula aparte de los servicios): como productor/a "
                       + (", ".join(f"{f['Persona']} {clp(f['Como productor/a'])}" for _, f in prod.iterrows()) or "nadie")
                       + "; como vendedor/a "
                       + (", ".join(f"{f['Persona']} {clp(f['Como vendedor/a'])}" for _, f in vend_.iterrows()) or "nadie")
                       + f"; para el espacio (AUCCA) {clp(r['productos_a_espacio'])}.")
    if not costos.empty:
        propios = costos[costos["PagadoPor"].astype(str).str.strip() != ""]
        total = sum(M.num(x) for x in propios["Monto"])
        sin_boleta = sum(1 for x in propios["ConBoleta"] if not M.verdadero(x))
        pend = r["reembolsos"]
        txt = f"Los gastos pagados de su bolsillo suman **{clp(total)}**. "
        txt += "Todos ya fueron devueltos." if pend == 0 else f"Faltan por devolver {clp(pend)}."
        if sin_boleta and sin_boleta == len(propios):
            txt += " Ninguno tiene boleta o factura."
        elif sin_boleta:
            txt += f" {sin_boleta} de {len(propios)} no tienen boleta o factura."
        obs.append(txt)
    aportes = personas["Aporte total ($)"].sum()
    if r["ingreso_total"] and r["ingreso_total"] - aportes > 1:
        obs.append(f"Los aportes suman {clp(aportes)} de {clp(r['ingreso_total'])} de ingresos. Los {clp(r['ingreso_total'] - aportes)} "
                   "restantes no se atribuyen a nadie todavía (por ejemplo, plantas sin productor/a registrado o líneas sin horas).")
    return obs


def obs_comparativo(tabla: pd.DataFrame, pagos: list[float]) -> list[str]:
    """`tabla`: personas en filas, escenarios en columnas, con el total a recibir (números)."""
    obs: list[str] = []
    if tabla.empty or tabla.shape[1] < 2:
        return obs
    if max(pagos) - min(pagos) <= 1:
        obs.append(f"Todos los escenarios reparten la misma plata por trabajo ({clp(pagos[0])}); solo cambia cómo se distribuye "
                   "entre las personas.")
    else:
        obs.append("Los escenarios no reparten el mismo total porque cambian los porcentajes de reserva para AUCCA o fondo común.")
    rango = tabla.max(axis=1) - tabla.min(axis=1)
    if rango.max() > 0:
        quien = rango.idxmax()
        obs.append(f"Quien más cambia según el escenario es {quien}: recibe entre {clp(tabla.loc[quien].min())} "
                   f"({tabla.loc[quien].idxmin()}) y {clp(tabla.loc[quien].max())} ({tabla.loc[quien].idxmax()}).")
        estable = rango.idxmin()
        if estable != quien:
            obs.append(f"Quien menos cambia es {estable}: entre {clp(tabla.loc[estable].min())} y {clp(tabla.loc[estable].max())}.")
    lideres = tabla.idxmax(axis=0).value_counts()
    obs.append("Quien recibe más en cada escenario: " + ", ".join(f"{k} en {v} de {tabla.shape[1]}" for k, v in lideres.items()) + ".")
    obs.append("Lo que se ve acá es el total a recibir (trabajo más reembolsos). Para decidir, conviene mirar también "
               "cuánto aportó cada persona y cuántas horas declaró.")
    return obs


def obs_escenario(prm: dict, res: dict, tarifas_estimadas: list[str] | None = None) -> list[str]:
    obs: list[str] = []
    pers = res["personas"]
    r = res["resumen"]
    pagan = pers[pers["Pago por trabajo"] > 0]
    if not pagan.empty and pagan["Pago por trabajo"].sum() > 0:
        mx = pagan.loc[pagan["Pago por trabajo"].idxmax()]
        mn = pagan.loc[pagan["Pago por trabajo"].idxmin()]
        share = mx["Pago por trabajo"] / pagan["Pago por trabajo"].sum() * 100
        obs.append(f"Recibe más por su trabajo {mx['Persona']} ({clp(mx['Pago por trabajo'])}, {share:.0f}% de lo repartido) y menos "
                   f"{mn['Persona']} ({clp(mn['Pago por trabajo'])}).")
    hh = pers[(pers["Horas"] > 0) & (pers["Bolsa de trabajo"] > 0)].copy()
    if len(hh) >= 2:
        hh["x_hora"] = hh["Bolsa de trabajo"] / hh["Horas"]
        a, b = hh.loc[hh["x_hora"].idxmin()], hh.loc[hh["x_hora"].idxmax()]
        if b["x_hora"] - a["x_hora"] < 1:
            obs.append(f"Todas las personas reciben lo mismo por cada hora declarada ({clp(a['x_hora'])}) de la bolsa de trabajo.")
        else:
            obs.append(f"Por cada hora declarada, la bolsa de trabajo paga entre {clp(a['x_hora'])} ({a['Persona']}) y "
                       f"{clp(b['x_hora'])} ({b['Persona']}).")
    m = prm["metodo"]
    if m == "A":
        obs.append("Como solo mira horas, quien declaró más horas recibe más, sin importar el tipo de tarea.")
    elif m == "B":
        obs.append("Los niveles de responsabilidad de cada tarea los puso quien cargó los datos; conviene que el grupo los "
                   "revise en «Registro».")
    elif m == "C":
        obs.append("Combina igualdad, horas y responsabilidad en las proporciones indicadas arriba.")
    elif m == "D":
        sin_linea = pers[(pers["Horas"] > 0) & (pers["Aporte en servicios ($)"] == 0)]["Persona"].tolist()
        txt = ("Depende de a qué línea de servicio se asignó cada hora: quien trabajó en líneas de mayor ingreso recibe más.")
        if sin_linea:
            txt += (f" {_lista(sin_linea)} no tiene{'n' if len(sin_linea) > 1 else ''} horas asignadas a una línea, así que solo "
                    f"participa{'n' if len(sin_linea) > 1 else ''} de la parte compartida ({prm['pct_bolsa_base_d']:g}%). "
                    "Si desglosan sus horas por línea, este escenario cambia bastante.")
        obs.append(txt)
    elif m == "E":
        obs.append("Ignora las horas: todas las personas con horas registradas reciben lo mismo.")
    else:
        txt = "Depende de los valores de hora de cada perfil: quien declara una tarifa más alta recibe más por la misma hora."
        if tarifas_estimadas:
            txt += f" Las tarifas de {_lista(tarifas_estimadas)} son estimaciones, no declaradas."
        obs.append(txt)
    if r["reembolsos"] > 0:
        obs.append(f"Incluye {clp(r['reembolsos'])} de reembolsos pendientes, que se devuelven enteros.")
    if r["sin_asignar"] > 0:
        obs.append(f"{clp(r['sin_asignar'])} de plantas quedan sin asignar porque falta registrar quién las produjo; "
                   "no se reparten hasta completar ese dato.")
    if not res["balance_ok"]:
        obs.append("⚠️ La cuadratura no cierra: hay que revisar los datos.")
    return obs
