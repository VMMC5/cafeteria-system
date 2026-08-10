# Fixes menores de seguridad y robustez — diseño

**Fecha:** 2026-08-09
**Estado:** aprobado (brainstorming cerrado, pendiente plan de implementación)

## Problema

Tres pendientes chicos de la lista de deuda, de naturaleza parecida (seguridad/robustez), que
juntos dan un slice coherente:

1. **`/logout` del panel web responde a GET** (`web/app/auth/routes.py:47`). Cualquier
   `<img src=".../logout">` en cualquier página desloguea al admin (logout CSRF). El PR #25
   protegió los 14 POST del panel con `CSRFProtect`, pero el logout quedó fuera por ser GET.
2. **El móvil no renueva el token a media sesión.** El único refresh vive en el `bootstrap()`
   del store (`mobile/src/store/auth.ts:24-54`), que corre al arrancar la app. Si el access
   token expira con la app abierta, toda llamada empieza a fallar con 401 y la única salida es
   reiniciar la app.
3. **Falta el test de API para venta con pagos múltiples con excedente y referencia** — el
   último pendiente del PR #22. Existe `test_cobrar_pago_dividido_exacto` (2 pagos, suma
   exacta), pero el caso que se validó solo a mano (smoke del PR #22) — excedente en Efectivo +
   referencia en Tarjeta — no tiene test.

## Decisiones

1. Los tres fixes van en **una sola rama/PR** (`feat/fixes-logout-refresh-pagos` o similar).
2. **Logout por POST**, sin conservar GET (405 automático de Flask). Sin handler especial.
3. **Refresh-on-401 como interceptor axios** con single-flight y un solo reintento por
   petición. Las pantallas no cambian.
4. Cuando el refresh también falla: **Alert único** («Tu sesión expiró, inicia sesión de
   nuevo») + redirección al login vía `status: "noauth"`.

## Diseño

### 1. `/logout` por POST (panel web)

- `web/app/auth/routes.py:47`: `@bp.route("/logout", methods=["POST"])`. `CSRFProtect` global
  (PR #25) lo cubre automáticamente: POST sin token → página de rechazo CSRF con 400.
- `web/app/templates/base.html:34`: el `<a class="sidebar__logout">` se convierte en un
  `<form method="post" action="{{ url_for('auth.logout') }}">` con
  `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` y un `<button
  type="submit" class="sidebar__logout">` con el mismo icono SVG y texto.
- `web/app/static/css/app.css:26-28`: `.sidebar__logout` se ajusta para que el `<button>` se
  vea idéntico al enlace actual (reset de `background`/`border`/`padding`/`font`, `cursor:
  pointer`; conserva colores y hover). El form contenedor no debe alterar el layout del
  sidebar (`display: contents` en el form, o form con los estilos de posicionamiento que hoy
  tiene el enlace — decidir en el plan mirando el flex del sidebar).
- **Bono automático:** el test de CSRF del PR #25 que recorre todas las plantillas y exige un
  `csrf_token` dentro de cada `<form method="post">` cubrirá este form nuevo sin tocarlo.

**Tests** (`web/tests/test_auth.py` — hoy no existe ningún test de logout; los tres son
nuevos):
- Logout por POST (con sesión iniciada, CSRF deshabilitado en fixture como el resto): cierra
  sesión y redirige a `/login`.
- GET a `/logout` → **405**.
- En `web/tests/test_csrf.py` (validación activa): POST a `/logout` sin token → 400 con la
  página de rechazo. El test existente `test_post_sin_token_es_rechazado_con_400` usa una
  ruta representativa, no un barrido: el caso de logout se añade aparte porque su forma vive
  en `base.html` (todas las páginas), no en una plantilla de módulo.

### 2. Refresh-on-401 global (móvil)

**Lógica pura** en `mobile/src/lib/authRefresh.ts` (convención del proyecto: decisiones en
`lib/` con tests jest; el interceptor es pegamento delgado):

- `debeIntentarRefresh(status, url, esReintento): boolean` — `true` solo si `status === 401`,
  la URL no es `/auth/login` ni `/auth/refresh`, y no es ya un reintento.
- Gestión single-flight: una promesa de refresh compartida a nivel de módulo; mientras haya un
  refresh en vuelo, los demás 401 esperan esa misma promesa en vez de disparar otro. Al
  resolverse (éxito o fallo) se limpia.

**Interceptor** en `mobile/src/api/client.ts`, junto al de `coerceDecimals`:

1. Respuesta con error → si `debeIntentarRefresh(...)` es falso, propagar el error tal cual.
2. Si es verdadero: unirse al refresh en vuelo (o iniciarlo con el `refreshToken` de
   `useAuth.getState()`).
3. Refresh OK → `saveTokens` + actualizar el store (`accessToken`/`refreshToken`), reescribir
   `Authorization` en la config original, marcar `_retry` y reintentar **una vez**.
4. Refresh falla → `clearTokens()` + `set({ status: "noauth", ... })` (el layout redirige al
   login) + `Alert` único («Tu sesión expiró, inicia sesión de nuevo») protegido por bandera
   para no apilarse si varios 401 caen a la vez; propagar el error original.

**Lo que no cambia:** las pantallas (siguen pasando `access` como argumento), `bootstrap()`
(su refresh al arrancar sigue siendo el camino del arranque en frío), y el resto del client.

**Riesgo anotado:** el reintento usa el token nuevo, pero una pantalla ya montada puede seguir
pasando el `access` viejo como argumento en llamadas posteriores; como el store ya se
actualizó, el siguiente render toma el nuevo, y si mientras tanto llega otro 401 con el token
caducado, el interceptor vuelve a salvarlo (ahora con un refresh ya renovado, el single-flight
lo hace barato). El patrón "token como argumento" queda como está; el interceptor es la red.

**Tests** (`mobile/src/lib/authRefresh.test.ts` + ajustes en tests del client si aplica):
- `debeIntentarRefresh`: 401 normal → true; 401 de `/auth/login` → false; 401 de
  `/auth/refresh` → false; reintento → false; 500/403/timeout → false.
- Single-flight: dos peticiones concurrentes → un solo refresh; la promesa se limpia al
  resolver (el siguiente 401 posterior dispara un refresh nuevo).
- El fallo del refresh limpia y no deja promesa colgada.
- (El reintento HTTP en sí se verifica en el smoke manual; no se monta un mock de axios
  completo salvo que el plan encuentre barato hacerlo.)

### 3. Test de venta con pagos múltiples, excedente y referencia (API)

Un test nuevo en `backend/tests/test_ventas_api.py`, calcado del smoke manual del PR #22:

- Pedido de `116.0` (helper `_pedido` existente).
- `pagos: [{Efectivo, monto: 150.0}, {Tarjeta, monto: 16.0, referencia: "V-123"}]` → **201**.
- `cambio == 50.0` (suma 166 − total 116), `len(pagos) == 2`; localizar cada pago **por
  método** (no por índice: el orden de la relación no está garantizado): el de Tarjeta con
  `referencia == "V-123"`, el de Efectivo con `referencia is None`.
- La mesa queda Disponible (mismo assert que `test_cobrar_ok`).

Sin código de producción. Cierra el último pendiente del PR #22.

## Pruebas — resumen por capa

- **Backend:** +1 test (pagos múltiples). 227 → **228**.
- **Web:** 3 tests nuevos de logout (POST OK, GET 405, POST sin token 400). 123 → **126**.
- **Móvil:** `authRefresh.test.ts` (~6 tests de lógica pura). 84 → **~90** + `tsc` limpio.

## Verificación manual (la hace el usuario)

1. Panel web: cerrar sesión desde el sidebar (debe verse y funcionar igual que siempre);
   visitar `/logout` por URL directa → página de error 405, la sesión sigue viva.
2. Móvil: con la app abierta y sesión iniciada, esperar a que expire el access token (o
   acortar su TTL en `.env` para la prueba) y tocar cualquier pantalla que llame a la API: la
   acción debe completarse sola tras el refresh transparente, sin error visible.
3. Móvil: con ambos tokens caducados (o revocados), la siguiente acción muestra el Alert de
   sesión expirada y devuelve al login.

## Deuda que queda anotada

- El patrón móvil "token como argumento" en cada llamada sigue vigente; el interceptor lo
  complementa pero no lo reemplaza. Migrar a token implícito (interceptor de request) sería un
  refactor aparte, hoy sin justificación.
- La regla de excedente solo-Efectivo vive únicamente en el cliente móvil (`puedeCobrarPagos`);
  la API acepta excedente con cualquier método y calcula el cambio igual. Si algún día importa
  a nivel de API, es endpoint nuevo de validación, no de este slice.
