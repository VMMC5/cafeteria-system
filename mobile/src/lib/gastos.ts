export function gastoValido(
  categoriaId: number | null,
  concepto: string,
  montoTxt: string
): boolean {
  return categoriaId !== null && concepto.trim() !== "" && Number(montoTxt) > 0;
}
