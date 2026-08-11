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

import type { Pedido } from "@/api/client";

export type CuentaMesa = {
  id_mesa: number;
  numero_mesa: number;
  pedidos: Pedido[]; // rondas ordenadas por id_pedido
  total: number; // total en pesos (acumulado internamente en centavos)
  cobrable: boolean; // todas las rondas Entregadas
};

export function cuentaCobrable(pedidos: Pick<Pedido, "estado">[]): boolean {
  return (
    pedidos.length > 0 &&
    pedidos.every((p) => p.estado.nombre_estado === "Entregado")
  );
}

export function agruparPorMesa(pedidos: Pedido[]): CuentaMesa[] {
  const porMesa = new Map<number, Pedido[]>();
  for (const p of pedidos) {
    const lista = porMesa.get(p.id_mesa) ?? [];
    lista.push(p);
    porMesa.set(p.id_mesa, lista);
  }
  return Array.from(porMesa.values())
    .map((lista) => {
      const rondas = [...lista].sort((a, b) => a.id_pedido - b.id_pedido);
      const totalCent = rondas.reduce(
        (s, p) => s + Math.round(Number(p.total) * 100),
        0
      );
      return {
        id_mesa: rondas[0].id_mesa,
        numero_mesa: rondas[0].mesa.numero_mesa,
        pedidos: rondas,
        total: totalCent / 100,
        cobrable: cuentaCobrable(rondas),
      };
    })
    .sort((a, b) => a.numero_mesa - b.numero_mesa);
}
