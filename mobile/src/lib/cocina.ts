export function minutosDesde(fechaISO: string, ahora: Date = new Date()): number {
  const ms = ahora.getTime() - new Date(fechaISO).getTime();
  return Math.max(0, Math.floor(ms / 60000));
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
