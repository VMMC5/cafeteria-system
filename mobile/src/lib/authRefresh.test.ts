import { crearGestorRefresh, debeIntentarRefresh } from "./authRefresh";

test("debeIntentarRefresh: solo 401 de rutas normales sin reintento previo", () => {
  expect(debeIntentarRefresh(401, "/insumos", false)).toBe(true);
  expect(debeIntentarRefresh(401, "/pedidos/3/estado", false)).toBe(true);
});

test("debeIntentarRefresh: excluye auth, reintentos y otros errores", () => {
  expect(debeIntentarRefresh(401, "/auth/login", false)).toBe(false);
  expect(debeIntentarRefresh(401, "/auth/refresh", false)).toBe(false);
  expect(debeIntentarRefresh(401, "/insumos", true)).toBe(false);
  expect(debeIntentarRefresh(403, "/insumos", false)).toBe(false);
  expect(debeIntentarRefresh(500, "/insumos", false)).toBe(false);
  // Error de red: axios no trae response ni a veces config.
  expect(debeIntentarRefresh(undefined, "/insumos", false)).toBe(false);
  expect(debeIntentarRefresh(401, undefined, false)).toBe(false);
});

test("gestor: N llamadas concurrentes comparten un solo refresh", async () => {
  let llamadas = 0;
  let liberar!: (v: string) => void;
  const gestor = crearGestorRefresh(() => {
    llamadas += 1;
    return new Promise<string>((res) => (liberar = res));
  });
  const p1 = gestor.obtener();
  const p2 = gestor.obtener();
  liberar("token-nuevo");
  expect(await p1).toBe("token-nuevo");
  expect(await p2).toBe("token-nuevo");
  expect(llamadas).toBe(1);
});

test("gestor: al resolver se limpia y el siguiente 401 dispara un refresh nuevo", async () => {
  let llamadas = 0;
  const gestor = crearGestorRefresh(async () => {
    llamadas += 1;
    return `t${llamadas}`;
  });
  expect(await gestor.obtener()).toBe("t1");
  expect(await gestor.obtener()).toBe("t2");
  expect(llamadas).toBe(2);
});

test("gestor: el fallo también limpia y no deja promesa colgada", async () => {
  let llamadas = 0;
  const gestor = crearGestorRefresh(async () => {
    llamadas += 1;
    if (llamadas === 1) throw new Error("refresh caducado");
    return "recuperado";
  });
  await expect(gestor.obtener()).rejects.toThrow("refresh caducado");
  expect(await gestor.obtener()).toBe("recuperado");
});

test("gestor: los que esperaban un refresh fallido reciben el mismo fallo", async () => {
  let rechazar!: (e: Error) => void;
  const gestor = crearGestorRefresh(
    () => new Promise<string>((_res, rej) => (rechazar = rej))
  );
  const p1 = gestor.obtener().catch((e: Error) => e.message);
  const p2 = gestor.obtener().catch((e: Error) => e.message);
  rechazar(new Error("expirado"));
  expect(await p1).toBe("expirado");
  expect(await p2).toBe("expirado");
});
