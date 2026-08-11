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

test("coacciona precio_unitario del detalle del pedido (ticket de caja)", () => {
  const pedido = {
    total: "103.00",
    detalle: [{ cantidad: 2, precio_unitario: "44.40", subtotal: "88.80" }],
  };
  const out = coerceDecimals(pedido);
  expect(out.detalle[0].precio_unitario).toBe(44.4);
  expect(out.detalle[0].subtotal).toBe(88.8);
});

test("coacciona cantidad_requerida de las líneas de receta", () => {
  const receta = [
    {
      id_producto_insumo: 1,
      id_insumo: 7,
      insumo: { id_insumo: 7, nombre_insumo: "Leche", unidad: { abreviatura: "L" } },
      cantidad_requerida: "0.250",
    },
  ];
  const out = coerceDecimals(receta) as any[];
  expect(out[0].cantidad_requerida).toBe(0.25);
  expect(typeof out[0].cantidad_requerida).toBe("number");
});
