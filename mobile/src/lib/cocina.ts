export function minutosDesde(fechaISO: string, ahora: Date = new Date()): number {
  const ms = ahora.getTime() - new Date(fechaISO).getTime();
  return Math.max(0, Math.floor(ms / 60000));
}

/**
 * Urgencia de un pedido según sus minutos de espera, para colorear el
 * contador en Cocina: "alerta" a los 10 min, "critico" a los 15.
 */
export type NivelRetraso = "ok" | "alerta" | "critico";

export function nivelRetraso(minutos: number): NivelRetraso {
  if (minutos >= 15) return "critico";
  if (minutos >= 10) return "alerta";
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
