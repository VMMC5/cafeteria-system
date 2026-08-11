import { entregable, mesaSeleccionable, prioridadEstado } from "./mesero";

test("entregable solo para Listo", () => {
  expect(entregable("Listo")).toBe(true);
  expect(entregable("Pendiente")).toBe(false);
  expect(entregable("En preparación")).toBe(false);
});

test("prioridadEstado ordena Listo primero", () => {
  expect(prioridadEstado("Listo")).toBe(0);
  expect(prioridadEstado("En preparación")).toBe(1);
  expect(prioridadEstado("Pendiente")).toBe(2);
  expect(prioridadEstado("Cancelado")).toBe(3);
});

test("mesaSeleccionable: Disponible y Ocupada sí; Reservada u otros no", () => {
  expect(mesaSeleccionable("Disponible")).toBe(true);
  expect(mesaSeleccionable("Ocupada")).toBe(true); // acepta otra ronda
  expect(mesaSeleccionable("Reservada")).toBe(false);
  expect(mesaSeleccionable("Fuera de servicio")).toBe(false);
});
