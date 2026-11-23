"""Datos de EJEMPLO del proyecto «Visita Red de Escuelas Comunitarias» (viernes 13 de nov 2026).

Los precios de los servicios y el total ($512.000 = $16.000 × 32) vienen del acta del 8 de
noviembre. Las horas, los costos, las cantidades de productos y las tarifas son SIMULADOS
y deben reemplazarse por los datos reales que entregue cada persona.
"""
CHALO, CAMILU, NIKO, DIEGO, FRANCIS, TAIS, CALA = (
    "🚴🏻Chalo", "🌿Camilú", "⚽Niko", "🍃Diego", "🪈Francis", "🌌Tais", "🌊Cala")
PID = "p-visita-13nov"


def datos_ejemplo() -> dict[str, list[dict]]:
    proyecto = [{
        "ID": PID, "Nombre": "Visita Red de Escuelas Comunitarias", "Tipo": "Visita / jornada",
        "Fecha": "2026-11-13", "Estado": "En cierre", "Cliente": "Red de Escuelas Comunitarias",
        "Asistentes": 32, "IVA": "Exento", "Escenario": "",
        "Descripcion": "Recorrido por las estaciones, snack, 2 talleres y almuerzo de cierre para 32 personas adultas. "
                       "Propuesta económica del acta del 8 de noviembre: $16.000 por persona, $512.000 sin IVA.",
        "Simulado": "TRUE"}]

    def serv(i, cat, nombre, precio, horas):
        return {"ID": i, "ProyectoID": PID, "Tipo": "Servicio", "Categoria": cat, "Nombre": nombre,
                "Unidad": "persona", "Precio": precio, "CostoUnit": 0, "CantidadPlan": 32,
                "CantidadReal": 32, "HorasPlan": horas}

    def prod(i, cat, nombre, precio, plan, prods, vend, horas):
        return {"ID": i, "ProyectoID": PID, "Tipo": "Producto", "Categoria": cat, "Nombre": nombre,
                "Unidad": "unidad", "Precio": precio, "CostoUnit": 0, "CantidadPlan": plan,
                "Productores": prods, "Vendedor": vend, "HorasPlan": horas}

    items = [
        serv("s-recorrido", "Recorrido / visita guiada", "Recorrido por las estaciones", 3000, 12),
        serv("s-snack", "Snack / coffee", "Snack media mañana (sándwich + jugo)", 3000, 5),
        serv("s-talleres", "Taller", "2 talleres: eficiencia hídrica y propagación de nativas", 6000, 11),
        serv("s-almuerzo", "Alimentación (servicio)", "Empanada de vegetales + jugo (cierre)", 4000, 11),
        prod("p-viva", "Planta viva", "Plantas vivas del invernadero", 3500, 20, f"{DIEGO}, {CALA}", DIEGO, 7),
        prod("p-seca", "Planta seca", "Plantas secas (arreglos)", 2500, 10, f"{TAIS}, {CAMILU}", DIEGO, 5),
        prod("p-semillas", "Semillas", "Sobres de semillas", 1000, 15, CAMILU, DIEGO, 2),
    ]
    ventas = [  # (item, cantidad, vendedor, medio)
        ("p-viva", 9, DIEGO, "Efectivo"), ("p-viva", 6, CALA, "Transferencia"),
        ("p-seca", 4, DIEGO, "Efectivo"), ("p-seca", 2, DIEGO, "Transferencia"),
        ("p-semillas", 12, DIEGO, "Efectivo"),
    ]
    ventas = [{"ID": f"v{n}", "ProyectoID": PID, "ItemID": a, "Cantidad": b, "PrecioUnit": "",
               "Vendedor": c, "Productor": "", "Medio": d, "Fecha": "2026-11-13", "Simulado": "TRUE"}
              for n, (a, b, c, d) in enumerate(ventas, 1)]
    produccion = [("p-viva", DIEGO, 12), ("p-viva", CALA, 8), ("p-seca", TAIS, 6),
                  ("p-seca", CAMILU, 4), ("p-semillas", CAMILU, 15)]
    produccion = [{"ID": f"pr{n}", "ProyectoID": PID, "ItemID": a, "Persona": b, "Cantidad": c,
                   "Simulado": "TRUE"} for n, (a, b, c) in enumerate(produccion, 1)]
    costos = [
        ("Insumos de empanadas y jugo", 45000, NIKO, "s-almuerzo"),
        ("Insumos del snack", 30000, CALA, "s-snack"),
        ("Materiales de los talleres", 25000, TAIS, "s-talleres"),
        ("Gas, bebidas y desechables del día", 8000, DIEGO, ""),
    ]
    costos = [{"ID": f"c{n}", "ProyectoID": PID, "Fecha": "2026-11-13", "Concepto": a, "Monto": b,
               "PagadoPor": c, "ItemID": d, "ConBoleta": "FALSE", "Reembolsado": "FALSE", "Simulado": "TRUE"}
              for n, (a, b, c, d) in enumerate(costos, 1)]
    reg = [  # persona, tarea, item, horas, nivel
        (TAIS, "Planificar y guiar recorrido", "s-recorrido", 4, 3),
        (CAMILU, "Planificar y guiar recorrido", "s-recorrido", 4, 3),
        (NIKO, "Planificar y guiar recorrido", "s-recorrido", 4, 3),
        (TAIS, "Diseñar, comprar materiales y dictar taller", "s-talleres", 5.5, 3),
        (DIEGO, "Diseñar, comprar materiales y dictar taller", "s-talleres", 5.5, 3),
        (NIKO, "Comprar, armar y hornear empanadas", "s-almuerzo", 11, 1),
        (CALA, "Comprar y preparar snack", "s-snack", 4.5, 1),
        (DIEGO, "Armar, atender y desarmar puesto Aucca", "p-viva", 5, 1),
        (DIEGO, "Almácigos y plantas vivas", "p-viva", 4, 1),
        (CALA, "Almácigos y plantas vivas", "p-viva", 3, 1),
        (TAIS, "Plantas secas", "p-seca", 3, 1),
        (CAMILU, "Plantas secas y semillas", "p-seca", 2, 1),
        (DIEGO, "Orden del invernadero", "", 2, 1),
        (DIEGO, "Despeje de caminos y cacas de perros", "", 3, 1),
        (DIEGO, "Contacto con la contraparte y propuesta", "", 3, 2),
        (CAMILU, "Preparación de baños", "", 2.5, 1),
        (CALA, "Zona de compostaje", "", 2, 1),
        (CHALO, "Sala, mesas, sillas y sombras", "", 3, 1),
        (NIKO, "Basura y zona de reciclaje", "", 1.5, 1),
        (FRANCIS, "Registro, documentación y cuadratura", "", 2, 2),
    ]
    registro = [{"ID": f"r{n}", "ProyectoID": PID, "Persona": a, "Tarea": b, "ItemID": c, "Horas": d,
                 "Nivel": e, "Esfuerzo": "", "Origen": "Simulado", "Evidencia": ""}
                for n, (a, b, c, d, e) in enumerate(reg, 1)]
    tarifas = {CHALO: 8000, CAMILU: 12000, NIKO: 12000, DIEGO: 15000, FRANCIS: 12000, TAIS: 18000, CALA: 10000}
    ofrece = {
        CHALO: "Mantención, construcción, orden del espacio", CAMILU: "Recorridos, plantas, semillas, difusión",
        NIKO: "Cocina, recorridos, logística", DIEGO: "Talleres, ventas, coordinación, invernadero",
        FRANCIS: "Registro, administración, sistematización", TAIS: "Talleres, plantas secas, recorridos",
        CALA: "Cocina y snacks, compostaje, vivero"}
    personas = [{"Persona": k, "ValorHora": v, "Ofrece": ofrece[k], "HorasMes": 20, "Nivel": "1",
                 "Notas": "Valor simulado: pídele a cada persona que declare el suyo.", "Simulado": "TRUE"}
                for k, v in tarifas.items()]
    import json
    from secciones import coop_motor as M

    def esc(i, nombre, notas, **kw):
        prm = M.params_completos(kw)
        return {"ID": i, "Nombre": nombre, "Estado": "Borrador", "Notas": notas,
                "Parametros": json.dumps(prm, ensure_ascii=False), "Actualizado": "2026-11-23 00:00"}
    escenarios = [
        esc("e-a", "Opción 1 · Por horas", "Ruta 1 de la reunión del 22 nov: valor de las horas.", metodo="A"),
        esc("e-b", "Opción 2 · Por puntos de tarea", "Ruta 2: según actividad/rol con niveles de responsabilidad.", metodo="B"),
        esc("e-c", "Opción 3 · Mixta", "20% partes iguales, 40% horas, 40% puntos.", metodo="C"),
        esc("e-d", "Opción 4 · Por valor de cada línea", "Respeta el valor de cada rol de la propuesta del 8 nov.", metodo="D"),
        esc("e-f", "Opción 5 · Por tarifa declarada", "Usa el valor de hora de cada perfil.", metodo="F"),
    ]
    def gob(i, tipo, titulo, circulo, desc, estado, resp="", fecha="2026-11-22", rev="", obj="", res=""):
        return {"ID": i, "Tipo": tipo, "Titulo": titulo, "Circulo": circulo, "Descripcion": desc, "Estado": estado,
                "Responsable": resp, "Fecha": fecha, "Revision": rev, "Objeciones": obj, "Resultado": res}
    gobernanza = [
        gob("g1", "Círculo", "Producción y bioinsumos", "Producción", "Vivero, almácigos, hierbas, compost, kits de huerta.", "Acordada"),
        gob("g2", "Círculo", "Educación y facilitación", "Educación", "Talleres, visitas guiadas, asesorías.", "Acordada"),
        gob("g3", "Círculo", "Cocina y alimentación", "Cocina", "Empanadas, snacks, repostería, almuerzos.", "Acordada"),
        gob("g4", "Círculo", "Espacio e infraestructura", "Espacio", "Mantención de los 1.500 m², arriendos, mejoras.", "Acordada"),
        gob("g5", "Círculo", "Difusión y comercialización", "Difusión", "Comunicaciones, convocatoria, ventas, alianzas.", "Acordada"),
        gob("g6", "Tensión", "El trabajo invisible no se registra", "Espacio",
            "Baños, orden, compostaje, logística: se hacen pero no quedan visibles ni valorados.", "En conversación"),
        gob("g7", "Propuesta", "Reservar un % de cada actividad para caja chica e infraestructura", "Espacio",
            "Se habló de partir con 10% desde el próximo año; el costo real es mayor.", "En conversación", "Todo el grupo", rev="2027-03-01"),
        gob("g8", "Acuerdo", "Venta de plantas: 50% productor/a, 25% vendedor/a, 25% espacio", "Producción",
            "Acordado el 8 de noviembre; se afinará por producto.", "Acordada", "Todo el grupo", fecha="2026-11-08", rev="2027-03-01"),
    ]
    return {"coop_parametros": escenarios, "coop_gobernanza": gobernanza, "coop_proyectos": proyecto, "coop_items": items, "coop_ventas": ventas,
            "coop_produccion": produccion, "coop_costos": costos, "coop_registro": registro,
            "coop_personas": personas}
