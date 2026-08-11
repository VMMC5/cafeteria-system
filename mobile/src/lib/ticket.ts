import { Pedido, Venta } from "@/api/client";
import { money } from "./format";

/** Escapa texto para incrustarlo en el HTML del ticket. */
function esc(texto: string): string {
  return texto.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/**
 * HTML imprimible del comprobante (expo-print). Formato angosto tipo ticket
 * de impresora térmica; los pedidos aportan mesa y líneas — con lista vacía
 * el ticket sale solo con los totales de la venta.
 */
export function ticketHtml(venta: Venta, pedidos: Pedido[]): string {
  const fecha = new Date(venta.fecha_venta).toLocaleString("es-MX", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const mesa = pedidos[0]?.mesa.numero_mesa;

  const lineas = pedidos
    .flatMap((p) => p.detalle)
    .map(
      (d) => `
      <tr>
        <td>${esc(d.producto.nombre_producto)}<br>
          <span class="mut">${d.cantidad} × ${money(d.precio_unitario)}</span></td>
        <td class="num">${money(d.subtotal)}</td>
      </tr>`
    )
    .join("");

  const pagos = venta.pagos
    .map(
      (p) => `
      <tr>
        <td>${esc(p.metodo.nombre_metodo)}${p.referencia ? ` (${esc(p.referencia)})` : ""}</td>
        <td class="num">${money(p.monto)}</td>
      </tr>`
    )
    .join("");

  return `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  body { font-family: -apple-system, Roboto, sans-serif; color: #33241B;
         max-width: 300px; margin: 0 auto; padding: 16px 8px; font-size: 13px; }
  h1 { font-size: 18px; text-align: center; margin: 0; font-weight: 600; }
  h1 em { color: #8A5A3B; }
  .head { text-align: center; color: #8A7A68; margin: 4px 0 10px; line-height: 1.5; }
  table { width: 100%; border-collapse: collapse; }
  td { padding: 3px 0; vertical-align: top; }
  .num { text-align: right; white-space: nowrap; }
  .mut { color: #8A7A68; font-size: 12px; }
  .tot td { font-weight: 700; }
  hr { border: none; border-top: 1px dashed #C8B9A6; margin: 8px 0; }
  .gracias { text-align: center; font-style: italic; color: #8A7A68; margin-top: 12px; }
</style>
</head>
<body>
  <h1>Cafetería <em>Aroma</em></h1>
  <div class="head">
    Folio ${esc(venta.folio)}<br>
    ${esc(fecha)}${mesa ? `<br>Mesa ${mesa}` : ""}
  </div>
  <hr>
  ${lineas ? `<table>${lineas}</table><hr>` : ""}
  <table>
    <tr><td>Subtotal</td><td class="num">${money(venta.subtotal)}</td></tr>
    <tr><td>IVA</td><td class="num">${money(venta.iva)}</td></tr>
    <tr class="tot"><td>Total</td><td class="num">${money(venta.total)}</td></tr>
  </table>
  <hr>
  <table>
    ${pagos}
    <tr class="tot"><td>Cambio</td><td class="num">${money(venta.cambio)}</td></tr>
  </table>
  <p class="gracias">¡Gracias por su visita!</p>
</body>
</html>`;
}
