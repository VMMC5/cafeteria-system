import * as client from "./client";

afterEach(() => {
  jest.restoreAllMocks();
});

test("login postea form urlencoded y devuelve tokens", async () => {
  const spy = jest
    .spyOn(client.http, "post")
    .mockResolvedValue({ data: { access_token: "a", refresh_token: "r" } } as any);
  const out = await client.login("admin@cafeteria.com", "secret123");
  expect(out.access_token).toBe("a");
  const [url, body, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/auth/login");
  expect(String(body)).toContain("username=admin%40cafeteria.com");
  expect(config.headers["Content-Type"]).toBe("application/x-www-form-urlencoded");
});

test("getMe manda el Bearer", async () => {
  const spy = jest
    .spyOn(client.http, "get")
    .mockResolvedValue({ data: { id_usuario: 1 } } as any);
  await client.getMe("tok");
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/auth/me");
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("getMesas manda bearer y pega a /mesas", async () => {
  const spy = jest
    .spyOn(client.http, "get")
    .mockResolvedValue({ data: [{ id_mesa: 1 }] } as any);
  const out = await client.getMesas("tok");
  expect(out).toEqual([{ id_mesa: 1 }]);
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/mesas");
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("crearPedido postea a /pedidos con el payload", async () => {
  const spy = jest
    .spyOn(client.http, "post")
    .mockResolvedValue({ data: { id_pedido: 9 } } as any);
  const payload = {
    id_mesa: 1,
    observaciones: null,
    items: [{ id_producto: 2, cantidad: 1, observaciones: null }],
  };
  const out = await client.crearPedido("tok", payload);
  expect(out).toEqual({ id_pedido: 9 });
  const [url, body, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/pedidos");
  expect(body).toEqual(payload);
  expect(config.headers.Authorization).toBe("Bearer tok");
});
