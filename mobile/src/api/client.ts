import axios from "axios";

import { coerceDecimals } from "./coerce";

const baseURL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const http = axios.create({ baseURL, timeout: 10000 });

// La API serializa Decimal como string; coacciona esos campos a number en el
// borde para que los tipos `number` de abajo sean verdaderos en runtime.
http.interceptors.response.use((response) => {
  response.data = coerceDecimals(response.data);
  return response;
});

export type Tokens = { access_token: string; refresh_token: string };
export type Rol = { id_rol: number; nombre_rol: string; descripcion: string | null };
export type Usuario = {
  id_usuario: number;
  nombre: string;
  apellido_paterno: string;
  apellido_materno: string | null;
  correo: string;
  nombre_usuario: string;
  id_rol: number;
  rol: Rol;
  activo: boolean;
};

export async function login(correo: string, password: string): Promise<Tokens> {
  const body = new URLSearchParams({ username: correo, password });
  const { data } = await http.post("/auth/login", body.toString(), {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

export async function getMe(access: string): Promise<Usuario> {
  const { data } = await http.get("/auth/me", {
    headers: { Authorization: `Bearer ${access}` },
  });
  return data;
}

export async function refresh(refreshToken: string): Promise<Tokens> {
  const { data } = await http.post("/auth/refresh", {
    refresh_token: refreshToken,
  });
  return data;
}

function authCfg(access: string) {
  return { headers: { Authorization: `Bearer ${access}` } };
}

export type Mesa = {
  id_mesa: number;
  numero_mesa: number;
  capacidad: number;
  ubicacion: string | null;
  estado: string;
};

export type Categoria = {
  id_categoria: number;
  nombre_categoria: string;
  descripcion: string | null;
};

export type Producto = {
  id_producto: number;
  id_categoria: number;
  nombre_producto: string;
  descripcion: string | null;
  precio_venta: number;
  disponible: boolean;
};

export type PedidoItemPayload = {
  id_producto: number;
  cantidad: number;
  observaciones: string | null;
};

export type CrearPedidoPayload = {
  id_mesa: number | null;
  observaciones: string | null;
  items: PedidoItemPayload[];
};

export type Estado = { id_estado: number; nombre_estado: string };

export type PedidoLinea = {
  cantidad: number;
  observaciones: string | null;
  producto: { nombre_producto: string };
};

export type Pedido = {
  id_pedido: number;
  id_mesa: number;
  mesa: { numero_mesa: number };
  estado: { id_estado: number; nombre_estado: string };
  fecha_pedido: string;
  observaciones: string | null;
  detalle: PedidoLinea[];
  total: number;
};

export type MetodoPago = { id_metodo_pago: number; nombre_metodo: string };

export type PagoOut = {
  id_pago: number;
  id_metodo_pago: number;
  metodo: { nombre_metodo: string };
  monto: number;
  referencia: string | null;
};

export type Venta = {
  id_venta: number;
  id_pedido: number;
  folio: string;
  estado_venta: string;
  fecha_venta: string;
  total: number;
  subtotal: number;
  iva: number;
  cambio: number;
  pagos: PagoOut[];
};

export type CategoriaGasto = { id_categoria_gasto: number; nombre_categoria: string };

export type Gasto = {
  id_gasto: number;
  id_categoria_gasto: number;
  categoria: { nombre_categoria: string };
  concepto: string;
  monto: number;
  fecha_gasto: string;
  id_usuario: number;
};

export type Insumo = {
  id_insumo: number;
  nombre_insumo: string;
  id_unidad: number;
  unidad: { nombre_unidad: string; abreviatura: string };
  descripcion: string | null;
  stock_actual: number;
  stock_minimo: number;
  costo_unitario: number;
};

export type Proveedor = { id_proveedor: number; nombre_proveedor: string };

export type DetalleCompra = {
  id_detalle_compra: number;
  id_insumo: number;
  insumo: { nombre_insumo: string };
  cantidad: number;
  costo_unitario: number;
  subtotal: number;
};

export type Compra = {
  id_compra: number;
  id_proveedor: number;
  proveedor: { nombre_proveedor: string };
  fecha_compra: string;
  total: number;
  folio_factura: string | null;
  detalle: DetalleCompra[];
};

export async function getMesas(access: string, estado?: string): Promise<Mesa[]> {
  const { data } = await http.get("/mesas", {
    ...authCfg(access),
    params: estado ? { estado } : undefined,
  });
  return data;
}

export async function getCategorias(access: string): Promise<Categoria[]> {
  const { data } = await http.get("/categorias", authCfg(access));
  return data;
}

export async function getProductos(
  access: string,
  opts?: { id_categoria?: number; disponible?: boolean }
): Promise<Producto[]> {
  const { data } = await http.get("/productos", { ...authCfg(access), params: opts });
  return data;
}

export async function crearPedido(
  access: string,
  payload: CrearPedidoPayload
): Promise<Pedido> {
  const { data } = await http.post("/pedidos", payload, authCfg(access));
  return data;
}

export async function getEstados(access: string): Promise<Estado[]> {
  const { data } = await http.get("/estados", authCfg(access));
  return data;
}

export async function getPedidos(
  access: string,
  opts?: { estados?: number[]; mias?: boolean; por_cobrar?: boolean }
): Promise<Pedido[]> {
  const params: Record<string, string | boolean> = {};
  if (opts?.estados) params.estados = opts.estados.join(",");
  if (opts?.mias) params.mias = true;
  if (opts?.por_cobrar) params.por_cobrar = true;
  const { data } = await http.get("/pedidos", {
    ...authCfg(access),
    params: Object.keys(params).length ? params : undefined,
  });
  return data;
}

export async function cambiarEstadoPedido(
  access: string,
  id_pedido: number,
  id_estado: number
): Promise<Pedido> {
  const { data } = await http.patch(
    `/pedidos/${id_pedido}/estado`,
    { id_estado },
    authCfg(access)
  );
  return data;
}

export async function getMetodosPago(access: string): Promise<MetodoPago[]> {
  const { data } = await http.get("/metodos_pago", authCfg(access));
  return data;
}

export async function getPedido(access: string, id: number): Promise<Pedido> {
  const { data } = await http.get(`/pedidos/${id}`, authCfg(access));
  return data;
}

export async function cobrarVenta(
  access: string,
  id_pedido: number,
  pagos: { id_metodo_pago: number; monto: number }[]
): Promise<Venta> {
  const { data } = await http.post("/ventas", { id_pedido, pagos }, authCfg(access));
  return data;
}

export async function getCategoriasGasto(access: string): Promise<CategoriaGasto[]> {
  const { data } = await http.get("/gastos/categorias", authCfg(access));
  return data;
}

export async function getGastos(access: string): Promise<Gasto[]> {
  const { data } = await http.get("/gastos", authCfg(access));
  return data;
}

export async function crearGasto(
  access: string,
  data: { id_categoria_gasto: number; concepto: string; monto: number }
): Promise<Gasto> {
  const { data: res } = await http.post("/gastos", data, authCfg(access));
  return res;
}

export async function getInsumos(access: string): Promise<Insumo[]> {
  const { data } = await http.get("/insumos", authCfg(access));
  return data;
}

export async function getInsumo(access: string, id: number): Promise<Insumo> {
  const { data } = await http.get(`/insumos/${id}`, authCfg(access));
  return data;
}

export async function registrarMovimiento(
  access: string,
  id: number,
  data: { tipo: string; motivo: string; cantidad: number }
): Promise<Insumo> {
  const { data: res } = await http.post(
    `/insumos/${id}/movimientos`,
    data,
    authCfg(access)
  );
  return res;
}

export async function getProveedores(access: string): Promise<Proveedor[]> {
  const { data } = await http.get("/proveedores", authCfg(access));
  return data;
}

export async function getCompras(access: string): Promise<Compra[]> {
  const { data } = await http.get("/compras", authCfg(access));
  return data;
}

export async function crearCompra(
  access: string,
  data: {
    id_proveedor: number;
    folio_factura: string | null;
    items: { id_insumo: number; cantidad: number; costo_unitario: number }[];
  }
): Promise<Compra> {
  const { data: res } = await http.post("/compras", data, authCfg(access));
  return res;
}
