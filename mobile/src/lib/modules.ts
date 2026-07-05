export type Modulo = {
  key: "mesero" | "caja" | "cocina";
  label: string;
  ruta: string;
};

const MESERO: Modulo = { key: "mesero", label: "Mesero", ruta: "/mesero/mesas" };
const CAJA: Modulo = { key: "caja", label: "Caja", ruta: "/modulo/caja" };
const COCINA: Modulo = { key: "cocina", label: "Cocina", ruta: "/modulo/cocina" };

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
