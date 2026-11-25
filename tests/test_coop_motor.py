import copy
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pandas as pd
import pytest
from secciones import coop_motor as M
from secciones.coop_inicial import datos_proyecto_inicial, DIEGO, CALA, TAIS, CAMILU, NIKO, CHALO, PID

D = datos_proyecto_inicial()


def correr(registro=None, produccion=None, costos=None, **p):
    params = M.params_completos({})
    params.update(p)
    return M.calcular(D["coop_proyectos"][0], D["coop_items"], D["coop_ventas"],
                      D["coop_produccion"] if produccion is None else produccion,
                      D["coop_registro"] if registro is None else registro,
                      D["coop_costos"] if costos is None else costos, D["coop_personas"], params)


def test_repartir_conserva_el_total():
    r = M.repartir(1000, {"a": 1, "b": 1, "c": 1})
    assert sum(r.values()) == 1000 and sorted(r.values()) == [333, 333, 334]
    assert M.repartir(100, {}) == {}


def test_ingresos_y_gastos_declarados():
    r = correr()["resumen"]
    assert r["ingreso_servicios"] == 512000            # $16.000 × 32 (acta 8 nov), líquido en cuenta AUCCA
    assert r["ingreso_productos"] == 12500 + 16000     # ventas declaradas por Diego
    assert r["costos_total"] == 57278 + 2400           # compras de Cala + masas de Nico (incluidas) + traslado de Tais


def test_compras_de_cala_y_nico_suman_57278():
    c = pd.DataFrame(D["coop_costos"])
    compras = c[c["PagadoPor"].isin([CALA, NIKO])]["Monto"].sum()
    assert compras == 57278
    assert c[c["ItemID"] == "s-snack"]["Monto"].sum() == 28753
    assert c[c["ItemID"] == "s-almuerzo"]["Monto"].sum() == 28525


def test_horas_declaradas_por_persona():
    p = correr()["personas"].set_index("Persona")["Horas"]
    assert p[NIKO] == pytest.approx(10.33)
    assert p[CALA] == pytest.approx(6.75)
    assert p[DIEGO] == 13
    assert p[TAIS] == pytest.approx(8.4)
    assert p[CAMILU] == 6
    assert CHALO not in p.index or p[CHALO] == 0
    assert correr()["resumen"]["horas_totales"] == pytest.approx(44.48)


def test_cascada_servicios_sin_mezclar_plantas():
    r = correr()["resumen"]
    margen = 512000 - 59678
    assert r["margen_servicios"] == margen             # las plantas no entran al margen de servicios
    assert r["reserva_espacio"] == round(margen * 0.15)
    assert r["fondo_comun"] == round(margen * 0.10)
    assert r["excedente_bolsa"] == margen - r["reserva_espacio"] - r["fondo_comun"]


def test_plantas_sin_productores_quedan_sin_asignar():
    res = correr()
    r = res["resumen"]
    assert r["sin_asignar"] == pytest.approx(0.5 * 28500, abs=1)
    assert r["productos_a_espacio"] == pytest.approx(0.25 * 28500, abs=1)
    assert any("sin productor" in a.lower() for a in res["alertas"])
    p = res["personas"].set_index("Persona")
    assert p.loc[DIEGO, "Como vendedor/a"] == pytest.approx(0.25 * 28500, abs=1)


def test_plantas_50_25_25_con_produccion():
    prod = [{"ID": "x1", "ProyectoID": PID, "ItemID": "p-viva", "Persona": DIEGO, "Cantidad": 12, "PorConfirmar": "FALSE"},
            {"ID": "x2", "ProyectoID": PID, "ItemID": "p-viva", "Persona": CALA, "Cantidad": 8, "PorConfirmar": "FALSE"}]
    p = correr(produccion=prod)["personas"].set_index("Persona")
    assert p.loc[DIEGO, "Como productor/a"] == pytest.approx(0.5 * 16000 * 12 / 20, abs=1)
    assert p.loc[CALA, "Como productor/a"] == pytest.approx(0.5 * 16000 * 8 / 20, abs=1)


@pytest.mark.parametrize("metodo", list(M.METODOS))
def test_todos_los_metodos_cuadran(metodo):
    res = correr(metodo=metodo)
    r = res["resumen"]
    assert res["balance_ok"], r
    assert r["diferencia_cuadratura"] == 0
    assert r["aporte_a_aucca"] + r["fondo_comun"] + r["pagos_trabajo"] + r["sin_asignar"] \
        == r["ingreso_total"] - r["costos_total"]


