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

test("getEstados pega a /estados con bearer", async () => {
  const spy = jest
    .spyOn(client.http, "get")
    .mockResolvedValue({ data: [{ id_estado: 1, nombre_estado: "Pendiente" }] } as any);
  const out = await client.getEstados("tok");
  expect(out).toEqual([{ id_estado: 1, nombre_estado: "Pendiente" }]);
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/estados");
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("getPedidos manda estados como CSV", async () => {
  const spy = jest.spyOn(client.http, "get").mockResolvedValue({ data: [] } as any);
  await client.getPedidos("tok", { estados: [1, 2] });
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/pedidos");
  expect(config.params).toEqual({ estados: "1,2" });
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("cambiarEstadoPedido hace PATCH con id_estado", async () => {
  const spy = jest
    .spyOn(client.http, "patch")
    .mockResolvedValue({ data: { id_pedido: 5 } } as any);
  await client.cambiarEstadoPedido("tok", 5, 3);
  const [url, body, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/pedidos/5/estado");
  expect(body).toEqual({ id_estado: 3 });
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("getPedidos con mias manda mias y estados", async () => {
  const spy = jest.spyOn(client.http, "get").mockResolvedValue({ data: [] } as any);
  await client.getPedidos("tok", { mias: true, estados: [1, 2, 3] });
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/pedidos");
  expect(config.params).toEqual({ estados: "1,2,3", mias: true });
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("getMetodosPago pega a /metodos_pago con bearer", async () => {
  const spy = jest
    .spyOn(client.http, "get")
    .mockResolvedValue({ data: [{ id_metodo_pago: 1, nombre_metodo: "Efectivo" }] } as any);
  const out = await client.getMetodosPago("tok");
  expect(out).toEqual([{ id_metodo_pago: 1, nombre_metodo: "Efectivo" }]);
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/metodos_pago");
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("getPedidos con por_cobrar manda el flag", async () => {
  const spy = jest.spyOn(client.http, "get").mockResolvedValue({ data: [] } as any);
  await client.getPedidos("tok", { por_cobrar: true });
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/pedidos");
  expect(config.params).toEqual({ por_cobrar: true });
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("cobrarVenta postea a /ventas con id_pedido y pagos", async () => {
  const spy = jest
    .spyOn(client.http, "post")
    .mockResolvedValue({ data: { id_venta: 3 } } as any);
  await client.cobrarVenta("tok", 7, [{ id_metodo_pago: 1, monto: 200 }]);
  const [url, body, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/ventas");
  expect(body).toEqual({ id_pedido: 7, pagos: [{ id_metodo_pago: 1, monto: 200 }] });
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("getCategoriasGasto pega a /gastos/categorias con bearer", async () => {
  const spy = jest
    .spyOn(client.http, "get")
    .mockResolvedValue({ data: [{ id_categoria_gasto: 1, nombre_categoria: "Servicios" }] } as any);
  const out = await client.getCategoriasGasto("tok");
  expect(out).toEqual([{ id_categoria_gasto: 1, nombre_categoria: "Servicios" }]);
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/gastos/categorias");
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("getGastos pega a /gastos con bearer", async () => {
  const spy = jest.spyOn(client.http, "get").mockResolvedValue({ data: [] } as any);
  await client.getGastos("tok");
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/gastos");
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("crearGasto postea a /gastos con el cuerpo", async () => {
  const spy = jest
    .spyOn(client.http, "post")
    .mockResolvedValue({ data: { id_gasto: 5 } } as any);
  await client.crearGasto("tok", { id_categoria_gasto: 1, concepto: "Luz", monto: 500 });
  const [url, body, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/gastos");
  expect(body).toEqual({ id_categoria_gasto: 1, concepto: "Luz", monto: 500 });
  expect(config.headers.Authorization).toBe("Bearer tok");
});
