import { Pedido, Venta } from "@/api/client";
import { ticketHtml } from "./ticket";

const VENTA: Venta = {
  id_venta: 1,
  ids_pedidos: [633],
  folio: "V-000631",
  estado_venta: "Pagada",
  fecha_venta: "2026-08-10T22:00:00Z",
  total: 103,
  subtotal: 88.79,
  iva: 14.21,
  cambio: 0,
  pagos: [
    { id_pago: 1, id_metodo_pago: 1, metodo: { nombre_metodo: "Efectivo" }, monto: 50, referencia: null },
    { id_pago: 2, id_metodo_pago: 2, metodo: { nombre_metodo: "Tarjeta" }, monto: 53, referencia: "1234" },
  ],
};

const PEDIDO: Pedido = {
  id_pedido: 633,
  id_mesa: 4,
  mesa: { numero_mesa: 4 },
  estado: { id_estado: 4, nombre_estado: "Entregado" },
  fecha_pedido: "2026-08-10T21:30:00Z",
  observaciones: null,
  detalle: [
    {
      cantidad: 2,
      observaciones: null,
      producto: { nombre_producto: "Café Americano" },
      precio_unitario: 44.4,
      subtotal: 88.8,
    },
  ],
  total: 103,
};

test("ticketHtml incluye marca, folio, mesa, productos, totales y pagos", () => {
  const html = ticketHtml(VENTA, [PEDIDO]);
  expect(html).toContain("Cafetería");
  expect(html).toContain("Aroma");
  expect(html).toContain("V-000631");
  expect(html).toContain("Mesa 4");
  expect(html).toContain("Café Americano");
  expect(html).toContain("2 × $44.40");
  expect(html).toContain("$88.80"); // subtotal de la línea
  expect(html).toContain("$103.00"); // total
  expect(html).toContain("$14.21"); // IVA
  expect(html).toContain("Efectivo");
  expect(html).toContain("Tarjeta (1234)");
  expect(html).toContain("Cambio");
  expect(html).toContain("Gracias por su visita");
});

test("ticketHtml funciona sin pedido y escapa HTML en textos", () => {
  const venta = {
    ...VENTA,
    pagos: [
      {
        id_pago: 1,
        id_metodo_pago: 1,
        metodo: { nombre_metodo: "Efectivo" },
        monto: 103,
        referencia: "<script>",
      },
    ],
  };
  const html = ticketHtml(venta, []);
  expect(html).toContain("V-000631");
  expect(html).not.toContain("Mesa"); // sin pedido no hay mesa ni líneas
  expect(html).not.toContain("<script>");
  expect(html).toContain("&lt;script&gt;");
});

test("ticketHtml: cuenta de dos rondas lista las líneas de ambas", () => {
  const linea = (nombre: string) => ({
    producto: { nombre_producto: nombre },
    cantidad: 1,
    precio_unitario: "58.00",
    subtotal: "58.00",
  });
  const p1 = { mesa: { numero_mesa: 4 }, detalle: [linea("Latte")] } as any;
  const p2 = { mesa: { numero_mesa: 4 }, detalle: [linea("Croissant")] } as any;
  const html = ticketHtml(VENTA, [p1, p2]);
  expect(html).toContain("Latte");
  expect(html).toContain("Croissant");
});
