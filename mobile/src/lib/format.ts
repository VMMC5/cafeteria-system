/**
 * Formatea un importe monetario a "$X.XX".
 *
 * La API serializa los campos Decimal como **string** en JSON (p. ej. "116.50"),
 * así que hay que coaccionar a número antes de `.toFixed`; llamarlo directo sobre
 * el string revienta con "undefined is not a function".
 */
export function money(value: number | string | null | undefined): string {
  return `$${Number(value ?? 0).toFixed(2)}`;
}

/**
 * Formatea una cantidad de inventario: hasta 3 decimales, sin ceros de relleno.
 *
 * La API manda las cantidades como string con la escala completa ("500.000"),
 * y `coerceDecimals` las convierte a number en el borde del cliente. Este
 * helper fija la regla de presentación en un solo sitio: "500", "12.5",
 * "0.125" — nunca "500.000" ni un `.toFixed(2)` que se coma el tercer decimal.
 */
export function cantidad(value: number | string | null | undefined): string {
  return String(Number(Number(value ?? 0).toFixed(3)));
}
