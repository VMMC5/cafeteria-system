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

test("montos con centavos no fallan por precisión flotante", () => {
  // 33.3 + 66.6 = 99.89999999999999 en float; debe contar como 99.90 exacto
  expect(
    puedeCobrarPagos([linea(TARJETA, 33.3), linea(EFECTIVO, 66.6)], 99.9, EFECTIVO)
  ).toBe(true);
  // split exacto solo-tarjetas de 116.30: 16.1 + 100.2 "excede" por epsilon
  expect(puedeCobrarPagos([linea(TARJETA, 16.1), linea(TARJETA, 100.2)], 116.3, null)).toBe(true);
  expect(excedeNoEfectivo([linea(TARJETA, 16.1), linea(TARJETA, 100.2)], 116.3, EFECTIVO)).toBe(false);
});

test("faltante y cambioPagos con lista vacía y total 0", () => {
  expect(faltante([], 100)).toBe(100);
  expect(faltante([], 0)).toBe(0);
  expect(cambioPagos([], 0)).toBe(0);
});

test("excedeNoEfectivo con idEfectivo null cuenta todo como no-Efectivo", () => {
  expect(excedeNoEfectivo([linea(EFECTIVO, 130)], 125, null)).toBe(true);
  expect(excedeNoEfectivo([linea(EFECTIVO, 125)], 125, null)).toBe(false);
});

import { agruparPorMesa, cuentaCobrable } from "./caja";
import type { Pedido } from "@/api/client";

const ped = (id: number, mesa: number, total: string, estado = "Entregado") =>
  ({
    id_pedido: id,
    id_mesa: mesa,
    mesa: { numero_mesa: mesa },
    estado: { id_estado: 0, nombre_estado: estado },
    total,
    detalle: [],
  }) as unknown as Pedido;

test("agruparPorMesa: agrupa, suma en centavos y ordena por mesa", () => {
  const cuentas = agruparPorMesa([
    ped(11, 4, "58.00"),
    ped(10, 2, "0.10"),
    ped(12, 4, "116.00"),
    ped(13, 2, "0.20"),
  ]);
  expect(cuentas.map((c) => c.numero_mesa)).toEqual([2, 4]);
  expect(cuentas[0].total).toBe(0.3); // 0.10 + 0.20 exacto, sin residuo de floats
  expect(cuentas[1].total).toBe(174);
  expect(cuentas[1].pedidos.map((p) => p.id_pedido)).toEqual([11, 12]); // rondas por id
});

test("cuentaCobrable: solo con todas las rondas Entregadas", () => {
  expect(cuentaCobrable([ped(1, 1, "10.00"), ped(2, 1, "10.00")])).toBe(true);
  expect(cuentaCobrable([ped(1, 1, "10.00"), ped(2, 1, "10.00", "Pendiente")])).toBe(false);
  expect(cuentaCobrable([])).toBe(false);
});

test("agruparPorMesa: la cuenta con ronda en cocina queda no cobrable", () => {
  const [c] = agruparPorMesa([ped(1, 7, "10.00"), ped(2, 7, "10.00", "Listo")]);
  expect(c.cobrable).toBe(false);
});
