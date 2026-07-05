import * as client from "./client";

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
