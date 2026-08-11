export function entregable(nombreEstado: string): boolean {
  return nombreEstado === "Listo";
}

// Una mesa Ocupada acepta otra ronda; Reservada y Fuera de servicio no.
export function mesaSeleccionable(estado: string): boolean {
  return estado === "Disponible" || estado === "Ocupada";
}

export function prioridadEstado(nombreEstado: string): number {
  const orden: Record<string, number> = {
    Listo: 0,
    "En preparación": 1,
    Pendiente: 2,
  };
  return orden[nombreEstado] ?? 3;
}
