import {
  aCantidad,
  cantidadValida,
  filtrarProductos,
  insumosDisponibles,
} from "./recetas";

test("cantidadValida exige número > 0 con hasta 3 decimales", () => {
  expect(cantidadValida("2")).toBe(true);
  expect(cantidadValida("0.25")).toBe(true);
  expect(cantidadValida("0,25")).toBe(true);
  expect(cantidadValida("0.125")).toBe(true);
  expect(cantidadValida("0.1255")).toBe(false);
  expect(cantidadValida("0")).toBe(false);
  expect(cantidadValida("-1")).toBe(false);
  expect(cantidadValida("")).toBe(false);
  expect(cantidadValida("abc")).toBe(false);
});

test("aCantidad normaliza la coma decimal a punto", () => {
  expect(aCantidad("0,25")).toBe(0.25);
  expect(aCantidad("0.25")).toBe(0.25);
  expect(aCantidad("3")).toBe(3);
});

test("filtrarProductos ignora mayúsculas y acentos", () => {
  const prods = [
    { nombre_producto: "Café Americano" },
    { nombre_producto: "Té verde" },
    { nombre_producto: "Jugo" },
  ];
  expect(filtrarProductos(prods, "cafe")).toHaveLength(1);
  expect(filtrarProductos(prods, "CAFÉ")).toHaveLength(1);
  expect(filtrarProductos(prods, "te")).toHaveLength(1);
  expect(filtrarProductos(prods, "")).toHaveLength(3);
  expect(filtrarProductos(prods, "   ")).toHaveLength(3);
  expect(filtrarProductos(prods, "zzz")).toHaveLength(0);
});

test("insumosDisponibles excluye los insumos ya presentes en la receta", () => {
  const insumos = [{ id_insumo: 1 }, { id_insumo: 2 }, { id_insumo: 3 }];
  const receta = [{ id_insumo: 2 }];
  expect(insumosDisponibles(insumos, receta).map((i) => i.id_insumo)).toEqual([1, 3]);
  expect(insumosDisponibles(insumos, [])).toHaveLength(3);
  expect(insumosDisponibles([], receta)).toHaveLength(0);
});
