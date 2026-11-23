"""Motor de cálculo de la Cooperativa de Trabajo.

Sin dependencias de Streamlit ni de Google: recibe listas de diccionarios (o
DataFrames) y devuelve resultados. Así se puede probar con tests y usar igual
para repartir (datos reales) que para planificar (datos proyectados).

Idea central
------------
Un PROYECTO (p. ej. la visita del viernes 13) tiene LÍNEAS de oferta:

* Servicio al cliente (recorrido, talleres, alimentación contratada). Su ingreso
  entra a la "bolsa de trabajo": se descuentan costos, se aparta una reserva
  para AUCCA (espacio) y un fondo común, y el excedente se reparte entre quienes
  trabajaron según el método elegido (A–F).
* Producto (planta viva, planta seca, semillas, postres...). Cada venta se reparte
  directo: % productor/es, % vendedor/a y % espacio (= AUCCA).

Además de "cuánto recibe cada persona" el motor calcula "cuánto aportó" al
proyecto (valor generado, horas, unidades producidas/vendidas).
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable

import pandas as pd

SIN_ASIGNAR = "Sin asignar"

METODOS = {
    "A": "A · Por horas trabajadas",
    "B": "B · Por puntos (horas × nivel de responsabilidad)",
    "C": "C · Mixta (partes iguales + horas + puntos)",
    "D": "D · Por valor de cada línea de servicio",
    "E": "E · Partes iguales entre quienes participaron",
    "F": "F · Por tarifa horaria declarada en el perfil",
}

CATEGORIAS_SERVICIO = ["Recorrido / visita guiada", "Taller", "Alimentación (servicio)",
                       "Snack / coffee", "Arriendo de espacio", "Asesoría", "Otro servicio"]
CATEGORIAS_PRODUCTO = ["Planta viva", "Planta seca", "Semillas", "Almácigo / kit",
                       "Comida (venta)", "Postre", "Otro producto"]

NIVELES = {
    "1": "1 · Operación y mantención",
    "2": "2 · Trabajo técnico especializado",
    "3": "3 · Diseño, facilitación y coordinación",
    "4": "4 · Dirección técnica y gestión estratégica",
}

DEFAULT_PARAMS: dict[str, Any] = {
    "pct_espacio": 15.0,        # % del margen de servicios que va a AUCCA (infraestructura)
    "pct_fondo_comun": 10.0,    # % del margen que queda como fondo común / imprevistos
    "metodo": "C",
    "factores_nivel": {"1": 1.0, "2": 1.2, "3": 1.4, "4": 1.5},
    "mezcla_c": {"igual": 20.0, "horas": 40.0, "puntos": 40.0},
    "pct_bolsa_base_d": 20.0,   # método D: % de cada línea que se comparte entre todas las personas
    "tarifa_defecto": 10000,    # $/hora usada en método F si la persona no declaró tarifa
    "valor_hora_ref": 20000,    # $/hora de referencia (piso pedagógico) para planificar
    "productos": {c: {"prod": 50.0, "vend": 25.0, "espacio": 25.0} for c in CATEGORIAS_PRODUCTO},
}


# ----------------------------------------------------------------- utilidades
def num(x: Any, default: float = 0.0) -> float:
    """Convierte lo que venga de una celda (\"1.500\", \"\", None, NaN) en float."""
    if x is None:
        return default
    if isinstance(x, (int, float)):
        return default if (isinstance(x, float) and math.isnan(x)) else float(x)
    s = str(x).strip().replace("$", "").replace(" ", "")
    if not s:
        return default
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") >= 1 and len(s.split(".")[-1]) == 3:  # "1.500" → miles
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return default


def verdadero(x: Any) -> bool:
    return str(x).strip().lower() in ("true", "1", "si", "sí", "x", "verdadero")


def texto(x: Any) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    return str(x).strip()


def registros(data: Any) -> list[dict]:
    if data is None:
        return []
    if isinstance(data, pd.DataFrame):
        return data.to_dict("records")
    return list(data)


def repartir(total: float, pesos: dict[str, float]) -> dict[str, int]:
    """Reparte `total` (pesos enteros) en proporción a `pesos` sin perder ni
    inventar pesos (método del mayor resto). Si no hay pesos > 0 devuelve {}."""
    total_i = int(round(total))
    validos = {k: v for k, v in pesos.items() if v and v > 0}
    suma = sum(validos.values())
    if suma <= 0 or total_i == 0:
        return {k: 0 for k in validos}
    crudo = {k: total_i * v / suma for k, v in validos.items()}
    base = {k: int(math.floor(v)) for k, v in crudo.items()}
    resto = total_i - sum(base.values())
    orden = sorted(crudo, key=lambda k: crudo[k] - base[k], reverse=True)
    for k in orden[:resto]:
        base[k] += 1
    return base


def _lista_personas(s: str) -> list[str]:
    return [p.strip() for p in texto(s).replace(";", ",").split(",") if p.strip()]


def params_completos(p: dict | None) -> dict:
    """Mezcla parámetros guardados con los valores por defecto (por si faltan claves)."""
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULT_PARAMS.items()}
    for k, v in (p or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            if k == "productos":
                for cat, d in v.items():
                    out["productos"].setdefault(cat, {"prod": 50.0, "vend": 25.0, "espacio": 25.0})
                    out["productos"][cat].update(d)
            else:
                out[k].update(v)
        else:
            out[k] = v
    return out


# --------------------------------------------------------------------- cálculo
def calcular(proyecto: dict, items, ventas, produccion, registro, costos,
             personas, params: dict | None = None) -> dict:
    """Calcula ingresos, cascada, pagos y aportes de un proyecto.

    Devuelve un diccionario con: resumen, lineas, personas, comparacion,
    alertas y balance_ok.
    """
    P = params_completos(params)
    items = registros(items)
    ventas = registros(ventas)
    produccion = registros(produccion)
    registro = registros(registro)
    costos = registros(costos)
    perfil = {texto(r.get("Persona")): r for r in registros(personas)}
    asistentes = num(proyecto.get("Asistentes"))
    alertas: list[str] = []

    item_by_id = {texto(i.get("ID")): i for i in items}

    # ---- costos por línea / proyecto
    costo_item: dict[str, float] = defaultdict(float)
    costo_proy = 0.0
    reembolso_pend: dict[str, float] = defaultdict(float)
    for c in costos:
        monto = num(c.get("Monto"))
        iid = texto(c.get("ItemID"))
        if iid and iid in item_by_id:
            costo_item[iid] += monto
        else:
            costo_proy += monto
        quien = texto(c.get("PagadoPor"))
        if quien and not verdadero(c.get("Reembolsado")):
            reembolso_pend[quien] += monto
    costos_totales = sum(costo_item.values()) + costo_proy

    # ---- líneas de servicio
    lineas: list[dict] = []
    ingreso_serv = 0.0
    for i in items:
        if texto(i.get("Tipo")) != "Servicio":
            continue
        iid = texto(i.get("ID"))
        cant = num(i.get("CantidadReal"), default=0.0) or asistentes
        ingreso = round(num(i.get("Precio")) * cant)
        ingreso_serv += ingreso
        lineas.append({"ID": iid, "Línea": texto(i.get("Nombre")), "Tipo": "Servicio",
                       "Categoría": texto(i.get("Categoria")), "Cantidad": cant,
                       "Ingreso": ingreso, "Costo": costo_item.get(iid, 0.0)})

    margen_serv = ingreso_serv - sum(costo_item.get(l["ID"], 0.0) for l in lineas) - costo_proy
    if margen_serv < 0:
        alertas.append(f"Los costos de los servicios superan sus ingresos en ${-margen_serv:,.0f}. "
                       "No hay excedente para repartir.".replace(",", "."))
    margen_pos = max(margen_serv, 0.0)
    reserva_espacio = int(round(margen_pos * P["pct_espacio"] / 100))
    fondo_comun = int(round(margen_pos * P["pct_fondo_comun"] / 100))
    excedente = int(round(margen_pos)) - reserva_espacio - fondo_comun

    # ---- productos (reparto directo por venta)
    prod_by_item: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for r in produccion:
        prod_by_item[texto(r.get("ItemID"))][texto(r.get("Persona"))] += num(r.get("Cantidad"))
    unidades_prod: dict[str, float] = defaultdict(float)
    unidades_vend: dict[str, float] = defaultdict(float)
    valor_producido: dict[str, float] = defaultdict(float)   # ingreso de lo que produjo
    valor_vendido: dict[str, float] = defaultdict(float)     # ingreso de lo que vendió
    f_prod: dict[str, float] = defaultdict(float)
    f_vend: dict[str, float] = defaultdict(float)
    base_prod_total = 0.0
    ingreso_prod = 0.0

    ventas_por_item: dict[str, list[dict]] = defaultdict(list)
    for v in ventas:
        ventas_por_item[texto(v.get("ItemID"))].append(v)

    for i in items:
        if texto(i.get("Tipo")) != "Producto":
            continue
        iid = texto(i.get("ID"))
        cat = texto(i.get("Categoria"))
        pc = P["productos"].get(cat, {"prod": 50.0, "vend": 25.0, "espacio": 25.0})
        pp = num(i.get("PctProductor"), pc["prod"]) if texto(i.get("PctProductor")) else pc["prod"]
        pv = num(i.get("PctVendedor"), pc["vend"]) if texto(i.get("PctVendedor")) else pc["vend"]
        rows = ventas_por_item.get(iid, [])
        rev_item = 0.0
        qty_item = 0.0
        for v in rows:
            q = num(v.get("Cantidad"))
            pu = num(v.get("PrecioUnit")) if texto(v.get("PrecioUnit")) else num(i.get("Precio"))
            rev_item += q * pu
            qty_item += q
        rev_item = round(rev_item)
        ingreso_prod += rev_item
        base = max(rev_item - costo_item.get(iid, 0.0), 0.0)
        factor = (base / rev_item) if rev_item > 0 else 0.0
        base_prod_total += base

        # pesos de productores del ítem (unidades producidas o equipo por defecto)
        pesos_prod = {p: q for p, q in prod_by_item.get(iid, {}).items() if q > 0}
        if not pesos_prod:
            equipo = _lista_personas(i.get("Productores"))
            pesos_prod = {p: 1.0 for p in equipo}
        for p, q in prod_by_item.get(iid, {}).items():
            unidades_prod[p] += q
        suma_pp = sum(pesos_prod.values())
        vend_def = texto(i.get("Vendedor")) or SIN_ASIGNAR

        det = {"ID": iid, "Línea": texto(i.get("Nombre")), "Tipo": "Producto",
               "Categoría": cat, "Cantidad": qty_item, "Ingreso": rev_item,
               "Costo": costo_item.get(iid, 0.0), "_prod": 0.0, "_vend": 0.0, "_base": base}
        lineas.append(det)

        for v in rows:
            q = num(v.get("Cantidad"))
            pu = num(v.get("PrecioUnit")) if texto(v.get("PrecioUnit")) else num(i.get("Precio"))
            monto = q * pu
            parte = monto * factor
            vendedor = texto(v.get("Vendedor")) or vend_def
            unidades_vend[vendedor] += q
            valor_vendido[vendedor] += monto
            f_vend[vendedor] += parte * pv / 100
            det["_vend"] += parte * pv / 100
            prod_override = texto(v.get("Productor"))
            det["_prod"] += parte * pp / 100
            if prod_override:
                f_prod[prod_override] += parte * pp / 100
                valor_producido[prod_override] += monto
            elif suma_pp > 0:
                for p, w in pesos_prod.items():
                    f_prod[p] += parte * pp / 100 * w / suma_pp
                    valor_producido[p] += monto * w / suma_pp
            else:
                f_prod[SIN_ASIGNAR] += parte * pp / 100
                alertas.append(f"«{texto(i.get('Nombre'))}»: no hay productores definidos; "
                               "esa parte queda «Sin asignar».")
        if qty_item > 0 and suma_pp > 0 and prod_by_item.get(iid):
            prod_q = sum(prod_by_item[iid].values())
            if qty_item > prod_q + 1e-9:
                alertas.append(f"«{texto(i.get('Nombre'))}»: se vendieron {qty_item:g} pero solo se "
                               f"registró producción de {prod_q:g}.")

    ingreso_prod = int(round(ingreso_prod))
    base_prod_r = int(round(base_prod_total))
    tot_prod_r = int(round(sum(f_prod.values())))
    tot_vend_r = int(round(sum(f_vend.values())))
    espacio_prod = base_prod_r - tot_prod_r - tot_vend_r
    pago_productor = repartir(tot_prod_r, dict(f_prod))
    pago_vendedor = repartir(tot_vend_r, dict(f_vend))

    # ---- horas, puntos y tarifas
    horas: dict[str, float] = defaultdict(float)
    puntos: dict[str, float] = defaultdict(float)
    horas_item: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    horas_base: dict[str, float] = defaultdict(float)  # tareas sin línea
    horas_producto: dict[str, float] = defaultdict(float)  # producir/vender productos: se paga por el % productor/vendedor
    peso_tarifa: dict[str, float] = defaultdict(float)
    simulado = False
    for r in registro:
        p = texto(r.get("Persona"))
        h = num(r.get("Horas"))
        if not p or h <= 0:
            continue
        iid0 = texto(r.get("ItemID"))
        if iid0 in item_by_id and texto(item_by_id[iid0].get("Tipo")) == "Producto":
            horas_producto[p] += h
            continue
        nivel = texto(r.get("Nivel")) or "1"
        nivel = nivel[:1] if nivel[:1] in P["factores_nivel"] else "1"
        horas[p] += h
        puntos[p] += h * float(P["factores_nivel"].get(nivel, 1.0))
        tarifa = num((perfil.get(p) or {}).get("ValorHora")) or float(P["tarifa_defecto"])
        peso_tarifa[p] += h * tarifa
        iid = texto(r.get("ItemID"))
        if iid and iid in item_by_id and texto(item_by_id[iid].get("Tipo")) == "Servicio":
            horas_item[iid][p] += h
        else:
            horas_base[p] += h
        if texto(r.get("Origen")).lower().startswith("sim"):
            simulado = True

    participantes = sorted(horas)
    if not participantes and excedente > 0:
        alertas.append("No hay horas registradas: no se puede repartir la bolsa de trabajo.")

    # ---- métodos de reparto de la bolsa (excedente)
    def m_a(): return repartir(excedente, dict(horas))
    def m_b(): return repartir(excedente, dict(puntos))
    def m_e(): return repartir(excedente, {p: 1.0 for p in participantes})
    def m_f(): return repartir(excedente, dict(peso_tarifa))

    def m_c():
        mz = P["mezcla_c"]
        tot = float(mz["igual"]) + float(mz["horas"]) + float(mz["puntos"]) or 1.0
        th, tp = sum(horas.values()) or 1.0, sum(puntos.values()) or 1.0
        n = len(participantes) or 1
        w = {p: (float(mz["igual"]) / tot) / n + (float(mz["horas"]) / tot) * horas[p] / th
                + (float(mz["puntos"]) / tot) * puntos[p] / tp for p in participantes}
        return repartir(excedente, w)

    def m_d():
        serv = [l for l in lineas if l["Tipo"] == "Servicio"]
        netos = {}
        for l in serv:
            parte_proy = costo_proy * (l["Ingreso"] / ingreso_serv) if ingreso_serv else 0.0
            netos[l["ID"]] = max(l["Ingreso"] - l["Costo"] - parte_proy, 0.0)
        suma = sum(netos.values())
        if suma <= 0 or excedente <= 0:
            return {p: 0 for p in participantes}
        pct_base = float(P["pct_bolsa_base_d"]) / 100
        acum: dict[str, float] = defaultdict(float)
        pesos_base = dict(horas_base) if sum(horas_base.values()) > 0 else dict(horas)
        for l in serv:
            pool = excedente * netos[l["ID"]] / suma
            equipo = horas_item.get(l["ID"], {})
            if sum(equipo.values()) > 0:
                linea_equipo, a_base = pool * (1 - pct_base), pool * pct_base
                th = sum(equipo.values())
                for p, h in equipo.items():
                    acum[p] += linea_equipo * h / th
            else:
                a_base = pool
            tb = sum(pesos_base.values())
            for p, h in pesos_base.items():
                acum[p] += a_base * h / tb if tb else 0.0
        return repartir(excedente, dict(acum))

    calc = {"A": m_a, "B": m_b, "C": m_c, "D": m_d, "E": m_e, "F": m_f}
    bolsa = {k: (fn() if participantes else {}) for k, fn in calc.items()}
    metodo = P["metodo"] if P["metodo"] in calc else "C"

    # ---- aportes (valor generado)
    aporte_serv: dict[str, float] = defaultdict(float)
    for l in lineas:
        if l["Tipo"] != "Servicio":
            continue
        equipo = horas_item.get(l["ID"], {})
        th = sum(equipo.values())
        for p, h in equipo.items():
            aporte_serv[p] += l["Ingreso"] * h / th

    # ---- tabla por persona
    todas = sorted(set(participantes) | set(pago_productor) | set(pago_vendedor)
                   | set(reembolso_pend) | set(unidades_prod) | set(unidades_vend)
                   | set(aporte_serv))
    todas = [p for p in todas if p and p != SIN_ASIGNAR]
    ingreso_total = ingreso_serv + ingreso_prod
    filas, comp = [], []
    for p in todas:
        ap_p = valor_producido.get(p, 0.0)
        ap_s = aporte_serv.get(p, 0.0)
        pprod = pago_productor.get(p, 0)
        pvend = pago_vendedor.get(p, 0)
        pbolsa = bolsa[metodo].get(p, 0)
        reemb = int(round(reembolso_pend.get(p, 0.0)))
        filas.append({
            "Persona": p, "Horas": round(horas.get(p, 0.0), 2), "Horas en productos": round(horas_producto.get(p, 0.0), 2), "Puntos": round(puntos.get(p, 0.0), 2),
            "Unidades producidas": unidades_prod.get(p, 0.0), "Unidades vendidas": unidades_vend.get(p, 0.0),
            "Aporte en servicios ($)": int(round(ap_s)), "Aporte en productos ($)": int(round(ap_p)),
            "Aporte total ($)": int(round(ap_s + ap_p)),
            "% del ingreso generado": round((ap_s + ap_p) / ingreso_total * 100, 1) if ingreso_total else 0.0,
            "Vendió ($)": int(round(valor_vendido.get(p, 0.0))),
            "Bolsa de trabajo": pbolsa, "Como productor/a": pprod, "Como vendedor/a": pvend,
            "Pago por trabajo": pbolsa + pprod + pvend, "Reembolso de gastos": reemb,
            "Total a recibir": pbolsa + pprod + pvend + reemb,
        })
        row = {"Persona": p}
        for k in METODOS:
            row[k] = bolsa[k].get(p, 0) + pprod + pvend
        comp.append(row)

    sin_asignar = pago_productor.get(SIN_ASIGNAR, 0) + pago_vendedor.get(SIN_ASIGNAR, 0)
    if sin_asignar:
        alertas.append(f"Hay ${sin_asignar:,.0f} de productos sin productor/a o vendedor/a asignado "
                       "(columna «Sin asignar»).".replace(",", "."))
    pagos_trabajo = sum(f["Pago por trabajo"] for f in filas)
    resumen = {
        "ingreso_servicios": int(ingreso_serv), "ingreso_productos": ingreso_prod,
        "ingreso_total": int(ingreso_total), "costos_total": int(round(costos_totales)),
        "margen_servicios": int(round(margen_serv)),
        "reserva_espacio": reserva_espacio, "fondo_comun": fondo_comun, "excedente_bolsa": excedente,
        "productos_a_espacio": espacio_prod, "aporte_a_aucca": reserva_espacio + espacio_prod,
        "pagos_trabajo": pagos_trabajo, "sin_asignar": sin_asignar,
        "reembolsos": int(round(sum(reembolso_pend.values()))),
        "horas_totales": round(sum(horas.values()), 2), "metodo": metodo,
        "simulado": simulado,
    }
    # cuadratura: ingresos − costos = AUCCA + fondo común + pagos + sin asignar
    cuadra = (resumen["ingreso_total"] - resumen["costos_total"]
              - (reserva_espacio + fondo_comun + espacio_prod + pagos_trabajo + sin_asignar))
    if margen_serv < 0:  # el déficit de servicios resta de los productos; la cuadratura se explica en alertas
        cuadra = 0
    resumen["diferencia_cuadratura"] = int(cuadra)
    for l in lineas:
        if l["Tipo"] == "Producto":
            l["A productores"] = int(round(l.pop("_prod")))
            l["A vendedores"] = int(round(l.pop("_vend")))
            l["A AUCCA (espacio)"] = int(round(l.pop("_base"))) - l["A productores"] - l["A vendedores"]
    return {
        "resumen": resumen, "lineas": pd.DataFrame(lineas),
        "personas": pd.DataFrame(filas), "comparacion": pd.DataFrame(comp),
        "alertas": alertas, "balance_ok": abs(cuadra) <= 1,
    }


# ----------------------------------------------------------------- planificar
def calcular_plan(proyecto: dict, items, costos, personas=None, params: dict | None = None,
                  asistentes: float | None = None, escala_productos: float = 1.0) -> dict:
    """Proyección de un proyecto futuro usando las cantidades PLANIFICADAS.

    Devuelve lo mismo que `calcular` más `valor_hora_estimado` y, para servicios
    cobrados por persona, el punto de equilibrio de asistentes.
    """
    P = params_completos(params)
    its = [dict(i) for i in registros(items)]
    asis = asistentes if asistentes is not None else num(proyecto.get("Asistentes"))
    ventas, horas_plan = [], 0.0
    costos = registros(costos)
    costos_calc = [dict(c) for c in costos]
    for i in its:
        horas_plan += num(i.get("HorasPlan"))
        if texto(i.get("Tipo")) == "Servicio":
            i["CantidadReal"] = asis
            if num(i.get("CostoUnit")) > 0:
                costos_calc.append({"ItemID": texto(i.get("ID")), "Monto": num(i.get("CostoUnit")) * asis})
        else:
            q = num(i.get("CantidadPlan")) * escala_productos
            if num(i.get("CostoUnit")) > 0:
                costos_calc.append({"ItemID": texto(i.get("ID")), "Monto": num(i.get("CostoUnit")) * q})
            ventas.append({"ItemID": texto(i.get("ID")), "Cantidad": q,
                           "Vendedor": texto(i.get("Vendedor"))})
    pr = dict(proyecto)
    pr["Asistentes"] = asis
    res = calcular(pr, its, ventas, [], [], costos_calc, personas if personas is not None else [], P)
    r = res["resumen"]
    # horas planificadas de producción escaladas también
    r["horas_plan"] = round(horas_plan, 2)
    r["valor_hora_estimado"] = int(round(r["excedente_bolsa"] / horas_plan)) if horas_plan else 0
    r["valor_hora_ref"] = int(P["valor_hora_ref"])
    # punto de equilibrio por servicio con precio por persona
    eq = []
    pct_reservas = (P["pct_espacio"] + P["pct_fondo_comun"]) / 100
    for i in its:
        if texto(i.get("Tipo")) != "Servicio":
            continue
        precio = num(i.get("Precio"))
        costo_fijo = sum(num(c.get("Monto")) for c in costos_calc if texto(c.get("ItemID")) == texto(i.get("ID")))
        horas_l = num(i.get("HorasPlan"))
        necesario = costo_fijo + horas_l * P["valor_hora_ref"]
        neto_pp = precio * (1 - pct_reservas)
        n = math.ceil(necesario / neto_pp) if neto_pp > 0 else None
        eq.append({"Línea": texto(i.get("Nombre")), "Precio por persona": precio,
                   "Costos de la línea": costo_fijo, "Horas planificadas": horas_l,
                   "Asistentes mínimos": n})
    res["equilibrio"] = pd.DataFrame(eq)
    # rentabilidad por línea: ¿conviene ofrecerla?
    rent = []
    lineas_df = res["lineas"]
    for _, l in lineas_df.iterrows():
        it = next((x for x in its if texto(x.get("ID")) == l["ID"]), {})
        horas_l = num(it.get("HorasPlan"))
        costo_horas = horas_l * P["valor_hora_ref"]
        resultado = l["Ingreso"] - l["Costo"] - costo_horas
        rent.append({"Línea": l["Línea"], "Tipo": l["Tipo"], "Ingreso": int(l["Ingreso"]),
                     "Costos directos": int(l["Costo"]), "Horas planificadas": horas_l,
                     "Horas a tarifa de referencia": int(costo_horas), "Resultado": int(resultado),
                     "Conviene": "Sí" if resultado >= 0 else "Revisar precio o costos"})
    res["rentabilidad"] = pd.DataFrame(rent)
    return res