def test_el_metodo_cambia_el_reparto():
    a = correr(metodo="A")["personas"].set_index("Persona")["Pago por trabajo"]
    e = correr(metodo="E")["personas"].set_index("Persona")["Pago por trabajo"]
    assert (a != e).any()


def test_parametros_cambian_resultados():
    assert correr(pct_espacio=30.0)["resumen"]["excedente_bolsa"] < correr()["resumen"]["excedente_bolsa"]


def test_reembolsos_ya_pagados_y_pendientes():
    assert correr()["resumen"]["reembolsos"] == 0       # todos declararon que ya les devolvieron
    pend = copy.deepcopy(D["coop_costos"])
    for c in pend:
        c["Reembolsado"] = "FALSE"
    p = correr(costos=pend)["personas"].set_index("Persona")
    assert p.loc[NIKO, "Reembolso de gastos"] == 12000
    assert p.loc[CALA, "Reembolso de gastos"] == 45278


def test_horas_de_productos_no_entran_a_la_bolsa():
    reg = copy.deepcopy(D["coop_registro"])
    reg.append({"ID": "z1", "ProyectoID": PID, "Persona": DIEGO, "Tarea": "Puesto de plantas", "ItemID": "p-viva",
                "Horas": 4, "Nivel": 1, "Esfuerzo": "", "Origen": "Real", "Evidencia": ""})
    p = correr(registro=reg)["personas"].set_index("Persona")
    assert p.loc[DIEGO, "Horas en productos"] == 4
    assert p.loc[DIEGO, "Horas"] == 13


def test_datos_por_confirmar_se_marcan():
    assert correr()["resumen"]["por_confirmar"] is True   # horas de Camilú y Diego sin desglose


def test_sin_horas_alerta():
    res = M.calcular(D["coop_proyectos"][0], D["coop_items"], [], [], [], [], [], M.DEFAULT_PARAMS)
    assert any("horas" in a.lower() for a in res["alertas"])


def test_plan_escala_con_asistentes():
    pr = D["coop_proyectos"][0]
    p1 = M.calcular_plan(pr, D["coop_items"], D["coop_costos"], D["coop_personas"], asistentes=32)
    p2 = M.calcular_plan(pr, D["coop_items"], D["coop_costos"], D["coop_personas"], asistentes=16)
    assert p2["resumen"]["ingreso_servicios"] == p1["resumen"]["ingreso_servicios"] // 2
    assert p1["resumen"]["valor_hora_estimado"] > 0
    assert not p1["equilibrio"].empty


def test_migracion_de_estimaciones_a_datos_reales(tmp_path, monkeypatch):
    from secciones import coop_datos as CD
    monkeypatch.setattr(CD, "_LOCAL", tmp_path)
    monkeypatch.setattr(CD, "usa_sheets", lambda: False)
    # instalación vieja: solo hay horas estimadas de la primera carga
    vieja = [{"ID": f"r{n}", "ProyectoID": PID, "Persona": DIEGO, "Tarea": "x", "ItemID": "", "Horas": 1,
              "Nivel": "1", "Esfuerzo": "", "Origen": "Estimado", "Evidencia": ""} for n in range(1, 21)]
    CD._escribir_todo("coop_registro", pd.DataFrame(vieja))
    CD._escribir_todo("coop_proyectos", pd.DataFrame(D["coop_proyectos"]))
    assert CD.migrar_a_datos_reales() is True
    reg = CD.cargar_proyecto("coop_registro", PID)
    assert reg["ID"].str.startswith("rh").all() and len(reg) == len(D["coop_registro"])
    assert CD.cargar_proyecto("coop_costos", PID)["Monto"].astype(int).sum() == 59678
    assert len(CD.cargar("coop_personas")) == 7
    # una segunda vez no hace nada
    assert CD.migrar_a_datos_reales() is False
    # y no pisa datos que alguien ya editó
    CD._escribir_todo("coop_registro", pd.DataFrame(vieja[:1] + [dict(vieja[1], Origen="Real")]))
    assert CD.migrar_a_datos_reales() is False


class _HojaFalsa:
    def __init__(self, titulo, filas):
        self.title, self.filas = titulo, filas

    def clear(self):
        self.filas = []

    def update(self, values, range_name="A1", value_input_option="RAW"):
        self.filas = values


