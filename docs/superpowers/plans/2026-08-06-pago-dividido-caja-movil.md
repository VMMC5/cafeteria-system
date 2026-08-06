# Pago Dividido en Caja Móvil — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir cobrar un pedido con varios métodos de pago desde la Caja móvil (lista dinámica de pagos), usando el soporte de N pagos que la API ya tiene.

**Architecture:** Lógica pura nueva en `mobile/src/lib/caja.ts` (sustituye `cambio`/`puedeCobrar`), testeada con jest; `cobro.tsx` mantiene el estado de las líneas y pinta; el payload sale de `aPayload()` hacia el `cobrarVenta` existente. Sin cambios en la API.

**Tech Stack:** React Native + Expo (expo-router), TypeScript, jest (`jest-expo`), axios.

**Spec:** `docs/superpowers/specs/2026-08-06-pago-dividido-caja-movil-design.md`

## Global Constraints

- **Solo `mobile/`** — prohibido tocar `backend/` y `web/`.
- **Regla de excedente:** la suma puede exceder el total solo si el excedente viene de Efectivo; líneas no-Efectivo deben sumar ≤ total. Con `idEfectivo === null` (catálogo sin "Efectivo") se exige suma exacta.
- **Referencia:** visible/capturable solo en líneas cuyo método ≠ Efectivo; se manda con `trim()`; si queda vacía se **omite** del payload.
- **Importes:** los valores de la API llegan coaccionados por `coerceDecimals` y se muestran con `money()` de `src/lib/format.ts`; prohibido `.toFixed` directo sobre valores de la API.
- **Tests:** `cd mobile && npm test` (jest). Typecheck: `cd mobile && npx tsc --noEmit`. En un **worktree** correr antes `cd mobile && npm ci` (el worktree no trae `node_modules`).
- **UI en español**, estilos consistentes con la pantalla actual (misma paleta `#2b6cb0`, chips, cards).
- Commits atómicos por tarea: `feat(mobile): …` / `docs: …`.
- Trabajar en rama `feat/mobile-pago-dividido` (worktree/rama los crea la skill de ejecución).

---

### Task 1: Lógica pura de pagos en `lib/caja.ts` + tipo del client

**Files:**
- Modify: `mobile/src/lib/caja.ts` (reemplazo completo)
- Modify: `mobile/src/api/client.ts:253` (tipo del parámetro `pagos` de `cobrarVenta`)
- Test: `mobile/src/lib/caja.test.ts` (reemplazo completo)

**Interfaces:**
- Consumes: nada de tareas previas.
- Produces (Task 2 consume exactamente estas firmas):
  - `type PagoLinea = { id_metodo_pago: number; monto: number; referencia?: string }`
  - `sumaPagos(pagos: PagoLinea[]): number`
  - `faltante(pagos: PagoLinea[], total: number): number`
  - `cambioPagos(pagos: PagoLinea[], total: number): number`
  - `puedeCobrarPagos(pagos: PagoLinea[], total: number, idEfectivo: number | null): boolean`
  - `excedeNoEfectivo(pagos: PagoLinea[], total: number, idEfectivo: number | null): boolean`
  - `aPayload(pagos: PagoLinea[]): { id_metodo_pago: number; monto: number; referencia?: string }[]`
  - `cobrarVenta` acepta `pagos: { id_metodo_pago: number; monto: number; referencia?: string }[]`

Las funciones `cambio` y `puedeCobrar` actuales se **eliminan** (su único consumidor era `cobro.tsx`, que Task 2 migra; entre Task 1 y Task 2 `cobro.tsx` sigue compilando porque Task 1 y 2 se integran en la misma rama — ver nota en Step 4).

- [ ] **Step 1: Reescribir el test (falla primero)** — reemplazar `mobile/src/lib/caja.test.ts` completo con:

