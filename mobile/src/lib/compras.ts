export function lineaCompraValida(
  idInsumo: number | null,
  cantidadTxt: string,
  costoTxt: string
): boolean {
  return (
    idInsumo !== null &&
    Number(cantidadTxt) > 0 &&
    costoTxt !== "" &&
    Number(costoTxt) >= 0
  );
}

export function compraTotal(
  lineas: { cantidad: number; costo_unitario: number }[]
): number {
  return lineas.reduce((s, l) => s + l.cantidad * l.costo_unitario, 0);
}

export function compraValida(
  idProveedor: number | null,
  lineas: unknown[]
): boolean {
  return idProveedor !== null && lineas.length > 0;
}
