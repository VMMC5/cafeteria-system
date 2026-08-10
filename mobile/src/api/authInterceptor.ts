import { Alert } from "react-native";
import { router } from "expo-router";
import type { AxiosError, InternalAxiosRequestConfig } from "axios";

import { http, refresh, type Tokens } from "./client";
import { crearGestorRefresh, debeIntentarRefresh } from "../lib/authRefresh";
import { clearTokens, saveTokens } from "../lib/session";
import { useAuth } from "../store/auth";

/**
 * Refresh-on-401 global. Complementa (no reemplaza) el refresh del
 * bootstrap(): este cubre la expiración a media sesión, aquel el arranque en
 * frío. Las pantallas siguen pasando `access` como argumento; tras un refresh
 * el store ya tiene el token nuevo y el siguiente render lo toma — si una
 * pantalla alcanza a usar el viejo, este interceptor la vuelve a salvar.
 */

const gestor = crearGestorRefresh<Tokens>(() => {
  const rt = useAuth.getState().refreshToken;
  if (!rt) return Promise.reject(new Error("sin refresh token"));
  return refresh(rt);
});

async function renovarYReintentar(config: InternalAxiosRequestConfig) {
  const nt = await gestor.obtener();
  await saveTokens(nt.access_token, nt.refresh_token);
  useAuth.setState({ accessToken: nt.access_token, refreshToken: nt.refresh_token });
  (config as { _retry?: boolean })._retry = true;
  config.headers.Authorization = `Bearer ${nt.access_token}`;
  return http.request(config);
}

// Guardia síncrona anti-ráfaga. Con 401 verdaderamente concurrentes (p. ej.
// Promise.all de dos endpoints con el mismo token ya caducado) varias
// invocaciones de expulsarAlLogin arrancan en el mismo tick, todas antes de
// que la primera alcance a poner "noauth" en el store — leer `status` ahí no
// sirve de guardia porque todas lo ven en "auth" todavía. `expulsando` sí
// funciona: se marca en la primera línea de la función, antes de cualquier
// `await`, y una función async corre sin interrupciones hasta su primer
// `await` (no hay forma de que otra invocación se cuele en medio). Así la
// primera invocación de la ráfaga gana la bandera de forma atómica y todas
// las demás la ven ya en `true` y retornan sin avisar ni navegar.
let expulsando = false;

// Rearme: cuando la sesión vuelve a autenticarse (login nuevo o bootstrap
// exitoso tras la expulsión) se libera la bandera, para que la siguiente
// expiración real vuelva a avisar. No se puede rearmar leyendo `status`
// dentro de expulsarAlLogin (ver guardia arriba): en la misma ráfaga que se
// protege, `status` sigue en "auth" hasta que la primera invocación termina
// su propio await, así que leerlo ahí reabriría la carrera que se corrige.
// Suscribirse al store, en cambio, solo dispara con una transición real de
// estado, desacoplada en el tiempo de cualquier ráfaga de 401.
useAuth.subscribe((state, previo) => {
  if (state.status === "auth" && previo.status !== "auth") {
    expulsando = false;
  }
});

async function expulsarAlLogin() {
  if (expulsando) return;
  // Solo avisa si de verdad había sesión: una llamada rezagada con token
  // viejo tras un logout explícito (no una expiración) no debe alertar.
  const habiaSesion = useAuth.getState().status === "auth";
  if (!habiaSesion) return;
  expulsando = true;
  await clearTokens();
  useAuth.setState({
    status: "noauth",
    user: null,
    accessToken: null,
    refreshToken: null,
  });
  router.replace("/login" as any);
  Alert.alert("Sesión expirada", "Tu sesión expiró, inicia sesión de nuevo.");
}

let instalado = false;

/** Registra el interceptor una sola vez (idempotente ante re-renders/HMR). */
export function instalarAuthInterceptor(): void {
  if (instalado) return;
  instalado = true;
  http.interceptors.response.use(undefined, async (error: AxiosError) => {
    const config = error.config;
    const esReintento = Boolean((config as { _retry?: boolean } | undefined)?._retry);
    if (
      config === undefined ||
      !debeIntentarRefresh(error.response?.status, config.url, esReintento)
    ) {
      throw error;
    }
    try {
      return await renovarYReintentar(config);
    } catch {
      await expulsarAlLogin();
      throw error;
    }
  });
}
