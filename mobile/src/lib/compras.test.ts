import { compraTotal, compraValida, lineaCompraValida } from "./compras";

test("lineaCompraValida exige insumo, cantidad > 0 y costo >= 0 no vacío", () => {
  expect(lineaCompraValida(1, "2", "30")).toBe(true);
  expect(lineaCompraValida(1, "2", "0")).toBe(true);
  expect(lineaCompraValida(null, "2", "30")).toBe(false);
  expect(lineaCompraValida(1, "0", "30")).toBe(false);
  expect(lineaCompraValida(1, "2", "")).toBe(false);
});

test("compraTotal suma cantidad × costo", () => {
  expect(
    compraTotal([
      { cantidad: 2, costo_unitario: 30 },
      { cantidad: 1, costo_unitario: 10 },
    ])
  ).toBe(70);
});

test("compraValida exige proveedor y al menos una línea", () => {
  expect(compraValida(1, [{}])).toBe(true);
  expect(compraValida(null, [{}])).toBe(false);
  expect(compraValida(1, [])).toBe(false);
});
