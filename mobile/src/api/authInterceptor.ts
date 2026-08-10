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

async function expulsarAlLogin() {
  // Solo avisa la primera vez: tras poner "noauth", los 401 rezagados de
  // llamadas concurrentes ya no encuentran una sesión que expirar.
  const habiaSesion = useAuth.getState().status === "auth";
  await clearTokens();
  useAuth.setState({
    status: "noauth",
    user: null,
    accessToken: null,
    refreshToken: null,
  });
  if (habiaSesion) {
    router.replace("/login" as any);
    Alert.alert("Sesión expirada", "Tu sesión expiró, inicia sesión de nuevo.");
  }
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