class _LibroFalso:
    """Cuenta las llamadas de lectura para comprobar que no se agota la cuota de Google."""
    def __init__(self):
        self.hojas = {}
        self.lecturas = 0

    def worksheets(self):
        self.lecturas += 1
        return list(self.hojas.values())

    def add_worksheet(self, title, rows, cols):
        self.hojas[title] = _HojaFalsa(title, [])
        return self.hojas[title]

    def values_batch_get(self, rangos):
        self.lecturas += 1
        return {"valueRanges": [{"values": self.hojas[r].filas} for r in rangos]}


def test_sheets_lee_todo_junto_y_no_relee_al_escribir(monkeypatch):
    from secciones import coop_datos as CD
    libro = _LibroFalso()
    monkeypatch.setattr(CD, "usa_sheets", lambda: True)
    monkeypatch.setattr("data.google._get_spreadsheet", lambda: libro, raising=False)
    CD._CACHE.update(t=0.0, datos={}, ws={})
    for t in CD.TABLAS:
        CD.cargar(t)
    assert libro.lecturas == 2                     # 1 listado de hojas + 1 lectura por lote, no una por tabla
    CD._escribir_todo("coop_personas", pd.DataFrame([{"Persona": "Ana", "ValorHora": "5000"}]))
    assert CD.cargar("coop_personas", fresco=True)["Persona"].tolist() == ["Ana"]
    assert libro.hojas["coop_personas"].filas[1][0] == "Ana"
    assert libro.lecturas == 2                     # escribir y volver a leer no gasta cuota
    CD._CACHE.update(t=0.0, datos={}, ws={})


def test_restaurar_proyecto_si_no_esta(tmp_path, monkeypatch):
    from secciones import coop_datos as CD
    monkeypatch.setattr(CD, "_LOCAL", tmp_path)
    monkeypatch.setattr(CD, "usa_sheets", lambda: False)
    assert CD.proyecto_inicial_presente() is False
    CD.restaurar_proyecto_inicial()
    assert CD.proyecto_inicial_presente() is True
    assert len(CD.cargar_proyecto("coop_registro", PID)) == len(D["coop_registro"])
    assert len(CD.cargar_proyecto("coop_costos", PID)) == len(D["coop_costos"])
    # repetirlo no duplica nada
    CD.restaurar_proyecto_inicial()
    assert len(CD.cargar_proyecto("coop_registro", PID)) == len(D["coop_registro"])
    assert len(CD.cargar("coop_proyectos")) == 1
    # si el proyecto se borra pero quedan filas huérfanas, se conservan
    CD._escribir_todo("coop_proyectos", pd.DataFrame(columns=CD.TABLAS["coop_proyectos"]))
    CD.restaurar_proyecto_inicial()
    assert len(CD.cargar_proyecto("coop_registro", PID)) == len(D["coop_registro"])


def test_pendientes_con_tablas_vacias_desde_sheets(monkeypatch):
    """Con datos leídos de Sheets, una tabla vacía (p. ej. producción) no debe romper el conteo."""
    from secciones import coop_datos as CD, cooperativa as C
    libro = _LibroFalso()
    monkeypatch.setattr(CD, "usa_sheets", lambda: True)
    monkeypatch.setattr("data.google._get_spreadsheet", lambda: libro, raising=False)
    CD._CACHE.update(t=0.0, datos={}, ws={})
    CD.restaurar_proyecto_inicial()
    pend = C._pendientes(PID)
    assert pend["producción"] == 0 and pend["horas"] == 2 and pend["ventas"] == 2
    CD._CACHE.update(t=0.0, datos={}, ws={})


def test_observaciones_explican_los_datos():
    from secciones import coop_observaciones as O
    res = correr(metodo="D")
    pers = res["personas"]
    ctx = " ".join(O.obs_contexto(pers, res["resumen"], pd.DataFrame(D["coop_registro"]), pd.DataFrame(D["coop_costos"])))
    assert "44,48" in ctx and "Todos ya fueron devueltos" in ctx and "Ninguno tiene boleta" in ctx
    assert "$28.500" in ctx
    assert DIEGO in ctx and CAMILU in ctx          # horas sin línea: aporte en $0
    d = " ".join(O.obs_escenario(M.params_completos({"metodo": "D"}), res))
    assert "parte compartida" in d and "$14.250" in d
    e = " ".join(O.obs_escenario(M.params_completos({"metodo": "E"}), correr(metodo="E")))
    assert "mismo" in e or "Ignora las horas" in e


def test_observaciones_comparativo():
    from secciones import coop_observaciones as O
    tabla = pd.DataFrame({"A": {"x": 100, "y": 50}, "B": {"x": 60, "y": 90}})
    txt = " ".join(O.obs_comparativo(tabla, [150, 150]))
    assert "misma plata" in txt and "más cambia" in txt
