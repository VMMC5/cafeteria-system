import { homeRoute, modulesForRole } from "./modules";

test("mesero ve solo su modulo", () => {
  const m = modulesForRole("Mesero");
  expect(m.map((x) => x.key)).toEqual(["mesero"]);
});

test("cajero ve caja, cocinero ve cocina", () => {
  expect(modulesForRole("Cajero").map((x) => x.key)).toEqual(["caja"]);
  expect(modulesForRole("Cocinero").map((x) => x.key)).toEqual(["cocina"]);
});

test("administrador ve los tres modulos", () => {
  expect(modulesForRole("Administrador").map((x) => x.key)).toEqual([
    "mesero",
    "caja",
    "cocina",
  ]);
});

test("rol desconocido no ve modulos", () => {
  expect(modulesForRole("Otro")).toEqual([]);
});

test("cada modulo apunta a su ruta", () => {
  expect(modulesForRole("Mesero")[0].ruta).toBe("/mesero/mesas");
  expect(modulesForRole("Cocinero")[0].ruta).toBe("/cocina");
});

test("homeRoute: rol de un solo modulo va directo a su home", () => {
  expect(homeRoute("Mesero")).toBe("/mesero/mesas");
  expect(homeRoute("Cajero")).toBe("/modulo/caja");
});

test("homeRoute: rol con varios modulos va a seleccion", () => {
  expect(homeRoute("Administrador")).toBe("/seleccion-modulo");
});
