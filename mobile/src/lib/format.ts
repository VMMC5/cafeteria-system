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
