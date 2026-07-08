import { coerceDecimals } from "./coerce";

test("convierte campos Decimal (string) a number y no toca otros strings", () => {
  const out = coerceDecimals({ total: "116.50", folio: "V-0001", nombre: "Café" });
  expect(out.total).toBe(116.5);
  expect(out.folio).toBe("V-0001");
  expect(out.nombre).toBe("Café");
});

test("recorre arrays y objetos anidados (venta con pagos y detalle)", () => {
  const venta = {
    total: "232.00",
    subtotal: "200.00",
    iva: "32.00",
    cambio: "0",
    pagos: [{ monto: "200.00" }, { monto: "32.00" }],
    detalle: [{ cantidad: "25.00", subtotal: "10.5", costo_unitario: "3.5" }],
  };
  const out = coerceDecimals(venta);
  expect(out.total).toBe(232);
  expect(out.iva).toBe(32);
  expect(out.pagos[0].monto).toBe(200);
  expect(out.pagos[1].monto).toBe(32);
  expect(out.detalle[0].cantidad).toBe(25);
  expect(out.detalle[0].subtotal).toBe(10.5);
  expect(out.detalle[0].costo_unitario).toBe(3.5);
});

test("deja intactos numbers, null y valores no numéricos", () => {
  const out = coerceDecimals({ total: 50, monto: null, precio_venta: "abc" });
  expect(out.total).toBe(50);
  expect(out.monto).toBeNull();
  expect(out.precio_venta).toBe("abc"); // no corrompe si no es numérico
});
