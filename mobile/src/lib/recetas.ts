/** Normaliza la coma decimal a punto: los teclados numéricos varían por locale. */
function normalizar(txt: string): string {
  return txt.trim().replace(",", ".");
}

/** Cantidad de receta válida: número > 0 con hasta 3 decimales (lo que acepta la API). */
export function cantidadValida(txt: string): boolean {
  const t = normalizar(txt);
  if (!/^\d+(\.\d{1,3})?$/.test(t)) return false;
  return Number(t) > 0;
}

export function aCantidad(txt: string): number {
  return Number(normalizar(txt));
}

/** Quita acentos y baja a minúsculas para que la búsqueda sea tolerante. */
function plano(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

export function filtrarProductos<T extends { nombre_producto: string }>(
  productos: T[],
  query: string
): T[] {
  const q = plano(query.trim());
  if (q === "") return productos;
  return productos.filter((p) => plano(p.nombre_producto).includes(q));
}

/**
 * Insumos que aún se pueden agregar a la receta. Excluir los ya presentes evita
 * el 409 de la API (un insumo no puede repetirse en la misma receta).
 */
export function insumosDisponibles<T extends { id_insumo: number }>(
  insumos: T[],
  receta: { id_insumo: number }[]
): T[] {
  const usados = new Set(receta.map((l) => l.id_insumo));
  return insumos.filter((i) => !usados.has(i.id_insumo));
}
