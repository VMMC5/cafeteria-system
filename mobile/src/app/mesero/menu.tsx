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
import { colors, fonts, radius, sizes, spacing } from "@/theme";
import { Stepper } from "@/ui";

export default function Menu() {
  const access = useAuth((s) => s.accessToken);
  const items = useCart((s) => s.items);
  const mesaNumero = useCart((s) => s.mesa_numero);
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
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} hitSlop={10}>
          <Text style={styles.back}>‹ Mesas</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Menú{mesaNumero != null ? ` · Mesa ${mesaNumero}` : ""}</Text>
      </View>
      {error && <Text style={styles.error}>{error}</Text>}
      <SectionList
        sections={secciones}
        keyExtractor={(p) => String(p.id_producto)}
        stickySectionHeadersEnabled={false}
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
              <Stepper
                value={n}
                onRemove={() => decItem(item.id_producto)}
                onAdd={() =>
                  addItem({
                    id_producto: item.id_producto,
                    nombre_producto: item.nombre_producto,
                    precio_venta: Number(item.precio_venta),
                  })
                }
              />
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
          Ver pedido ({count}) — {money(total)}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.cream },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.cream },
  header: { paddingHorizontal: spacing.screen, paddingTop: 24, paddingBottom: spacing.sm, gap: 4 },
  back: { fontFamily: fonts.semibold, fontSize: 14, color: colors.accent },
  title: { fontFamily: fonts.title, fontSize: 24, color: colors.coffee900 },
  sectionH: {
    fontFamily: fonts.bold,
    fontSize: 11.5,
    letterSpacing: 1,
    textTransform: "uppercase",
    color: colors.muted,
    paddingHorizontal: spacing.screen,
    paddingTop: spacing.lg,
    paddingBottom: 6,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.card,
    paddingHorizontal: spacing.screen,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  nombre: { fontFamily: fonts.semibold, fontSize: 15, color: colors.coffee900 },
  precio: { fontFamily: fonts.title, color: colors.coffee700, fontSize: 14, marginTop: 2 },
  bar: {
    backgroundColor: colors.accent,
    height: sizes.button,
    margin: spacing.screen,
    borderRadius: radius.button,
    alignItems: "center",
    justifyContent: "center",
  },
  barDisabled: { backgroundColor: colors.disabled },
  barTxt: { color: colors.onAccent, fontFamily: fonts.bold, fontSize: 15.5 },
  error: { fontFamily: fonts.medium, color: colors.error, textAlign: "center", padding: 8 },
});
