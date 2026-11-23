import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from secciones import coop_motor as M
from secciones.coop_ejemplo import datos_ejemplo, DIEGO, CALA, TAIS, CAMILU, NIKO

D = datos_ejemplo()


def correr(**p):
    params = M.params_completos({})
    params.update(p)
    return M.calcular(D["coop_proyectos"][0], D["coop_items"], D["coop_ventas"], D["coop_produccion"],
                      D["coop_registro"], D["coop_costos"], D["coop_personas"], params)


def test_repartir_conserva_el_total():
    r = M.repartir(1000, {"a": 1, "b": 1, "c": 1})
    assert sum(r.values()) == 1000 and sorted(r.values()) == [333, 333, 334]
    assert M.repartir(100, {}) == {}


def test_ingresos_del_dia_13():
    r = correr()["resumen"]
    assert r["ingreso_servicios"] == 512000            # $16.000 × 32 (acta 8 nov)
    assert r["ingreso_productos"] == 15 * 3500 + 6 * 2500 + 12 * 1000   # 79.500
    assert r["costos_total"] == 108000


def test_cascada_servicios():
    r = correr()["resumen"]
    margen = 512000 - 108000
    assert r["margen_servicios"] == margen
    assert r["reserva_espacio"] == round(margen * 0.15)
    assert r["fondo_comun"] == round(margen * 0.10)
    assert r["excedente_bolsa"] == margen - r["reserva_espacio"] - r["fondo_comun"]


def test_productos_50_25_25():
    res = correr()
    p = res["personas"].set_index("Persona")
    assert p.loc[TAIS, "Como productor/a"] == pytest.approx(0.5 * 15000 * 6 / 10, abs=1)
    assert p.loc[CAMILU, "Como productor/a"] == pytest.approx(0.5 * 15000 * 4 / 10 + 0.5 * 12000, abs=1)
    assert p.loc[DIEGO, "Como productor/a"] == pytest.approx(0.5 * 52500 * 12 / 20, abs=1)
    assert p.loc[CALA, "Como productor/a"] == pytest.approx(0.5 * 52500 * 8 / 20, abs=1)
    assert p.loc[CALA, "Como vendedor/a"] == pytest.approx(0.25 * 21000, abs=1)   # vendió 6 vivas
    assert res["resumen"]["productos_a_espacio"] == pytest.approx(0.25 * 79500, abs=2)


@pytest.mark.parametrize("metodo", list(M.METODOS))
def test_todos_los_metodos_cuadran(metodo):
    res = correr(metodo=metodo)
    r = res["resumen"]
    assert res["balance_ok"], r
    prod = res["personas"]["Como productor/a"].sum() + res["personas"]["Como vendedor/a"].sum()
    assert res["comparacion"][metodo].sum() - prod == r["excedente_bolsa"]
    assert r["reserva_espacio"] + r["fondo_comun"] + r["productos_a_espacio"] + r["pagos_trabajo"] \
        == r["ingreso_total"] - r["costos_total"]


def test_el_metodo_cambia_el_reparto():
    a = correr(metodo="A")["personas"].set_index("Persona")["Pago por trabajo"]
    e = correr(metodo="E")["personas"].set_index("Persona")["Pago por trabajo"]
    assert (a != e).any()


def test_parametros_cambian_resultados():
    assert correr(pct_espacio=30.0)["resumen"]["excedente_bolsa"] < correr()["resumen"]["excedente_bolsa"]


def test_aporte_y_reembolsos():
    p = correr()["personas"].set_index("Persona")
    assert p.loc[NIKO, "Reembolso de gastos"] == 45000
    assert p.loc[NIKO, "Aporte en servicios ($)"] > 0
    assert p.loc[DIEGO, "Aporte en productos ($)"] > 0
    assert p["% del ingreso generado"].sum() <= 100.5


def test_horas_de_productos_no_entran_a_la_bolsa():
    p = correr()["personas"].set_index("Persona")
    assert p.loc[DIEGO, "Horas en productos"] == 9
    assert p.loc[DIEGO, "Horas"] == 5.5 + 2 + 3 + 3


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
