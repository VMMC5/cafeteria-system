export function entregable(nombreEstado: string): boolean {
  return nombreEstado === "Listo";
}

export function prioridadEstado(nombreEstado: string): number {
  const orden: Record<string, number> = {
    Listo: 0,
    "En preparación": 1,
    Pendiente: 2,
  };
  return orden[nombreEstado] ?? 3;
}
