jest.mock("react-native", () => ({
  Alert: { alert: jest.fn() },
  Platform: { OS: "web", select: (obj: Record<string, unknown>) => obj.web ?? obj.default },
}));
jest.mock("expo-router", () => ({ router: { replace: jest.fn() } }));
jest.mock("./client", () => ({
  http: {
    interceptors: { response: { use: jest.fn() } },
    request: jest.fn(),
  },
  refresh: jest.fn(),
}));
jest.mock("../lib/session", () => ({
  saveTokens: jest.fn().mockResolvedValue(undefined),
  clearTokens: jest.fn().mockResolvedValue(undefined),
}));

import { Alert } from "react-native";
import { router } from "expo-router";

import { http, refresh } from "./client";
import { useAuth } from "../store/auth";
import { instalarAuthInterceptor } from "./authInterceptor";

/**
 * Reproduce, fuera de un dispositivo real, la ráfaga de 401 concurrentes que
 * encontró la revisión (p. ej. el Promise.all de mesero/menu.tsx con el
 * token ya caducado): varias peticiones fallan casi al mismo tiempo, todas
 * antes de que la primera termine de poner "noauth" en el store. El refresh
 * single-flight de authRefresh.ts ya evita duplicar la llamada HTTP; este
 * test cubre la otra mitad — que el aviso al usuario (Alert + navegación)
 * tampoco se duplique — y que, tras un login nuevo, la siguiente expiración
 * vuelva a avisar exactamente una vez.
 */
describe("authInterceptor: expulsión ante 401 concurrentes", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.setState({
      status: "auth",
      user: null,
      accessToken: "viejo",
      refreshToken: "rt-caducado",
    });
    (refresh as jest.Mock).mockRejectedValue(new Error("refresh token caducado"));
    instalarAuthInterceptor();
  });

  function errorHandler(): (error: unknown) => Promise<unknown> {
    const use = http.interceptors.response.use as jest.Mock;
    return use.mock.calls[0][1];
  }

  function error401(url: string) {
    return { config: { url, headers: {} }, response: { status: 401 } };
  }

  test("ráfaga concurrente -> un solo Alert; login nuevo rearma para la siguiente expiración", async () => {
    const handler = errorHandler();

    // Ráfaga 1: 3 peticiones con el mismo token caducado, todas casi
    // simultáneas (sin await entre invocaciones, como en un Promise.all).
    const ráfaga1 = await Promise.allSettled([
      handler(error401("/categorias")),
      handler(error401("/productos")),
      handler(error401("/mesas")),
    ]);

    // Cada una sigue propagando su propio error (nada se silencia).
    expect(ráfaga1.every((r) => r.status === "rejected")).toBe(true);
    expect(Alert.alert).toHaveBeenCalledTimes(1);
    expect(router.replace).toHaveBeenCalledTimes(1);
    expect(useAuth.getState().status).toBe("noauth");

    // El usuario vuelve a iniciar sesión: transición real a "auth" que debe
    // rearmar el guardia.
    useAuth.setState({
      status: "auth",
      accessToken: "nuevo",
      refreshToken: "rt-nuevo",
    });

    // Ráfaga 2: la nueva sesión también expira, otra vez con concurrencia.
    const ráfaga2 = await Promise.allSettled([
      handler(error401("/insumos")),
      handler(error401("/pedidos")),
    ]);

    expect(ráfaga2.every((r) => r.status === "rejected")).toBe(true);
    expect(Alert.alert).toHaveBeenCalledTimes(2);
    expect(router.replace).toHaveBeenCalledTimes(2);
    expect(useAuth.getState().status).toBe("noauth");
  });
});