```ts
import {
  aPayload,
  cambioPagos,
  excedeNoEfectivo,
  faltante,
  PagoLinea,
  puedeCobrarPagos,
  sumaPagos,
} from "./caja";

const EFECTIVO = 1;
const TARJETA = 2;

const linea = (
  id_metodo_pago: number,
  monto: number,
  referencia?: string
): PagoLinea => ({ id_metodo_pago, monto, referencia });

test("sumaPagos suma 0, 1 y N líneas", () => {
  expect(sumaPagos([])).toBe(0);
  expect(sumaPagos([linea(EFECTIVO, 100)])).toBe(100);
  expect(sumaPagos([linea(EFECTIVO, 100), linea(TARJETA, 25)])).toBe(125);
});

test("faltante = total - suma, nunca negativo", () => {
  expect(faltante([linea(EFECTIVO, 100)], 125)).toBe(25);
  expect(faltante([linea(EFECTIVO, 200)], 125)).toBe(0);
});

test("cambioPagos = suma - total, nunca negativo", () => {
  expect(cambioPagos([linea(EFECTIVO, 200)], 116)).toBe(84);
  expect(cambioPagos([linea(EFECTIVO, 100)], 116)).toBe(0);
});

test("excedente cubierto por Efectivo permite cobrar", () => {
  expect(
    puedeCobrarPagos([linea(TARJETA, 100), linea(EFECTIVO, 50)], 125, EFECTIVO)
  ).toBe(true);
});

test("excedente sin línea de Efectivo no permite cobrar", () => {
  expect(puedeCobrarPagos([linea(TARJETA, 150)], 125, EFECTIVO)).toBe(false);
});

test("líneas no-Efectivo sumando más que el total no permiten cobrar", () => {
  expect(
    puedeCobrarPagos([linea(TARJETA, 130), linea(EFECTIVO, 10)], 125, EFECTIVO)
  ).toBe(false);
});

test("suma exacta sin Efectivo permite cobrar", () => {
  expect(puedeCobrarPagos([linea(TARJETA, 125)], 125, EFECTIVO)).toBe(true);
});

test("sin método Efectivo en el catálogo se exige suma exacta", () => {
  expect(puedeCobrarPagos([linea(TARJETA, 125)], 125, null)).toBe(true);
  expect(puedeCobrarPagos([linea(TARJETA, 130)], 125, null)).toBe(false);
});

test("pago insuficiente, línea en cero, lista vacía o total 0 no permiten cobrar", () => {
  expect(puedeCobrarPagos([linea(EFECTIVO, 100)], 125, EFECTIVO)).toBe(false);
  expect(
    puedeCobrarPagos([linea(EFECTIVO, 125), linea(TARJETA, 0)], 125, EFECTIVO)
  ).toBe(false);
  expect(puedeCobrarPagos([], 125, EFECTIVO)).toBe(false);
  expect(puedeCobrarPagos([linea(EFECTIVO, 10)], 0, EFECTIVO)).toBe(false);
});

test("excedeNoEfectivo detecta la regla violada (para el aviso de UI)", () => {
  expect(excedeNoEfectivo([linea(TARJETA, 130)], 125, EFECTIVO)).toBe(true);
  expect(
    excedeNoEfectivo([linea(TARJETA, 100), linea(EFECTIVO, 50)], 125, EFECTIVO)
  ).toBe(false);
});

test("aPayload recorta la referencia y la omite si queda vacía", () => {
  expect(
    aPayload([linea(TARJETA, 25, "  V-123  "), linea(EFECTIVO, 100, "   ")])
  ).toEqual([
    { id_metodo_pago: TARJETA, monto: 25, referencia: "V-123" },
    { id_metodo_pago: EFECTIVO, monto: 100 },
  ]);
});
```

- [ ] **Step 2: Verificar que falla**

Run: `cd mobile && npm test -- caja`
Expected: FAIL — `caja.ts` no exporta las funciones nuevas (error de compilación del test).

- [ ] **Step 3: Implementar** — reemplazar `mobile/src/lib/caja.ts` completo con:

