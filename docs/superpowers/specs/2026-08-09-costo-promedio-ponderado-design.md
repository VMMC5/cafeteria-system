# Costo de insumo por promedio ponderado — diseño

**Fecha:** 2026-08-09
**Estado:** aprobado (brainstorming cerrado, pendiente plan de implementación)

## Problema

Cada compra pisa el costo del insumo con el último costo pagado
(`compra_service.crear_compra`, `backend/app/services/compra_service.py:85`:
`insumo.costo_unitario = item.costo_unitario`). Con compras a precios distintos, la valuación
del inventario miente: 10 kg comprados a $95 y 8 kg a $98.50 dejan el insumo "valuado" a $98.50
como si los 18 kg hubieran costado eso.

Hallazgo del brainstorming que acota el slice: `insumo.costo_unitario` no se muestra hoy en
ninguna pantalla ni reporte — lo escriben las compras y el PATCH manual, lo devuelve la API
(`InsumoOut`) y lo lee `seed_demo`. Este slice es de **corrección de datos**, no de UI.

## Decisiones

1. **Promedio ponderado al comprar:**
   `nuevo_costo = (stock_actual × costo_actual + cantidad × costo_compra) / (stock_actual + cantidad)`.
2. **2 decimales, redondeando** con `ROUND_HALF_UP` al persistir cada compra. La columna sigue
   `Numeric(10,2)` — sin migración, coherente con la regla del proyecto (dinero a 2 decimales).
   La deriva por redondeo es de centavos y se recalibra sola con cada compra.
3. **Bordes:** si `stock_actual <= 0` o `costo_actual == 0`, el costo nuevo es directamente el
   de la compra. Evita el promedio diluido por stock fantasma a $0 (10 pzas a $0 + 5 a $30
   daría $10, un costo que nadie pagó).
4. **El PATCH manual de costo se conserva** (`insumo_service.actualizar`): es la válvula de
   recalibración del admin.

## Diseño

### Backend — `compra_service.py` (único archivo de producción)

Helper puro en el mismo módulo:

```python
def _costo_promedio(
    stock_actual: Decimal, costo_actual: Decimal,
    cantidad: Decimal, costo_compra: Decimal,
) -> Decimal:
    """Promedio ponderado del costo tras una compra, a 2 decimales.

    Si el inventario previo no tiene valor (stock <= 0 o costo 0), el costo
    nuevo es el de la compra: promediar contra valor cero diluiría el costo
    con unidades que nadie pagó.
    """
    if stock_actual <= 0 or costo_actual == 0:
        return costo_compra
    total_previo = stock_actual * costo_actual
    total_compra = cantidad * costo_compra
    return ((total_previo + total_compra) / (stock_actual + cantidad)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
```

En el bucle de `crear_compra`, **el orden importa** — el promedio usa el stock previo, así que
el costo se calcula antes de sumar el stock (hoy el stock se suma primero):

```python
        insumo = insumos[item.id_insumo]
        insumo.costo_unitario = _costo_promedio(
            insumo.stock_actual, insumo.costo_unitario,
            item.cantidad, item.costo_unitario,
        )
        insumo.stock_actual = insumo.stock_actual + item.cantidad
```

Si una compra trae el mismo insumo en dos líneas, el cálculo **compone secuencialmente**: la
segunda línea promedia contra el resultado (costo y stock) de la primera. El dict `insumos` ya
comparte la misma instancia entre líneas, así que esto ocurre solo con el orden correcto de las
dos asignaciones.

Nota de precisión: `stock_actual` es `Numeric(10,3)` (PR #26) y `costo_actual` `Numeric(10,2)`;
la aritmética es `Decimal` exacta y solo se cuantiza el resultado final.

### Lo que NO cambia

- `insumo_service` (PATCH manual de costo), `receta_service`, `venta_service`.
- El kárdex: `MovimientoInventario` no registra costo por movimiento (sería una feature aparte
  — histórico de valuación — hoy sin consumidor).
- `seed_demo`: genera compras al costo vigente del insumo; promediar contra el mismo costo da
  el mismo costo (`(x·c + y·c)/(x+y) = c`), así que no necesita ajuste. La no-regresión la
  cubre `backend/tests/test_seed_demo.py`, que ejecuta `seed_demo` completo.
- Los tests existentes de compras usan todos insumos con costo inicial 0 (verificado): el
  borde acordado los mantiene verdes sin tocarlos.
- Ninguna pantalla ni template: nada muestra `costo_unitario` de insumo hoy.
- `CompraItemIn.costo_unitario` (validación `ge=0`) y `DetalleCompra` (el detalle histórico de
  la compra conserva el costo pagado real, que es su función).

## Pruebas

**Del helper puro (unit, sin BD):**
- Promedio simple: 10 @ $95 + 8 @ $98.50 → $96.56 (verifica el `ROUND_HALF_UP` sobre
  $96.5555…).
- Redondeo hacia abajo: caso cuya fracción caiga por debajo de .005.
- `stock == 0` → costo de la compra; `costo_actual == 0` → costo de la compra.
- Composición secuencial: dos líneas del mismo insumo en una compra.

**De la API (integración, `backend/tests/test_compras_api.py`):**
- Compra sobre insumo con stock y costo previos reales (p. ej. stock 10 @ $95, compra 8 @
  $98.50) → `GET /insumos/{id}` devuelve `costo_unitario == "96.56"` y el detalle de la compra
  conserva `costo_unitario == "98.50"` (el costo pagado no se promedia).
- `test_crear_compra_ok` existente (insumo con costo 0 → toma el de la compra, espera 20.0)
  debe seguir pasando **sin tocarlo**: el borde de costo 0 lo garantiza.
- Si algún otro test existente asumía "último costo" con costo previo ≠ 0, se actualiza a la
  expectativa del promedio, con comentario del porqué.

## Verificación manual (la hace el usuario)

1. Insumo con stock y costo conocidos (p. ej. 10 kg @ $95.00, visible vía `GET /insumos/{id}`
   en Swagger).
2. Compra móvil de 8 kg @ $98.50 → el insumo queda en `96.56`, no en `98.50`.
3. Segunda compra a un precio distinto → el costo se mueve hacia el promedio, no salta al
   último precio.
4. Compra sobre un insumo recién creado (costo 0) → toma el costo de la compra tal cual.

## Deuda que queda anotada

- El kárdex no registra el costo por movimiento: sin histórico de valuación, el promedio solo
  vive en el estado actual del insumo. Si algún día se quiere un reporte de valuación en el
  tiempo, habrá que añadir costo a `MovimientoInventario`.
- La deriva de centavos por cuantizar a 2 decimales en cada compra es aceptada por diseño.
