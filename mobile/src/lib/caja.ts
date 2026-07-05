export function cambio(recibido: number, total: number): number {
  return Math.max(0, recibido - total);
}

export function puedeCobrar(recibido: number, total: number): boolean {
  return total > 0 && recibido >= total;
}
