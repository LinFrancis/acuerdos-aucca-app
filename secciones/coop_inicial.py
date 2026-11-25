"""Primer proyecto de la plataforma: «Visita Red de Escuelas Comunitarias» (viernes 13 de nov 2026).

Los precios de los servicios y el total ($512.000 = $16.000 × 32) vienen del acta del 8 de
noviembre. Las horas, gastos, ventas y valores de hora son los que cada persona declaró el 23 y
24 de noviembre de 2026 (ver «Informacion_declarada_visita_13_noviembre.docx»). Lo que aún no
entregaron (horas por tarea de Camilú, ventas de Camilú, quién produjo cada planta, valor de hora
de Camilú, Chalo y Francis) queda marcado como «por confirmar».
"""
CHALO, CAMILU, NIKO, DIEGO, FRANCIS, TAIS, CALA = (
    "🚴🏻Chalo", "🌿Camilú", "⚽Niko", "🍃Diego", "🪈Francis", "🌌Tais", "🌊Cala")
PID = "p-visita-13nov"
# IDs de la primera carga (estimaciones). Si el registro de horas solo tiene estos, nadie lo ha tocado
# y se puede reemplazar por los datos reales.
IDS_REGISTRO_ESTIMADO = {f"r{n}" for n in range(1, 21)}


