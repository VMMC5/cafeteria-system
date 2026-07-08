/**
 * La API serializa los campos Decimal como **string** en JSON (p. ej. "116.50").
 * Los tipos de `client.ts` los declaran `number`, así que hay que coaccionarlos
 * en el borde del cliente para que esos tipos sean verdaderos en runtime y ningún
 * consumidor reviente al hacer `.toFixed()` o aritmética sobre un string.
 *
 * Este conjunto lista los nombres de campo monetarios/numéricos que la API
 * devuelve como Decimal. Todos son inequívocamente numéricos en este dominio.
 */
export const DECIMAL_FIELDS = new Set<string>([
  "total",
  "subtotal",
  "iva",
  "cambio",
  "monto",
  "cantidad",
  "precio_venta",
  "costo_unitario",
  "stock_actual",
  "stock_minimo",
]);

/**
 * Recorre recursivamente la respuesta (objetos/arrays anidados) y convierte a
 * `number` los campos de {@link DECIMAL_FIELDS} que lleguen como string numérico.
 * Muta el nodo in situ y lo devuelve. No toca numbers, null ni strings no numéricos.
 */
export function coerceDecimals<T>(node: T): T {
  if (Array.isArray(node)) {
    node.forEach(coerceDecimals);
  } else if (node !== null && typeof node === "object") {
    const obj = node as Record<string, unknown>;
    for (const key of Object.keys(obj)) {
      const v = obj[key];
      if (
        DECIMAL_FIELDS.has(key) &&
        typeof v === "string" &&
        v.trim() !== "" &&
        !Number.isNaN(Number(v))
      ) {
        obj[key] = Number(v);
      } else {
        coerceDecimals(v);
      }
    }
  }
  return node;
}
