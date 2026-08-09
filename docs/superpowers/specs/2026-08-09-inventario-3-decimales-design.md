# Inventario a 3 decimales — diseño

**Fecha:** 2026-08-09
**Estado:** aprobado (brainstorming cerrado, pendiente plan de implementación)

## Problema

El inventario guarda cantidades con 2 decimales (`Numeric(10,2)`) mientras que las recetas
guardan `cantidad_requerida` con 3 (`Numeric(10,3)`). La asimetría desincroniza el kárdex: una
receta de `0.125 kg` descuenta `0.13 kg` de stock porque Postgres redondea al escribir, y el
movimiento registrado no cuadra con lo que la receta dice consumir.

El parche actual vive en el móvil: `cantidadValida` limita a 2 decimales la cantidad de una línea
de receta, a propósito, para no provocar la desincronización. Este slice quita ese parche
ampliando el inventario a 3 decimales.

Además, hoy **nadie valida ni cuantiza decimales en la API**: Postgres redondea en silencio y el
usuario nunca se entera de que su número cambió.

## Alcance

Cuatro columnas de **cantidad** pasan de `Numeric(10,2)` a `Numeric(10,3)`:

| Modelo | Archivo | Columna |
|---|---|---|
| `Insumo` | `backend/app/models/inventario.py:33-34` | `stock_actual`, `stock_minimo` |
| `MovimientoInventario` | `backend/app/models/inventario.py:59` | `cantidad` |
| `DetalleCompra` | `backend/app/models/compra.py:56` | `cantidad` |

**Fuera de alcance (explícito):** todos los campos de dinero se quedan en 2 decimales —
`Insumo.costo_unitario`, `DetalleCompra.costo_unitario`, `Producto.precio_venta`,
`DetallePedido.precio_unitario`, `PagoVenta.monto`, `Gasto.monto`, totales y subtotales. Dos
decimales es lo correcto para pesos, y arrastrar el dinero a 3 convertiría un slice de inventario
en un barrido de ventas, pagos y reportes.

## Decisiones

1. **Solo las 4 cantidades.** Es el alcance mínimo que cierra la deuda con `cantidad_requerida`.
2. **Cantidades con más de 3 decimales se rechazan con 422**, no se cuantizan en silencio. La
   validación vive en el borde (Pydantic); la columna es la red de seguridad.
3. **Las cantidades se muestran recortando ceros a la derecha**: `500 pza`, `12.5 kg`,
   `0.125 kg`. Misma regla en móvil y web.
4. **La migración se aplica a mano** (`docker compose exec api alembic upgrade head`), no en el
   arranque del contenedor. Mantiene el control del esquema en el operador, igual que hoy.

## Diseño

### 1. Esquema y migración

Los cuatro `Column(Numeric(10, 2))` pasan a `Numeric(10, 3)`. Nueva revisión Alembic con
`down_revision = "a1557e1dd3bf"` (la única existente, el esquema inicial de 23 tablas) y cuatro
`op.alter_column(..., type_=sa.Numeric(10, 3))`.

Ampliar la escala en Postgres es no destructivo: `2.00` pasa a ser `2.000` sin reescribir
semántica ni bloquear la tabla de forma apreciable a esta escala de datos.

El `downgrade` vuelve a `(10,2)` y **pierde el tercer decimal por redondeo**. No se intenta
impedirlo; se documenta en el docstring de la revisión para que quien lo ejecute sepa lo que
pierde.

#### Dos avisos operativos

- **BD del volumen (dev/producción):** requiere `docker compose exec api alembic upgrade head`.
  Se documenta en `README.md` junto al seed y en `progress.md`.
- **BD de tests:** `backend/tests/conftest.py:78-83` hace `_ensure_database_exists` +
  `Base.metadata.create_all`, y **ninguna de las dos altera tablas existentes**. Si la BD
  `cafeteria_test` ya existe con `numeric(10,2)`, los tests de 3 decimales fallarían aunque el
  modelo esté correcto. Antes de correr la suite hay que tirarla una vez:

  ```bash
  docker compose exec db psql -U <user> -c 'DROP DATABASE IF EXISTS cafeteria_test'
  ```

  Es un requisito de ejecución del plan, no un cambio de código.

### 2. Validación en la API

Se añade `max_digits=10, decimal_places=3` a los cinco campos de cantidad de entrada:

| Schema | Archivo | Campo |
|---|---|---|
| `InsumoCreate` | `backend/app/schemas/insumo.py:18-19` | `stock_actual`, `stock_minimo` |
| `InsumoUpdate` | `backend/app/schemas/insumo.py:26` | `stock_minimo` |
| `MovimientoCreate` | `backend/app/schemas/insumo.py:33` | `cantidad` |
| `CompraItemIn` | `backend/app/schemas/compra.py:26` | `cantidad` |
| `RecetaLineaCreate` / `RecetaLineaUpdate` | `backend/app/schemas/receta.py:8,12` | `cantidad_requerida` |

`cantidad_requerida` ya vivía en una columna `(10,3)` pero sin validación, así que también
redondeaba en silencio a partir del cuarto decimal; entra por consistencia.

`max_digits=10` con `decimal_places=3` deja el tope en `9 999 999.999`, exactamente lo que
aguanta la columna: una cantidad que hoy revienta contra la base de datos ahora sale como 422
legible.

Los schemas `*Out` no cambian: declaran `Decimal` y FastAPI serializa el valor tal como lo trae
la columna (como string en JSON, convención ya establecida del proyecto).

