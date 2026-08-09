/**
 * Reglas decimales compartidas por inventario, compras y recetas.
 *
 * La API acepta cantidades con hasta 3 decimales y rechaza el resto con 422
 * (Numeric(10,3) en insumos, kárdex, detalle de compra y recetas). Validar aquí
 * evita que ese 422 le llegue al usuario en forma de error de red.
 */

/** Normaliza la coma decimal a punto: los teclados numéricos varían por locale. */
export function normalizar(txt: string): string {
  return txt.trim().replace(",", ".");
}

/** Número > 0 con hasta `max` decimales, aceptando coma o punto. */
export function decimalesValidos(txt: string, max: number): boolean {
  const t = normalizar(txt);
  const re = new RegExp(`^\\d+(\\.\\d{1,${max}})?$`);
  if (!re.test(t)) return false;
  return Number(t) > 0;
}

export function aCantidad(txt: string): number {
  return Number(normalizar(txt));
}
