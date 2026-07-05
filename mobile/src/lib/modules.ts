export type Modulo = {
  key: "mesero" | "caja" | "cocina";
  label: string;
  ruta: string;
};

const MESERO: Modulo = { key: "mesero", label: "Mesero", ruta: "/mesero/mesas" };
const CAJA: Modulo = { key: "caja", label: "Caja", ruta: "/modulo/caja" };
const COCINA: Modulo = { key: "cocina", label: "Cocina", ruta: "/cocina" };

export function modulesForRole(rol: string): Modulo[] {
  switch (rol) {
    case "Mesero":
      return [MESERO];
    case "Cajero":
      return [CAJA];
    case "Cocinero":
      return [COCINA];
    case "Administrador":
      return [MESERO, CAJA, COCINA];
    default:
      return [];
  }
}

/**
 * Ruta a la que va un usuario tras autenticarse: si su rol tiene un solo
 * módulo, entra directo a su home; si tiene varios, a la selección de módulo.
 */
export function homeRoute(rol: string): string {
  const modulos = modulesForRole(rol);
  return modulos.length === 1 ? modulos[0].ruta : "/seleccion-modulo";
}
