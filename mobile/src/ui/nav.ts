// Barra inferior por rol (mockups "Cafetería Aroma móvil"): ítems y navegación.
import { router } from "expo-router";

import { NavItem } from "@/ui";

export type RoleNavItem = NavItem & { ruta?: string }; // "salir" no lleva ruta

export const NAV_MESERO: RoleNavItem[] = [
  { key: "mesas", label: "Mesas", icon: "mesas", ruta: "/mesero/mesas" },
  { key: "pedidos", label: "Pedidos", icon: "pedidos", ruta: "/mesero/mis-pedidos" },
  { key: "salir", label: "Salir", icon: "salir" },
];

export const NAV_COCINA: RoleNavItem[] = [
  { key: "pedidos", label: "Pedidos", icon: "pedidos", ruta: "/cocina" },
  { key: "recetas", label: "Recetas", icon: "recetas", ruta: "/cocina/recetas" },
  { key: "compras", label: "Compras", icon: "compras", ruta: "/cocina/compras" },
  { key: "inventario", label: "Inventario", icon: "inventario", ruta: "/cocina/inventario" },
  { key: "salir", label: "Salir", icon: "salir" },
];

export const NAV_CAJA: RoleNavItem[] = [
  { key: "cobrar", label: "Cobrar", icon: "cobrar", ruta: "/caja" },
  { key: "gastos", label: "Gastos", icon: "gastos", ruta: "/caja/gastos" },
  { key: "salir", label: "Salir", icon: "salir" },
];

/** Maneja el tap en la barra: navega a la ruta del ítem o cierra sesión. */
export async function onNavPress(
  items: RoleNavItem[],
  key: string,
  logout: () => Promise<void>
) {
  if (key === "salir") {
    await logout();
    router.replace("/login" as any);
    return;
  }
  const item = items.find((i) => i.key === key);
  if (item?.ruta) router.replace(item.ruta as any);
}
