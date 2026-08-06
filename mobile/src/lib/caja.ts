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

/** Redondea a centavos para comparar sumas sin arrastrar el error de precisión de floats. */
const centavos = (n: number): number => Math.round(n * 100);

export function faltante(pagos: PagoLinea[], total: number): number {
  return Math.max(0, centavos(total) - centavos(sumaPagos(pagos))) / 100;
}

export function cambioPagos(pagos: PagoLinea[], total: number): number {
  return Math.max(0, centavos(sumaPagos(pagos)) - centavos(total)) / 100;
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
  if (centavos(sumaPagos(pagos)) < centavos(total)) return false;
  return centavos(montoNoEfectivo(pagos, idEfectivo)) <= centavos(total);
}

export function excedeNoEfectivo(
  pagos: PagoLinea[],
  total: number,
  idEfectivo: number | null
): boolean {
  return centavos(montoNoEfectivo(pagos, idEfectivo)) > centavos(total);
}

export function aPayload(pagos: PagoLinea[]): PagoPayload[] {
  return pagos.map((p) => {
    const referencia = p.referencia?.trim();
    return referencia
      ? { id_metodo_pago: p.id_metodo_pago, monto: p.monto, referencia }
      : { id_metodo_pago: p.id_metodo_pago, monto: p.monto };
  });
}