```ts
export type PagoLinea = {
  id_metodo_pago: number;
  monto: number;
  referencia?: string;
};

export type PagoPayload = {
  id_metodo_pago: number;
  monto: number;
  referencia?: string;
};

export function sumaPagos(pagos: PagoLinea[]): number {
  return pagos.reduce((acc, p) => acc + p.monto, 0);
}

export function faltante(pagos: PagoLinea[], total: number): number {
  return Math.max(0, total - sumaPagos(pagos));
}

export function cambioPagos(pagos: PagoLinea[], total: number): number {
  return Math.max(0, sumaPagos(pagos) - total);
}

function montoNoEfectivo(pagos: PagoLinea[], idEfectivo: number | null): number {
  return pagos
    .filter((p) => p.id_metodo_pago !== idEfectivo)
    .reduce((acc, p) => acc + p.monto, 0);
}

/** El excedente solo puede venir de Efectivo: con idEfectivo null degrada a suma exacta. */
export function puedeCobrarPagos(
  pagos: PagoLinea[],
  total: number,
  idEfectivo: number | null
): boolean {
  if (total <= 0 || pagos.length === 0) return false;
  if (pagos.some((p) => p.monto <= 0)) return false;
  if (sumaPagos(pagos) < total) return false;
  return montoNoEfectivo(pagos, idEfectivo) <= total;
}

export function excedeNoEfectivo(
  pagos: PagoLinea[],
  total: number,
  idEfectivo: number | null
): boolean {
  return montoNoEfectivo(pagos, idEfectivo) > total;
}

export function aPayload(pagos: PagoLinea[]): PagoPayload[] {
  return pagos.map((p) => {
    const referencia = p.referencia?.trim();
    return referencia
      ? { id_metodo_pago: p.id_metodo_pago, monto: p.monto, referencia }
      : { id_metodo_pago: p.id_metodo_pago, monto: p.monto };
  });
}
```

- [ ] **Step 4: Ampliar el tipo del client** — en `mobile/src/api/client.ts`, cambiar la firma de `cobrarVenta`:

```ts
export async function cobrarVenta(
  access: string,
  id_pedido: number,
  pagos: { id_metodo_pago: number; monto: number; referencia?: string }[]
): Promise<Venta> {
  const { data } = await http.post("/ventas", { id_pedido, pagos }, authCfg(access));
  return data;
}
```

**Nota:** tras este step, `cobro.tsx` aún importa `cambio`/`puedeCobrar` que ya no existen — `npx tsc --noEmit` fallará hasta Task 2. Es esperado dentro de la rama; por eso el typecheck completo se corre al final de Task 2, no aquí.

- [ ] **Step 5: Verificar que los tests de lib pasan**

Run: `cd mobile && npm test -- caja`
Expected: PASS los 11.

- [ ] **Step 6: Commit**

```bash
git add mobile/src/lib/caja.ts mobile/src/lib/caja.test.ts mobile/src/api/client.ts
git commit -m "feat(mobile): lógica de pagos divididos en lib/caja (regla de excedente solo Efectivo)"
```

---

### Task 2: Pantalla de cobro con lista dinámica de pagos

**Files:**
- Modify: `mobile/src/app/caja/cobro.tsx` (reemplazo completo)

**Interfaces:**
- Consumes de Task 1: `PagoLinea`, `sumaPagos`, `faltante`, `cambioPagos`, `puedeCobrarPagos`, `excedeNoEfectivo`, `aPayload` desde `@/lib/caja`; `cobrarVenta` con `referencia?` desde `@/api/client`.
- Produces: pantalla final; nadie más la consume.

Esta pantalla no tiene tests de render (convención del proyecto: solo lógica en `lib/` se testea); la verificación es `tsc` + suite completa + revisión visual en Task 3.

- [ ] **Step 1: Reemplazar `mobile/src/app/caja/cobro.tsx` completo con:**

