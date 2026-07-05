import { cartCount, cartTotal, toPayload, useCart } from "./cart";

const P = (id: number, precio: number) => ({
  id_producto: id,
  nombre_producto: "P" + id,
  precio_venta: precio,
});

beforeEach(() => {
  useCart.setState({ id_mesa: null, mesa_numero: null, items: [], observaciones: "" });
});

test("addItem agrega y luego incrementa", () => {
  const { addItem } = useCart.getState();
  addItem(P(1, 10));
  addItem(P(1, 10));
  addItem(P(2, 5));
  const items = useCart.getState().items;
  expect(items.length).toBe(2);
  expect(items.find((i) => i.producto.id_producto === 1)!.cantidad).toBe(2);
});

test("decItem baja y a 0 elimina", () => {
  const { addItem, decItem } = useCart.getState();
  addItem(P(1, 10));
  decItem(1);
  expect(useCart.getState().items.length).toBe(0);
});

test("cartTotal y cartCount", () => {
  const { addItem } = useCart.getState();
  addItem(P(1, 10));
  addItem(P(1, 10));
  addItem(P(2, 5));
  const items = useCart.getState().items;
  expect(cartTotal(items)).toBe(25);
  expect(cartCount(items)).toBe(3);
});

test("toPayload arma el cuerpo correcto", () => {
  const { setMesa, addItem, setObservaciones } = useCart.getState();
  setMesa(3, 3);
  addItem(P(1, 10));
  setObservaciones("Sin sal");
  expect(toPayload(useCart.getState())).toEqual({
    id_mesa: 3,
    observaciones: "Sin sal",
    items: [{ id_producto: 1, cantidad: 1, observaciones: null }],
  });
});

test("clear vacía todo", () => {
  const { setMesa, addItem, clear } = useCart.getState();
  setMesa(3, 3);
  addItem(P(1, 10));
  clear();
  const s = useCart.getState();
  expect(s.items.length).toBe(0);
  expect(s.id_mesa).toBeNull();
});
