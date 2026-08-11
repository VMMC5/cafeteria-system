import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { Compra, getCompras } from "@/api/client";
import { money } from "@/lib/format";
import { useAuth } from "@/store/auth";
import { cardShadow, colors, fonts, radius, spacing } from "@/theme";
import { BottomNav } from "@/ui";
import { NAV_COCINA, onNavPress } from "@/ui/nav";

export default function Compras() {
  const access = useAuth((s) => s.accessToken);
  const logout = useAuth((s) => s.logout);
  const [compras, setCompras] = useState<Compra[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    if (!access) return;
    setLoading(true);
    setError(null);
    try {
      setCompras(await getCompras(access));
    } catch {
      setError("No se pudieron cargar las compras.");
    } finally {
      setLoading(false);
    }
  }, [access]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  return (
    <View style={styles.screen}>
      <View style={styles.container}>
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>Compras</Text>
            <Text style={styles.subtitle}>Entradas de insumos a inventario</Text>
          </View>
          <TouchableOpacity
            style={styles.nuevaBtn}
            onPress={() => router.push("/cocina/compra-nueva" as any)}
          >
            <Text style={styles.nuevaTxt}>+ Nueva</Text>
          </TouchableOpacity>
        </View>
        {loading && <ActivityIndicator size="large" color={colors.accent} />}
        {error && (
          <TouchableOpacity onPress={cargar}>
            <Text style={styles.error}>{error} (tocar para reintentar)</Text>
          </TouchableOpacity>
        )}
        <FlatList
          data={compras}
          keyExtractor={(c) => String(c.id_compra)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            !loading ? <Text style={styles.muted}>No hay compras.</Text> : null
          }
          renderItem={({ item }) => (
            <View style={styles.card}>
              <View style={{ flex: 1 }}>
                <Text style={styles.prov}>{item.proveedor.nombre_proveedor}</Text>
                <Text style={styles.meta}>
                  {item.folio_factura ?? `#${item.id_compra}`}
                </Text>
              </View>
              <Text style={styles.total}>{money(item.total)}</Text>
            </View>
          )}
        />
      </View>
      <BottomNav items={NAV_COCINA} active="compras" onPress={(k) => onNavPress(NAV_COCINA, k, logout)} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.cream },
  container: { flex: 1, padding: spacing.screen },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginTop: 24,
    marginBottom: spacing.lg,
    gap: spacing.md,
  },
  title: { fontFamily: fonts.title, fontSize: 24, color: colors.coffee900 },
  subtitle: { fontFamily: fonts.body, fontSize: 14, color: colors.muted, marginTop: 2 },
  nuevaBtn: {
    backgroundColor: colors.accent,
    borderRadius: radius.button,
    paddingHorizontal: 16,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
  },
  nuevaTxt: { color: colors.onAccent, fontFamily: fonts.bold, fontSize: 14 },
  list: { gap: spacing.sm + 2, paddingBottom: spacing.lg },
  card: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardLg,
    padding: spacing.lg,
    ...cardShadow,
  },
  prov: { fontFamily: fonts.title, fontSize: 15.5, color: colors.coffee900 },
  meta: { fontFamily: fonts.body, color: colors.muted, fontSize: 13, marginTop: 2 },
  total: { fontFamily: fonts.title, fontSize: 16, color: colors.coffee900 },
  muted: { fontFamily: fonts.body, color: colors.muted, textAlign: "center", marginVertical: 16 },
  error: { fontFamily: fonts.medium, color: colors.error, textAlign: "center", marginVertical: 8 },
});