**Ningún servicio cuantiza.** `insumo_service.registrar_movimiento`, `compra_service.crear` y
`receta_service` no cambian una línea: sus sumas y restas ya operan sobre `Decimal` y con escala
3 el resultado pasa a ser exacto en vez de redondeado.

### 3. Móvil

**Validación.** Un helper compartido `decimalesValidos(txt, max)` concentra el regex, junto con
`normalizar` (coma → punto, que hoy vive en `recetas.ts` y se mueve con él). Tres consumidores:

- `cantidadValida` (`mobile/src/lib/recetas.ts:11`): de `\.\d{1,2}` a `\.\d{1,3}`. El comentario
  que hoy explica por qué se limitaba a 2 se reemplaza por el criterio nuevo.
- `movimientoValido` (`mobile/src/lib/inventario.ts:8`): hoy solo pide `Number(txt) > 0`, así que
  la pantalla de Ajuste deja mandar `0.1234`. Con el 422 nuevo eso sería un error de red en la
  cara del cocinero; se le añade el límite de 3 decimales.
- `lineaCompraValida` (`mobile/src/lib/compras.ts:1`): igual sobre `cantidad`. `costo_unitario`
  se queda como está, coherente con dejar el dinero fuera de alcance.

**Presentación.** `mobile/src/api/coerce.ts:10-22` ya convierte `stock_actual`, `stock_minimo`,
`cantidad` y `cantidad_requerida` de string a `number` en el borde del cliente, y JS renderiza
`500` para `Number("500.000")` — el móvil ya recorta los ceros, pero por accidente, no por
diseño. Se hace explícito con `cantidad(value)` en `mobile/src/lib/format.ts`, junto a `money()`:
máximo 3 decimales, sin ceros de relleno. Se usa en los cuatro sitios de despliegue:

- `mobile/src/app/cocina/inventario.tsx` — `stock_actual` y `stock_minimo` de la lista
- `mobile/src/app/cocina/ajuste.tsx` — stock actual y stock resultante del movimiento
- `mobile/src/app/cocina/receta-detalle.tsx` — `cantidad_requerida` por línea
- `mobile/src/app/cocina/compra-nueva.tsx` — `cantidad` de cada línea capturada

Convierte una coincidencia frágil en una convención con nombre, igual que `money()` protege a los
importes.

### 4. Panel web

La gráfica "Nivel de inventario" del dashboard (`web/app/templates/dashboard/index.html:48-57`)
solo pinta `nombre`, `nivel_pct` y `bajo_minimo` — ninguna cantidad, **no cambia**.
`reporte_service.inventario_niveles` tampoco: su `float()` es para calcular el porcentaje, y
`stock_actual`/`stock_minimo` salen como `Decimal` intactos.

Queda un solo punto: `web/app/reportes/routes.py:36-37`, donde el armador de filas hace
`float(f["stock_actual"])`. Esas filas alimentan tres salidas a la vez —vista previa HTML, CSV y
celdas tipadas del XLSX—, así que no pueden volverse strings formateados sin romper el tipado
numérico de la hoja de cálculo.

Helper local `_cantidad(x)`: devuelve `int` si el valor es entero, `float` redondeado a 3 en
cualquier otro caso. Las celdas siguen siendo numéricas para XLSX y CSV, y la vista previa deja
de mostrar `500.0` para 500 servilletas — muestra `500`, `12.5`, `0.125`. Misma regla de recorte
que el móvil, sin sacrificar el tipo.

## Pruebas

**Backend** (`backend/tests/`):
- Round-trip exacto de 3 decimales: alta de insumo con `stock_actual = 0.125`; movimiento manual
  de `0.005`; ítem de compra de `0.125`.
- Consumo por receta: una línea de receta de `0.125` descontada tres veces deja `0.375` de stock
  y tres movimientos de `0.125` — el caso que hoy no cuadra.
- 422 con 4 decimales en cada uno de los cinco campos de entrada.
- Los tests de inventario, compras y recetas existentes siguen pasando sin cambios.

**Web** (`web/tests/`):
- `_cantidad` en sus tres formas: entero → `int`, fraccionario → `float` a 3, redondeo del cuarto
  decimal.
- Fila de reporte de inventario con stock fraccionario, con el stub Decimal-string de la
  convención del proyecto.

**Móvil** (`mobile/src/**/*.test.ts`):
- `decimalesValidos` y las tres funciones que lo consumen: 2, 3 y 4 decimales, coma decimal,
  cero, negativo, texto.
- `cantidad()`: enteros, fracciones, ceros de relleno (`"500.000"` → `500`), `null`/`undefined`.

## Verificación manual (la hace el usuario)

1. `docker compose exec api alembic upgrade head` sobre la BD real.
2. Alta de un insumo con stock `0.125` — se guarda y se muestra `0.125`, no `0.13`.
3. Ajuste de `0.005` sobre ese insumo — stock resultante `0.130`, mostrado como `0.13`.
4. Compra con cantidad fraccionaria — el kárdex registra la cantidad exacta.
5. Receta con `0.125` de un insumo: al entregar el pedido, el descuento es exacto.
6. Reporte de Inventario en el panel: vista previa, CSV y XLSX con las cantidades recortadas.

## Deuda que queda anotada

- Los campos de dinero siguen sin `decimal_places=2` en Pydantic: mismo redondeo silencioso, otra
  escala y otro radio de impacto (ventas, pagos, reportes).
- El `downgrade` de la migración pierde el tercer decimal por redondeo.
