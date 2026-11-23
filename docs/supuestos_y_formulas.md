# Supuestos y fórmulas

## 1. Qué viene de los acuerdos y qué es propuesta
| Tema | Estado | Fuente |
|---|---|---|
| Precios de los servicios del 13 (recorrido $3.000, snack $3.000, talleres $6.000, alimentación $4.000 por persona; $16.000 × 32 = $512.000 sin IVA) | Propuesta aprobada por asistentes | Acta 8 de noviembre |
| Reparto inicial «igualitario equiparando tareas» y visibilizar tareas de orden | Propuesta de esa reunión | Acta 8 de noviembre |
| Plantas: 50% productor/a, 25% vendedor/a, 25% espacio (AUCCA) | Acordado, con afinación pendiente por producto | Acta 8 de noviembre |
| Probar reparto por horas **y** por actividad/rol y comparar | Acordado | Reunión 22 de noviembre |
| Porcentaje para caja chica e infraestructura (10% mencionado) | Sin acuerdo | Reunión 22 de noviembre |
| Gastos de cuenta bancaria y firma electrónica (~$20.000) | Salen de los fondos de AUCCA, **no** del proyecto | Acta 22 de noviembre |
| Factura exenta de IVA; declarar a más tardar el 20 de diciembre | Hecho/plazo | Acta 22 de noviembre |
| Reserva de espacio 15%, fondo común 10%, factores de nivel 1,0–1,5, mezcla C 20/40/40, valor de referencia $20.000 la hora | **Hipótesis para simular**, no acuerdos | Borrador de ideas de la cooperativa |
| Horas, costos, cantidades vendidas y tarifas del proyecto de ejemplo | **Simulados** | Reemplazar con datos reales |

## 2. Estructura del dinero (cascada)
```
Servicios al cliente (ingreso) ─ costos de las líneas y del proyecto = MARGEN DE SERVICIOS
   ├─ % reserva de espacio ......... → AUCCA (se ingresa a mano en Finanzas)
   ├─ % fondo común ................ → queda en custodia del proyecto
   └─ resto = BOLSA DE TRABAJO ..... → se reparte por el método elegido (A–F)

Productos (cada venta) ─ costos imputados al producto = BASE
   ├─ % productor/es ............... → según unidades producidas
   ├─ % vendedor/a ................. → quien vendió
   └─ % espacio .................... → AUCCA (se ingresa a mano en Finanzas)
```
**Aporte a AUCCA** = reserva de espacio sobre servicios + parte «espacio» de los productos.

Cuadratura (siempre debe cerrar): `aporte a AUCCA + fondo común + pagos por trabajo + sin asignar = ingresos totales − costos totales`.

## 3. Métodos de reparto de la bolsa de trabajo
Sea *B* la bolsa, *hᵢ* las horas de la persona *i* y *H* el total de horas (solo de tareas de servicios y de base; las horas en productos se pagan por el % productor/vendedor).

| Método | Fórmula | Cuándo conviene |
|---|---|---|
| **A · Por horas** | `B × hᵢ / H` | Simple y fácil de auditar. No distingue tipo de tarea. |
| **B · Por puntos** | `pᵢ = Σ(horas × factor del nivel)`; `B × pᵢ / P` | Reconoce responsabilidad y preparación. Exige acordar los factores. |
| **C · Mixta** | `B × [ a/n + b·hᵢ/H + c·pᵢ/P ]` con a+b+c = 100% (se normaliza) | Equilibra igualdad, tiempo y responsabilidad. |
| **D · Por línea** | Cada línea de servicio aporta su margen neto a la bolsa; un % se comparte entre todos por horas de tareas de base y el resto va a quienes trabajaron en esa línea | Respeta el valor del rol de la propuesta del 8 de nov y reconoce la logística invisible. |
| **E · Partes iguales** | `B / n` (n = personas con horas) | Máxima igualdad. Ignora diferencias de aporte. |
| **F · Por tarifa declarada** | `B × (hᵢ·tarifaᵢ) / Σ(hⱼ·tarifaⱼ)` | Usa el valor de hora de cada perfil. Cuidado: puede premiar tarifas altas declaradas. |

**Niveles** (factores de ejemplo): 1 Operación y mantención = 1,0 · 2 Técnico especializado = 1,2 · 3 Diseño, facilitación y coordinación = 1,4 · 4 Dirección técnica y gestión = 1,5.

## 4. Productos
Por cada venta: `base = monto × (1 − costos imputados / ingreso del producto)`.
- Productor/es: `base × %productor`, repartido según **unidades producidas** de cada persona (o el productor indicado en la venta).
- Vendedor/a: `base × %vendedor`.
- Espacio: `base − productor − vendedor`.
Los porcentajes se definen por **categoría** (planta viva, planta seca, semillas, almácigo/kit, comida, postre, otro) en el escenario, y pueden sobrescribirse en la línea.

## 5. Redondeo
Todos los repartos usan el **método del mayor resto**: se reparten pesos enteros y la suma de los pagos es exactamente el monto a repartir.

## 6. Planificación
- Ingresos de servicios = precio × asistentes. Ingresos de productos = precio × cantidad planificada × escala.
- Costos = costos registrados + costo unitario × cantidad.
- **Valor por hora estimado** = bolsa de trabajo ÷ horas planificadas.
- **Resultado por línea** = ingreso − costos directos − horas planificadas × tarifa de referencia.
- **Punto de equilibrio** de un servicio = `⌈(costos de la línea + horas × tarifa de referencia) ÷ (precio × (1 − %espacio − %fondo))⌉` asistentes.

## 7. Límites
- No es asesoría legal ni tributaria (ver notas aparte).
- El modelo reparte lo que hay, no garantiza un ingreso mínimo.
- Los datos son tan buenos como lo que se registra: si falta una tarea o una venta, el reparto cambia.
