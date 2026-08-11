import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { getProductos, Producto } from "@/api/client";
import { filtrarProductos } from "@/lib/recetas";
import { useAuth } from "@/store/auth";
import { cardShadow, colors, fonts, radius, spacing } from "@/theme";
import { BottomNav, Input } from "@/ui";
import { NAV_COCINA, onNavPress } from "@/ui/nav";

export default function Recetas() {
  const access = useAuth((s) => s.accessToken);
  const logout = useAuth((s) => s.logout);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    if (!access) return;
    setLoading(true);
    setError(null);
    try {
      setProductos(await getProductos(access));
    } catch {
      setError("No se pudieron cargar los productos.");
    } finally {
      setLoading(false);
    }
  }, [access]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const visibles = filtrarProductos(productos, query);

  return (
    <View style={styles.screen}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Recetas</Text>
          <Text style={styles.subtitle}>Insumos por producto del menú</Text>
        </View>

        <Input
          value={query}
          onChangeText={setQuery}
          placeholder="Buscar producto"
          autoCorrect={false}
          style={styles.buscador}
        />

        {loading && <ActivityIndicator size="large" color={colors.accent} />}
        {error && (
          <TouchableOpacity onPress={cargar}>
            <Text style={styles.error}>{error} (tocar para reintentar)</Text>
          </TouchableOpacity>
        )}
        <FlatList
          data={visibles}
          keyExtractor={(p) => String(p.id_producto)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            !loading ? <Text style={styles.muted}>No hay productos.</Text> : null
          }
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.card}
              onPress={() =>
                router.push(
                  `/cocina/receta-detalle?id_producto=${item.id_producto}&nombre=${encodeURIComponent(
                    item.nombre_producto
                  )}` as any
                )
              }
            >
              <Text style={styles.nombre}>{item.nombre_producto}</Text>
              <Text style={styles.chevron}>›</Text>
            </TouchableOpacity>
          )}
        />
      </View>
      <BottomNav items={NAV_COCINA} active="recetas" onPress={(k) => onNavPress(NAV_COCINA, k, logout)} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.cream },
  container: { flex: 1, padding: spacing.screen },
  header: { marginTop: 24, marginBottom: spacing.lg },
  title: { fontFamily: fonts.title, fontSize: 24, color: colors.coffee900 },
  subtitle: { fontFamily: fonts.body, fontSize: 14, color: colors.muted, marginTop: 2 },
  buscador: { marginBottom: spacing.md },
  list: { gap: spacing.sm + 2, paddingBottom: spacing.lg },
  card: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardLg,
    padding: spacing.lg,
    ...cardShadow,
  },
  nombre: { fontFamily: fonts.title, fontSize: 15.5, color: colors.coffee900, flex: 1 },
  chevron: { fontSize: 22, color: colors.caramel },
  muted: { fontFamily: fonts.body, color: colors.muted, textAlign: "center", marginVertical: 16 },
  error: { fontFamily: fonts.medium, color: colors.error, textAlign: "center", marginVertical: 8 },
});