```tsx
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import {
  cobrarVenta,
  getMetodosPago,
  getPedido,
  MetodoPago,
  Pedido,
  Venta,
} from "@/api/client";
import {
  aPayload,
  cambioPagos,
  excedeNoEfectivo,
  faltante,
  PagoLinea,
  puedeCobrarPagos,
  sumaPagos,
} from "@/lib/caja";
import { money } from "@/lib/format";
import { useAuth } from "@/store/auth";

type LineaUI = {
  id_metodo_pago: number | null;
  montoTxt: string;
  referencia: string;
};

function Row({
  label,
  value,
  bold,
}: {
  label: string;
  value: number | string;
  bold?: boolean;
}) {
  return (
    <View style={styles.row}>
      <Text style={[styles.rowL, bold && styles.bold]}>{label}</Text>
      <Text style={[styles.rowV, bold && styles.bold]}>{money(value)}</Text>
    </View>
  );
}

export default function Cobro() {
  const access = useAuth((s) => s.accessToken);
  const { id_pedido } = useLocalSearchParams<{ id_pedido: string }>();
  const pid = Number(id_pedido);
  const [pedido, setPedido] = useState<Pedido | null>(null);
  const [metodos, setMetodos] = useState<MetodoPago[]>([]);
  const [lineas, setLineas] = useState<LineaUI[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cobrando, setCobrando] = useState(false);
  const [venta, setVenta] = useState<Venta | null>(null);

  useEffect(() => {
    if (!access) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [p, ms] = await Promise.all([
          getPedido(access, pid),
          getMetodosPago(access),
        ]);
        setPedido(p);
        setMetodos(ms);
        setLineas([
          {
            id_metodo_pago: ms[0]?.id_metodo_pago ?? null,
            montoTxt: "",
            referencia: "",
          },
        ]);
      } catch {
        setError("No se pudo cargar el cobro.");
      } finally {
        setLoading(false);
      }
    })();
  }, [access, pid]);

  const total = Number(pedido?.total ?? 0);
  const idEfectivo =
    metodos.find((m) => m.nombre_metodo === "Efectivo")?.id_metodo_pago ?? null;

  const parseadas: PagoLinea[] = lineas
    .filter((l) => l.id_metodo_pago !== null)
    .map((l) => ({
      id_metodo_pago: l.id_metodo_pago as number,
      monto: Number(l.montoTxt) || 0,
      referencia: l.referencia,
    }));
  const completas = parseadas.length === lineas.length;
  const habilitado = completas && puedeCobrarPagos(parseadas, total, idEfectivo);
  const avisoExcedente =
    completas && excedeNoEfectivo(parseadas, total, idEfectivo);

  function setLinea(i: number, patch: Partial<LineaUI>) {
    setLineas((ls) => ls.map((l, j) => (j === i ? { ...l, ...patch } : l)));
  }

  function agregarLinea() {
    setLineas((ls) => [
      ...ls,
      {
        id_metodo_pago: metodos[0]?.id_metodo_pago ?? null,
        montoTxt: "",
        referencia: "",
      },
    ]);
  }

  function quitarLinea(i: number) {
    setLineas((ls) => ls.filter((_, j) => j !== i));
  }

  async function confirmar() {
    if (!access || !habilitado) return;
    setCobrando(true);
    try {
      const v = await cobrarVenta(access, pid, aPayload(parseadas));
      setVenta(v);
    } catch (e: any) {
      const msg =
        e?.response?.status === 409
          ? "El pedido ya no está disponible para cobro."
          : "No se pudo cobrar.";
      Alert.alert("Error", msg, [
        { text: "OK", onPress: () => router.replace("/caja" as any) },
      ]);
    } finally {
      setCobrando(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2b6cb0" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorTxt}>{error}</Text>
        <TouchableOpacity onPress={() => router.replace("/caja" as any)}>
          <Text style={styles.link}>Volver</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (venta) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Comprobante</Text>
        <View style={styles.ticket}>
          <Text style={styles.folio}>Folio {venta.folio}</Text>
          <Row label="Subtotal" value={venta.subtotal} />
          <Row label="IVA" value={venta.iva} />
          <Row label="Total" value={venta.total} bold />
          <View style={styles.sep} />
          {venta.pagos.map((pg) => (
            <Row
              key={pg.id_pago}
              label={
                pg.metodo.nombre_metodo +
                (pg.referencia ? ` (${pg.referencia})` : "")
              }
              value={pg.monto}
            />
          ))}
          <Row label="Cambio" value={venta.cambio} bold />
        </View>
        <TouchableOpacity
          style={styles.btn}
          onPress={() => router.replace("/caja" as any)}
        >
          <Text style={styles.btnTxt}>Terminar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Cobro — Mesa {pedido?.mesa.numero_mesa}</Text>
      <ScrollView>
        {pedido?.detalle.map((d, i) => (
          <Text key={i} style={styles.linea}>
            {d.cantidad} × {d.producto.nombre_producto}
          </Text>
        ))}
        <Text style={styles.total}>Total: {money(total)}</Text>

        {lineas.map((l, i) => (
          <View key={i} style={styles.lineaPago}>
            <View style={styles.lineaHead}>
              <Text style={styles.label}>Pago {i + 1}</Text>
              {lineas.length > 1 && (
                <TouchableOpacity
                  onPress={() => quitarLinea(i)}
                  accessibilityLabel={`Quitar pago ${i + 1}`}
                >
                  <Text style={styles.quitar}>✕</Text>
                </TouchableOpacity>
              )}
            </View>
            <View style={styles.chips}>
              {metodos.map((m) => {
                const sel = l.id_metodo_pago === m.id_metodo_pago;
                return (
                  <TouchableOpacity
                    key={m.id_metodo_pago}
                    style={[styles.chip, sel && styles.chipSel]}
                    onPress={() => setLinea(i, { id_metodo_pago: m.id_metodo_pago })}
                  >
                    <Text style={[styles.chipTxt, sel && styles.chipTxtSel]}>
                      {m.nombre_metodo}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
            <TextInput
              style={styles.input}
              keyboardType="numeric"
              value={l.montoTxt}
              onChangeText={(t) => setLinea(i, { montoTxt: t })}
              placeholder="0.00"
            />
            {l.id_metodo_pago !== idEfectivo && (
              <TextInput
                style={styles.input}
                value={l.referencia}
                onChangeText={(t) => setLinea(i, { referencia: t })}
                placeholder="Referencia (opcional)"
              />
            )}
          </View>
        ))}

        <TouchableOpacity onPress={agregarLinea}>
          <Text style={styles.agregar}>+ Agregar pago</Text>
        </TouchableOpacity>

        <View style={styles.resumen}>
          <Row label="Total" value={total} bold />
          <Row label="Pagado" value={sumaPagos(parseadas)} />
          <Row label="Falta" value={faltante(parseadas, total)} />
          <Row label="Cambio" value={cambioPagos(parseadas, total)} bold />
        </View>
        {avisoExcedente && (
          <Text style={styles.aviso}>El excedente solo se permite en Efectivo</Text>
        )}
      </ScrollView>
      <TouchableOpacity
        style={[styles.btn, (!habilitado || cobrando) && styles.btnDisabled]}
        disabled={!habilitado || cobrando}
        onPress={confirmar}
      >
        {cobrando ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.btnTxt}>Confirmar cobro</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f4f5f7", padding: 16 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12 },
  title: {
    fontSize: 20,
    fontWeight: "700",
    color: "#2d3748",
    marginTop: 24,
    marginBottom: 12,
  },
  linea: { color: "#2d3748", paddingVertical: 2 },
  total: {
    fontSize: 18,
    fontWeight: "700",
    color: "#2d3748",
    textAlign: "right",
    marginVertical: 12,
  },
  label: { fontWeight: "600", color: "#4a5568" },
  lineaPago: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 12,
    marginBottom: 10,
    gap: 8,
  },
  lineaHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  quitar: { color: "#c53030", fontSize: 16, fontWeight: "700", padding: 4 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  chipSel: { backgroundColor: "#2b6cb0", borderColor: "#2b6cb0" },
  chipTxt: { color: "#2d3748" },
  chipTxtSel: { color: "#fff", fontWeight: "700" },
  input: {
    backgroundColor: "#f7fafc",
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
  },
  agregar: {
    color: "#2b6cb0",
    fontWeight: "700",
    paddingVertical: 8,
    marginBottom: 4,
  },
  resumen: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 12,
    gap: 6,
    marginBottom: 8,
  },
  aviso: { color: "#c05621", marginBottom: 8, textAlign: "right" },
  ticket: { backgroundColor: "#fff", borderRadius: 12, padding: 16, gap: 6 },
  folio: { fontWeight: "700", color: "#2d3748", marginBottom: 6 },
  row: { flexDirection: "row", justifyContent: "space-between" },
  rowL: { color: "#4a5568" },
  rowV: { color: "#2d3748" },
  bold: { fontWeight: "700" },
  sep: { height: 1, backgroundColor: "#e2e8f0", marginVertical: 6 },
  btn: {
    backgroundColor: "#2b6cb0",
    padding: 16,
    borderRadius: 8,
    alignItems: "center",
  },
  btnDisabled: { backgroundColor: "#a0aec0" },
  btnTxt: { color: "#fff", fontWeight: "700", fontSize: 16 },
  errorTxt: { color: "#c53030", textAlign: "center" },
  link: { color: "#2b6cb0", fontWeight: "600" },
});
```

