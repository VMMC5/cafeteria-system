jest.mock("../api/client");
jest.mock("../lib/session");

import * as client from "../api/client";
import * as session from "../lib/session";
import { useAuth } from "./auth";

beforeEach(() => {
  jest.clearAllMocks();
  useAuth.setState({
    status: "loading",
    user: null,
    accessToken: null,
    refreshToken: null,
  });
});

test("login guarda tokens y pone status auth", async () => {
  (client.login as jest.Mock).mockResolvedValue({ access_token: "a", refresh_token: "r" });
  (client.getMe as jest.Mock).mockResolvedValue({ id_usuario: 1, rol: { nombre_rol: "Mesero" } });
  await useAuth.getState().login("m@cafeteria.com", "secret123");
  expect(session.saveTokens).toHaveBeenCalledWith("a", "r");
  expect(useAuth.getState().status).toBe("auth");
  expect(useAuth.getState().user?.rol.nombre_rol).toBe("Mesero");
});

test("bootstrap sin tokens -> noauth", async () => {
  (session.loadTokens as jest.Mock).mockResolvedValue(null);
  await useAuth.getState().bootstrap();
  expect(useAuth.getState().status).toBe("noauth");
});

test("bootstrap con token valido -> auth", async () => {
  (session.loadTokens as jest.Mock).mockResolvedValue({ access: "a", refresh: "r" });
  (client.getMe as jest.Mock).mockResolvedValue({ id_usuario: 1, rol: { nombre_rol: "Cajero" } });
  await useAuth.getState().bootstrap();
  expect(useAuth.getState().status).toBe("auth");
});

test("logout limpia el estado", async () => {
  useAuth.setState({
    status: "auth",
    user: { id_usuario: 1 } as any,
    accessToken: "a",
    refreshToken: "r",
  });
  await useAuth.getState().logout();
  expect(session.clearTokens).toHaveBeenCalled();
  expect(useAuth.getState().status).toBe("noauth");
  expect(useAuth.getState().user).toBeNull();
});
