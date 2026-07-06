export function stockBajo(insumo: {
  stock_actual: number;
  stock_minimo: number;
}): boolean {
  return insumo.stock_actual <= insumo.stock_minimo;
}

export function movimientoValido(
  tipo: string | null,
  motivo: string | null,
  cantidadTxt: string
): boolean {
  return tipo !== null && motivo !== null && Number(cantidadTxt) > 0;
}
