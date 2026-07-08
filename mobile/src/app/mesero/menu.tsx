import { router } from "expo-router";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  SectionList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { Categoria, getCategorias, getProductos, Producto } from "@/api/client";
import { money } from "@/lib/format";
import { useAuth } from "@/store/auth";
import { cartCount, cartTotal, useCart } from "@/store/cart";

export default function Menu() {
  const access = useAuth((s) => s.accessToken);
  const items = useCart((s) => s.items);
  const addItem = useCart((s) => s.addItem);
  const decItem = useCart((s) => s.decItem);
  const [secciones, setSecciones] = useState<{ title: string; data: Producto[] }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!access) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [cats, prods] = await Promise.all([
          getCategorias(access),
          getProductos(access, { disponible: true }),
        ]);
        const secs = cats
          .map((c: Categoria) => ({
            title: c.nombre_categoria,
            data: prods.filter((p) => p.id_categoria === c.id_categoria),
          }))
          .filter((s) => s.data.length > 0);
        setSecciones(secs);
      } catch {
        setError("No se pudo cargar el menú.");
      } finally {
        setLoading(false);
      }
    })();
  }, [access]);

  function cantidadDe(id: number) {
    return items.find((it) => it.producto.id_producto === id)?.cantidad ?? 0;
  }

  const total = cartTotal(items);
  const count = cartCount(items);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2b6cb0" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {error && <Text style={styles.error}>{error}</Text>}
      <SectionList
        sections={secciones}
        keyExtractor={(p) => String(p.id_producto)}
        renderSectionHeader={({ section }) => (
          <Text style={styles.sectionH}>{section.title}</Text>
        )}
        renderItem={({ item }) => {
          const n = cantidadDe(item.id_producto);
          return (
            <View style={styles.row}>
              <View style={{ flex: 1 }}>
                <Text style={styles.nombre}>{item.nombre_producto}</Text>
                <Text style={styles.precio}>{money(item.precio_venta)}</Text>
              </View>
              <View style={styles.stepper}>
                <TouchableOpacity
                  style={styles.step}
                  onPress={() => decItem(item.id_producto)}
                >
                  <Text style={styles.stepTxt}>−</Text>
                </TouchableOpacity>
                <Text style={styles.qty}>{n}</Text>
                <TouchableOpacity
                  style={styles.step}
                  onPress={() =>
                    addItem({
                      id_producto: item.id_producto,
                      nombre_producto: item.nombre_producto,
                      precio_venta: Number(item.precio_venta),
                    })
                  }
                >
                  <Text style={styles.stepTxt}>+</Text>
                </TouchableOpacity>
              </View>
            </View>
          );
        }}
      />
      <TouchableOpacity
        style={[styles.bar, count === 0 && styles.barDisabled]}
        disabled={count === 0}
        onPress={() => router.push("/mesero/carrito" as any)}
      >
        <Text style={styles.barTxt}>
          Ver pedido ({count}) — ${total.toFixed(2)}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f4f5f7" },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  sectionH: {
    backgroundColor: "#edf2f7",
    paddingHorizontal: 16,
    paddingVertical: 6,
    fontWeight: "700",
    color: "#2d3748",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#e2e8f0",
  },
  nombre: { fontSize: 15, color: "#2d3748" },
  precio: { color: "#718096", fontSize: 13 },
  stepper: { flexDirection: "row", alignItems: "center", gap: 10 },
  step: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#2b6cb0",
    alignItems: "center",
    justifyContent: "center",
  },
  stepTxt: { color: "#fff", fontSize: 18, fontWeight: "700" },
  qty: { minWidth: 20, textAlign: "center", fontSize: 16 },
  bar: { backgroundColor: "#2b6cb0", padding: 16, alignItems: "center" },
  barDisabled: { backgroundColor: "#a0aec0" },
  barTxt: { color: "#fff", fontWeight: "700", fontSize: 16 },
  error: { color: "#c53030", textAlign: "center", padding: 8 },
});