- [ ] **Step 2: Typecheck limpio (aquí se sana el fallo esperado de Task 1)**

Run: `cd mobile && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 3: Suite completa**

Run: `cd mobile && npm test`
Expected: 67 passed (58 previos − 2 reescritos + 11 de Task 1; ninguna otra suite afectada).

- [ ] **Step 4: Commit**

```bash
git add mobile/src/app/caja/cobro.tsx
git commit -m "feat(mobile): cobro con lista dinámica de pagos divididos en Caja"
```

---

### Task 3: Verificación integral y documentación

**Files:**
- Modify: `progress.md`

**Interfaces:**
- Consumes: Tasks 1–2 commiteadas en la rama.
- Produces: suite + typecheck verdes verificados, `progress.md` al día.

- [ ] **Step 1: Verificación completa**

Run: `cd mobile && npm test && npx tsc --noEmit`
Expected: 67 passed, tsc sin errores.

- [ ] **Step 2: Smoke de payload contra la API real (sin dispositivo)** — verificar que el payload que arma `aPayload` es aceptado por la API con 2 pagos y referencia:

```bash
cd /home/vikca/cafeteria-system && docker compose up -d db api
# login como cajero, crear pedido de prueba vía API (mesa Disponible + producto del seed),
# cobrarlo con dos pagos: efectivo excedente + tarjeta con referencia, p. ej.:
# POST /api/v1/ventas {"id_pedido": <id>, "pagos": [
#   {"id_metodo_pago": <efectivo>, "monto": 100},
#   {"id_metodo_pago": <tarjeta>, "monto": 25.5, "referencia": "V-123"}]}
# → 201 con pagos[1].referencia == "V-123" y cambio == suma − total
```

Registrar en el reporte los comandos curl reales y el JSON de respuesta. Si el seed no tiene datos: `docker compose exec api python -m app.db.seed`.

- [ ] **Step 3: Actualizar `progress.md`**

- Añadir bajo la sección Post-Sprint 6 una entrada "Pago dividido en la Caja móvil": lista dinámica de pagos, regla de excedente solo-Efectivo (cliente), referencia opcional en no-Efectivo, lógica pura en `lib/caja.ts`, 67 tests móviles.
- Quitar de *Deuda técnica* la línea "**Pago dividido** en la Caja móvil: la API lo soporta, pero la UI cobra con un solo método." y la de "falta test de pago dividido en el cobro" (queda cubierto del lado móvil; el de API sigue sin test propio — mantener esa mitad si se considera vigente, reformulando a "falta test de API para venta con pagos múltiples").
- Actualizar el conteo de tests móviles (58 → 67) y la línea "Última actualización".
- Actualizar "Próximo" (siguiente candidato: pantalla de recetas o hardening CSRF/guard API).

- [ ] **Step 4: Commit**

```bash
git add progress.md
git commit -m "docs: progress.md — pago dividido en Caja móvil"
```

---

## Self-review del plan (hecho al escribirlo)

- **Cobertura del spec:** lista dinámica + resumen (T2), regla de Efectivo y fallback (T1 `puedeCobrarPagos`), referencia solo no-Efectivo con trim/omisión (T1 `aPayload` + T2 render condicional), aviso de excedente (T1 `excedeNoEfectivo` + T2), tipo del client (T1), comprobante con referencia (T2), 409 intacto (T2), tests ~11 + tsc (T1–T3), fuera-de-alcance respetado.
- **Sin placeholders:** todo el código y comandos incluidos; el único paso descriptivo (smoke de API en T3) lista el payload exacto esperado.
- **Consistencia de tipos:** firmas de `@/lib/caja` idénticas entre T1 (Produces) y T2 (imports); `LineaUI` (UI, montoTxt string) vs `PagoLinea` (lógica, monto number) claramente separados; conteo 58−2+11=67 consistente en T2/T3.
- **Nota honesta:** entre el commit de T1 y el de T2 el typecheck del repo está roto (cobro.tsx importa funciones eliminadas). Decisión consciente para mantener commits atómicos por capa; ambos commits van en la misma rama y el gate de tsc corre en T2/T3.
