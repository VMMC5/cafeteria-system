import { decimalesValidos } from "./decimales";

export { aCantidad } from "./decimales";

/**
 * Cantidad de receta válida: número > 0 con hasta 3 decimales, lo mismo que
 * aceptan el inventario y el kárdex desde la migración a Numeric(10,3).
 */
export function cantidadValida(txt: string): boolean {
  return decimalesValidos(txt, 3);
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
