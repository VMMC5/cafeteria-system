import { aCantidad, decimalesValidos, normalizar } from "./decimales";

test("normalizar convierte la coma decimal en punto y recorta espacios", () => {
  expect(normalizar(" 0,25 ")).toBe("0.25");
  expect(normalizar("0.25")).toBe("0.25");
});

test("decimalesValidos exige número > 0 con hasta N decimales", () => {
  expect(decimalesValidos("2", 3)).toBe(true);
  expect(decimalesValidos("0.125", 3)).toBe(true);
  expect(decimalesValidos("0,125", 3)).toBe(true);
  expect(decimalesValidos("0.1255", 3)).toBe(false);
  expect(decimalesValidos("0.125", 2)).toBe(false);
  expect(decimalesValidos("0", 3)).toBe(false);
  expect(decimalesValidos("-1", 3)).toBe(false);
  expect(decimalesValidos("", 3)).toBe(false);
  expect(decimalesValidos("abc", 3)).toBe(false);
});

test("aCantidad normaliza la coma decimal a punto", () => {
  expect(aCantidad("0,125")).toBe(0.125);
  expect(aCantidad("3")).toBe(3);
});