def datos_proyecto_inicial() -> dict[str, list[dict]]:
    proyecto = [{
        "ID": PID, "Nombre": "Visita Red de Escuelas Comunitarias", "Tipo": "Visita / jornada",
        "Fecha": "2026-11-13", "Estado": "En cierre", "Cliente": "Red de Escuelas Comunitarias",
        "Asistentes": 32, "IVA": "Exento", "Escenario": "",
        "Descripcion": "Recorrido por las estaciones, snack, 2 talleres y almuerzo de cierre para 32 personas adultas. "
                       "Propuesta económica del acta del 8 de noviembre: $16.000 por persona, $512.000 sin IVA. "
                       "Horas, gastos y ventas cargados con lo que declaró cada persona (24 nov). Falta definir el reparto del dinero."}]

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
        prod("p-viva", "Planta viva", "Plantas vivas del invernadero", 3500, 20, "", "", 0),
        prod("p-seca", "Planta seca", "Plantas secas (arreglos)", 2500, 10, "", "", 0),
        prod("p-semillas", "Semillas", "Sobres de semillas", 1000, 15, "", "", 0),
    ]
    # Ventas declaradas por Diego: $12.500 en plantas secas y $16.000 en plantas vivas. Cada total se
    # registra como una venta agrupada (cantidad 1 × monto) porque no declaró las unidades.
    # El detalle de ventas de Camilú del día 13 aún no existe.
    ventas = [("p-seca", 1, 12500, DIEGO), ("p-viva", 1, 16000, DIEGO)]
    ventas = [{"ID": f"v{n}", "ProyectoID": PID, "ItemID": a, "Cantidad": b, "PrecioUnit": c,
               "Vendedor": d, "Productor": "", "Medio": "", "Fecha": "2026-11-13", "PorConfirmar": "TRUE"}
              for n, (a, b, c, d) in enumerate(ventas, 1)]
    produccion = []   # nadie ha declarado quién produjo cada planta
    # Gastos: compras de Cala ($57.278 en total, con el detalle por preparación que ella entregó),
    # masas de Nico y traslado de Tais. Todos ya reembolsados, ninguno con boleta.
    costos = [
        ("Colación (pan, palta, queso, frutillas y jugo)", 28753, CALA, "s-snack", "FALSE"),
        ("Insumos de las empanadas, sin las masas", 16525, CALA, "s-almuerzo", "FALSE"),
        ("Masas de empanadas", 12000, NIKO, "s-almuerzo", "FALSE"),
        ("Traslado de Tais (micro y metro). Diego le adelantó $5.000 desde la venta de plantas", 2400, TAIS, "", "TRUE"),
    ]
    costos = [{"ID": f"c{n}", "ProyectoID": PID, "Fecha": "2026-11-13", "Concepto": a, "Monto": b,
               "PagadoPor": c, "ItemID": d, "ConBoleta": "FALSE", "Reembolsado": "TRUE", "PorConfirmar": pc}
              for n, (a, b, c, d, pc) in enumerate(costos, 1)]
    # persona, tarea, línea, horas, nivel, esfuerzo (1–5, si lo declaró), origen
    reg = [
        (NIKO, "Comprar masas de empanadas", "s-almuerzo", 0.33, 1, "", "Real"),
        (NIKO, "Limpiar cocina y preparar relleno de empanadas", "s-almuerzo", 4, 1, "", "Real"),
        (NIKO, "Guiar el recorrido", "s-recorrido", 2, 3, "", "Real"),
        (NIKO, "Armar y hornear empanadas", "s-almuerzo", 2, 1, "", "Real"),
        (NIKO, "Ordenar el espacio después de la visita", "", 2, 1, "", "Real"),
        (CALA, "Propuesta de colación: planificar, cotizar menú y calcular gastos", "s-snack", 0.5, 2, 1, "Real"),
        (CALA, "Compras en feria, supermercados y locales de Talagante (snack y empanadas)", "", 2, 1, 4, "Real"),
        (CALA, "Cotizar, encargar y retirar 32 panes", "s-snack", 0.25, 1, 1, "Real"),
        (CALA, "Remojo y lavado de frutillas, jugo para 40 porciones", "s-snack", 2, 1, 3, "Real"),
        (CALA, "Preparar pan con palta y queso", "s-snack", 1.5, 1, 3, "Real"),
        (CALA, "Montaje de la mesa de alimentación", "", 0.5, 1, 1, "Real"),
        (DIEGO, "Coordinación, planificación y propuesta del documento de la visita", "", 3, 2, "", "Real"),
        (DIEGO, "Orden del invernadero y del patio", "", 2, 1, "", "Real"),
        # Horas juntas: puesto/ventas, sala, fotos, guardián del tiempo y orden (sin el taller, que va aparte). Falta separarlas.
        (DIEGO, "Puesto de AUCCA, sala, registro fotográfico, guardián del tiempo y orden posterior (9:00–17:00, sin el taller)", "", 7, 2, "", "Estimado"),
        (TAIS, "Planificación y reunión con Diego, Nico y Camilú", "", 0.8, 2, "", "Real"),
        (TAIS, "Preparar la presentación (trabajó más de 6 h; cuenta 3)", "", 3, 3, "", "Real"),
        (TAIS, "Orden zona de hornos, limpieza de sillas, sala y baño", "", 0.6, 1, "", "Real"),
        (TAIS, "Recorrido de AUCCA", "s-recorrido", 2, 3, "", "Real"),
        (TAIS, "Dos talleres de 1 hora", "s-talleres", 2, 3, "", "Real"),
        # Camilú declaró solo su horario; falta el desglose por tarea.
        (CAMILU, "Horario 9–15 h: limpieza de baños, jugos, lavado de loza y ventas (sin el recorrido; sin desglose)", "", 4, 2, "", "Estimado"),
        # El recorrido cuenta como un taller y cada taller dura lo mismo que declaró Tais (recorrido 2 h, taller 1 h).
        (DIEGO, "Taller de propagación de especies vegetales (1 h, igual que Tais por taller)", "s-talleres", 1, 3, "", "Estimado"),
        (CAMILU, "Recorrido guiado de AUCCA (2 h, igual que Tais)", "s-recorrido", 2, 3, "", "Estimado"),
    ]
    registro = [{"ID": f"rh{n}", "ProyectoID": PID, "Persona": a, "Tarea": b, "ItemID": c, "Horas": d,
                 "Nivel": e, "Esfuerzo": f, "Origen": g, "Evidencia": ""}
                for n, (a, b, c, d, e, f, g) in enumerate(reg, 1)]
    # valor de hora declarado (promedio o mínimo); para quienes no respondieron queda una estimación
    tarifas = {CHALO: (8000, True), CAMILU: (12000, True), NIKO: (10000, False), DIEGO: (15000, False),
               FRANCIS: (12000, True), TAIS: (10000, False), CALA: (10000, False)}
    ofrece = {
        CHALO: "Mantención, construcción, orden del espacio", CAMILU: "Recorridos, plantas, semillas, jugos, ventas",
        NIKO: "Cocina, recorridos (cultivo, bosquicultura, plantas medicinales, bioconstrucción, sustentabilidad), logística",
        DIEGO: "Coordinación, talleres de reproducción de especies, ventas, invernadero",
        FRANCIS: "Registro, administración, sistematización",
        TAIS: "Talleres, eficiencia hídrica (OCAS, SUDS), gasfitería, presentaciones, recorridos",
        CALA: "Cocina, compras y logística de alimentación, compostaje, vivero"}
    notas = {
        NIKO: "Declaró $10.000 promedio. Exigencia general 4 de 5. Prefiere repartir por horas.",
        CALA: "Declaró $10.000 promedio. Prefiere por horas considerando el tipo de tarea. Propone no contar tareas de semanero como horas.",
        DIEGO: "Declaró $15.000 promedio, o menos con precio diferenciado según para quién trabaje.",
        TAIS: "Declaró desde $10.000 en AUCCA; en su empleo $10.000 a $30.000 según especialidad. Su traslado de 2 h no está en sus horas.",
        CAMILU: "No dio una cifra: depende de a quién le trabaja y en qué. Valor estimado.",
        CHALO: "Ese día cumplió solo tareas de semanero. Valor estimado.",
        FRANCIS: "Valor estimado: cada persona debe confirmar el suyo."}
    personas = [{"Persona": k, "ValorHora": v[0], "Ofrece": ofrece[k], "HorasMes": 20, "Nivel": "1",
                 "Notas": notas[k], "PorConfirmar": "TRUE" if v[1] else "FALSE"}
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
        gob("g9", "Tensión", "¿Qué tareas son de semanero y cuáles del proyecto?", "Espacio",
            "Cala propone no contar como horas de trabajo las tareas de semanero. Hay que definir cuáles de orden y limpieza lo son.",
            "Abierta", fecha="2026-11-23"),
        gob("g10", "Propuesta", "Ofrecer estas jornadas de forma regular, con publicidad", "Difusión",
            "Propuesta de Tais para generar más ingresos a la economía comunitaria e individual. Lo presentará en la próxima reunión.",
            "Abierta", "Tais", fecha="2026-11-23"),
    ]
    return {"coop_parametros": escenarios, "coop_gobernanza": gobernanza, "coop_proyectos": proyecto, "coop_items": items, "coop_ventas": ventas,
            "coop_produccion": produccion, "coop_costos": costos, "coop_registro": registro,
            "coop_personas": personas}
