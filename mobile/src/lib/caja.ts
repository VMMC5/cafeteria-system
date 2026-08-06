export type PagoLinea = {
  id_metodo_pago: number;
  monto: number;
  referencia?: string;
};

export type PagoPayload = {
  id_metodo_pago: number;
  monto: number;
  referencia?: string;
};

export function sumaPagos(pagos: PagoLinea[]): number {
  return pagos.reduce((acc, p) => acc + p.monto, 0);
}

export function faltante(pagos: PagoLinea[], total: number): number {
  return Math.max(0, total - sumaPagos(pagos));
}

export function cambioPagos(pagos: PagoLinea[], total: number): number {
  return Math.max(0, sumaPagos(pagos) - total);
}

function montoNoEfectivo(pagos: PagoLinea[], idEfectivo: number | null): number {
  return pagos
    .filter((p) => p.id_metodo_pago !== idEfectivo)
    .reduce((acc, p) => acc + p.monto, 0);
}

/** El excedente solo puede venir de Efectivo: con idEfectivo null degrada a suma exacta. */
export function puedeCobrarPagos(
  pagos: PagoLinea[],
  total: number,
  idEfectivo: number | null
): boolean {
  if (total <= 0 || pagos.length === 0) return false;
  if (pagos.some((p) => p.monto <= 0)) return false;
  if (sumaPagos(pagos) < total) return false;
  return montoNoEfectivo(pagos, idEfectivo) <= total;
}

export function excedeNoEfectivo(
  pagos: PagoLinea[],
  total: number,
  idEfectivo: number | null
): boolean {
  return montoNoEfectivo(pagos, idEfectivo) > total;
}

export function aPayload(pagos: PagoLinea[]): PagoPayload[] {
  return pagos.map((p) => {
    const referencia = p.referencia?.trim();
    return referencia
      ? { id_metodo_pago: p.id_metodo_pago, monto: p.monto, referencia }
      : { id_metodo_pago: p.id_metodo_pago, monto: p.monto };
  });
}
