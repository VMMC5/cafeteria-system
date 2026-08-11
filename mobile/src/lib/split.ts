/**
 * División de cuenta por artículos ("calculadora de división").
 *
 * La asignación es una matriz `asignacion[linea][persona] = unidades` sobre el
 * detalle del pedido. Los precios del detalle ya incluyen IVA (el total del
 * pedido es la suma de sus líneas y la venta solo lo desglosa), así que el
 * monto de cada persona es exacto: suma de sus unidades × precio_unitario.
 * Todas las operaciones son inmutables: devuelven una matriz nueva.
 */

export type Asignacion = number[][];

/** Lo mínimo que la aritmética necesita de una línea del pedido. */
export type LineaDetalle = { cantidad: number; precio_unitario: number };

export function crearAsignacion(numLineas: number, numPersonas: number): Asignacion {
  return Array.from({ length: numLineas }, () => Array(numPersonas).fill(0));
}

export function unidadesAsignadas(a: Asignacion, linea: number): number {
  return (a[linea] ?? []).reduce((s, u) => s + u, 0);
}

export function unidadesRestantes(
  a: Asignacion,
  linea: number,
  unidadesLinea: number
): number {
  return Math.max(0, unidadesLinea - unidadesAsignadas(a, linea));
}

/**
 * Total de una persona: suma de sus unidades × precio_unitario. Se acumula en
 * centavos para que la suma de todas las personas cuadre exacta con el total
 * del pedido (los precios traen 2 decimales; los floats no asocian parejo).
 */
export function totalPersona(
  a: Asignacion,
  persona: number,
  detalle: LineaDetalle[]
): number {
  const centavos = detalle.reduce(
    (s, d, linea) => s + Math.round(d.precio_unitario * 100) * (a[linea]?.[persona] ?? 0),
    0
  );
  return centavos / 100;
}

/** true cuando cada línea tiene todas sus unidades repartidas. */
export function completa(a: Asignacion, detalle: LineaDetalle[]): boolean {
  return detalle.every((d, linea) => unidadesAsignadas(a, linea) === d.cantidad);
}

/** Índices (ascendentes) de las personas con al menos una unidad asignada. */
export function personasConConsumo(a: Asignacion): number[] {
  const numPersonas = a[0]?.length ?? 0;
  const indices: number[] = [];
  for (let p = 0; p < numPersonas; p++) {
    if (a.some((fila) => (fila[p] ?? 0) > 0)) indices.push(p);
  }
  return indices;
}

/** Añade una persona (columna en 0) a todas las líneas. */
export function agregarPersona(a: Asignacion): Asignacion {
  return a.map((fila) => [...fila, 0]);
}

/**
 * Quita a la persona: su columna desaparece y sus unidades regresan a
 * "sin asignar" (nadie las hereda). Con 2 personas no hace nada — la división
 * mínima es entre dos.
 */
export function quitarPersona(a: Asignacion, persona: number): Asignacion {
  if ((a[0]?.length ?? 0) <= 2) return a;
  return a.map((fila) => fila.filter((_, p) => p !== persona));
}

/**
 * Suma `delta` unidades de la línea a una persona. Nunca deja la celda en
 * negativo y, si el alta rebasa las unidades de la línea (entre todas las
 * personas), devuelve la matriz sin cambios.
 */
export function asignar(
  a: Asignacion,
  linea: number,
  persona: number,
  delta: number,
  unidadesLinea: number
): Asignacion {
  const actual = a[linea]?.[persona] ?? 0;
  const nuevo = Math.max(0, actual + delta);
  const totalLinea = unidadesAsignadas(a, linea) - actual + nuevo;
  if (totalLinea > unidadesLinea) return a;
  return a.map((fila, i) =>
    i === linea ? fila.map((u, p) => (p === persona ? nuevo : u)) : fila
  );
}
