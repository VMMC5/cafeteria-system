import { create } from "zustand";

export type ProductoCarrito = {
  id_producto: number;
  nombre_producto: string;
  precio_venta: number;
};

export type CartItem = {
  producto: ProductoCarrito;
  cantidad: number;
  observaciones?: string | null;
};

type CartState = {
  id_mesa: number | null;
  mesa_numero: number | null;
  items: CartItem[];
  observaciones: string;
  setMesa: (id: number, numero: number) => void;
  addItem: (producto: ProductoCarrito) => void;
  decItem: (idProducto: number) => void;
  removeItem: (idProducto: number) => void;
  setObservaciones: (txt: string) => void;
  clear: () => void;
};

export function cartTotal(items: CartItem[]): number {
  return items.reduce((s, it) => s + it.cantidad * it.producto.precio_venta, 0);
}

export function cartCount(items: CartItem[]): number {
  return items.reduce((s, it) => s + it.cantidad, 0);
}

export function toPayload(state: {
  id_mesa: number | null;
  observaciones: string;
  items: CartItem[];
}) {
  return {
    id_mesa: state.id_mesa,
    observaciones: state.observaciones || null,
    items: state.items.map((it) => ({
      id_producto: it.producto.id_producto,
      cantidad: it.cantidad,
      observaciones: it.observaciones ?? null,
    })),
  };
}

export const useCart = create<CartState>((set) => ({
  id_mesa: null,
  mesa_numero: null,
  items: [],
  observaciones: "",

  setMesa: (id, numero) => set({ id_mesa: id, mesa_numero: numero }),

  addItem: (producto) =>
    set((s) => {
      const existe = s.items.find(
        (it) => it.producto.id_producto === producto.id_producto
      );
      if (existe) {
        return {
          items: s.items.map((it) =>
            it.producto.id_producto === producto.id_producto
              ? { ...it, cantidad: it.cantidad + 1 }
              : it
          ),
        };
      }
      return {
        items: [...s.items, { producto, cantidad: 1, observaciones: null }],
      };
    }),

  decItem: (idProducto) =>
    set((s) => ({
      items: s.items
        .map((it) =>
          it.producto.id_producto === idProducto
            ? { ...it, cantidad: it.cantidad - 1 }
            : it
        )
        .filter((it) => it.cantidad > 0),
    })),

  removeItem: (idProducto) =>
    set((s) => ({
      items: s.items.filter((it) => it.producto.id_producto !== idProducto),
    })),

  setObservaciones: (txt) => set({ observaciones: txt }),

  clear: () =>
    set({ id_mesa: null, mesa_numero: null, items: [], observaciones: "" }),
}));
