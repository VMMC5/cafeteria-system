import { accionCocina, minutosDesde, nivelRetraso } from "./cocina";

test("nivelRetraso escala ok → alerta (10 min) → critico (15 min)", () => {
  expect(nivelRetraso(0)).toBe("ok");
  expect(nivelRetraso(9)).toBe("ok");
  expect(nivelRetraso(10)).toBe("alerta");
  expect(nivelRetraso(14)).toBe("alerta");
  expect(nivelRetraso(15)).toBe("critico");
  expect(nivelRetraso(40)).toBe("critico");
});

test("minutosDesde calcula minutos enteros", () => {
  const ahora = new Date("2026-07-05T12:30:00Z");
  expect(minutosDesde("2026-07-05T12:00:00Z", ahora)).toBe(30);
});

test("minutosDesde nunca es negativo", () => {
  const ahora = new Date("2026-07-05T12:00:00Z");
  expect(minutosDesde("2026-07-05T12:05:00Z", ahora)).toBe(0);
});

test("accionCocina mapea Pendiente y En preparación", () => {
  expect(accionCocina("Pendiente")).toEqual({
    label: "Iniciar preparación",
    destinoNombre: "En preparación",
  });
  expect(accionCocina("En preparación")).toEqual({
    label: "Marcar listo",
    destinoNombre: "Listo",
  });
});

test("accionCocina devuelve null para Listo o desconocido", () => {
  expect(accionCocina("Listo")).toBeNull();
  expect(accionCocina("Cualquiera")).toBeNull();
});
