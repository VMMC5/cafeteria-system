/**
 * Lógica pura del refresh-on-401 global. El cableado con axios, el store y la
 * navegación vive en api/authInterceptor.ts; aquí solo decisiones, para que
 * jest las cubra sin montar nada.
 */

const RUTAS_AUTH = ["/auth/login", "/auth/refresh"];

/**
 * ¿Este error amerita intentar un refresh? Solo un 401 de una ruta normal y
 * que no sea ya el reintento (un solo reintento por petición). Los 401 de
 * login/refresh son credenciales malas o refresh caducado: reintentarlos
 * ciclaría.
 */
export function debeIntentarRefresh(
  status: number | undefined,
  url: string | undefined,
  esReintento: boolean
): boolean {
  if (status !== 401 || esReintento || url === undefined) return false;
  return !RUTAS_AUTH.some((ruta) => url.includes(ruta));
}

/**
 * Single-flight: mientras haya un refresh en vuelo, todo el que lo pida
 * comparte la misma promesa (N pantallas con 401 simultáneo → 1 refresh).
 * Al resolverse o fallar se limpia, para que el siguiente 401 real dispare
 * un refresh nuevo.
 */
export function crearGestorRefresh<T>(refrescar: () => Promise<T>): {
  obtener: () => Promise<T>;
} {
  let enVuelo: Promise<T> | null = null;
  return {
    obtener() {
      if (enVuelo === null) {
        enVuelo = refrescar().finally(() => {
          enVuelo = null;
        });
      }
      return enVuelo;
    },
  };
}
