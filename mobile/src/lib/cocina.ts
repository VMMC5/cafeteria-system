export function minutosDesde(fechaISO: string, ahora: Date = new Date()): number {
  const ms = ahora.getTime() - new Date(fechaISO).getTime();
  return Math.max(0, Math.floor(ms / 60000));
}

/**
 * Urgencia de un pedido según sus minutos de espera, para colorear el
 * contador en Cocina. Umbrales acortados (1 y 2 min) para demo en vivo;
 * en operación real subirlos (p. ej. 10 y 15).
 */
export type NivelRetraso = "ok" | "alerta" | "critico";

export const RETRASO_ALERTA_MIN = 1;
export const RETRASO_CRITICO_MIN = 2;

export function nivelRetraso(minutos: number): NivelRetraso {
  if (minutos >= RETRASO_CRITICO_MIN) return "critico";
  if (minutos >= RETRASO_ALERTA_MIN) return "alerta";
  return "ok";
}

export type AccionCocina = { label: string; destinoNombre: string };

export function accionCocina(nombreEstado: string): AccionCocina | null {
  if (nombreEstado === "Pendiente") {
    return { label: "Iniciar preparación", destinoNombre: "En preparación" };
  }
  if (nombreEstado === "En preparación") {
    return { label: "Marcar listo", destinoNombre: "Listo" };
  }
  return null;
}
