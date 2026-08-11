import {
  accionCocina,
  minutosDesde,
  nivelRetraso,
  RETRASO_ALERTA_MIN,
  RETRASO_CRITICO_MIN,
} from "./cocina";

test("nivelRetraso escala ok → alerta → critico según los umbrales", () => {
  expect(nivelRetraso(RETRASO_ALERTA_MIN - 1)).toBe("ok");
  expect(nivelRetraso(RETRASO_ALERTA_MIN)).toBe("alerta");
  expect(nivelRetraso(RETRASO_CRITICO_MIN - 1)).toBe("alerta");
  expect(nivelRetraso(RETRASO_CRITICO_MIN)).toBe("critico");
  expect(nivelRetraso(RETRASO_CRITICO_MIN + 25)).toBe("critico");
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
