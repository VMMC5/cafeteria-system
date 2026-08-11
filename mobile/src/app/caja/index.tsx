import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { getPedidos, Pedido } from "@/api/client";
import { money } from "@/lib/format";
import { useAuth } from "@/store/auth";
import { cardShadow, colors, fonts, radius, spacing } from "@/theme";
import { BottomNav } from "@/ui";
import { NAV_CAJA, onNavPress } from "@/ui/nav";

const POLL_MS = 10000;

export default function Caja() {
  const access = useAuth((s) => s.accessToken);
  const logout = useAuth((s) => s.logout);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(
    async (mostrarSpinner: boolean) => {
      if (!access) return;
      if (mostrarSpinner) setLoading(true);
      setError(null);
      try {
        setPedidos(await getPedidos(access, { por_cobrar: true }));
      } catch {
        setError("No se pudieron cargar los pendientes de cobro.");
      } finally {
        if (mostrarSpinner) setLoading(false);
      }
    },
    [access]
  );

  useFocusEffect(
    useCallback(() => {
      cargar(true);
      const id = setInterval(() => cargar(false), POLL_MS);
      return () => clearInterval(id);
    }, [cargar])
  );

  return (
    <View style={styles.screen}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Caja</Text>
          <Text style={styles.subtitle}>Pedidos entregados por cobrar</Text>
        </View>
        {loading && <ActivityIndicator size="large" color={colors.accent} />}
        {error && (
          <TouchableOpacity onPress={() => cargar(true)}>
            <Text style={styles.error}>{error} (tocar para reintentar)</Text>
          </TouchableOpacity>
        )}
        {!loading && !error && pedidos.length === 0 && (
          <Text style={styles.muted}>No hay pedidos por cobrar.</Text>
        )}
        <FlatList
          data={pedidos}
          keyExtractor={(p) => String(p.id_pedido)}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.card}
              onPress={() =>
                router.push(`/caja/cobro?id_pedido=${item.id_pedido}` as any)
              }
            >
              <View>
                <Text style={styles.mesa}>Mesa {item.mesa.numero_mesa}</Text>
                <Text style={styles.meta}>#{item.id_pedido}</Text>
              </View>
              <Text style={styles.total}>{money(item.total)}</Text>
            </TouchableOpacity>
          )}
        />
      </View>
      <BottomNav items={NAV_CAJA} active="cobrar" onPress={(k) => onNavPress(NAV_CAJA, k, logout)} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.cream },
  container: { flex: 1, padding: spacing.screen },
  header: { marginTop: 24, marginBottom: spacing.lg },
  title: { fontFamily: fonts.title, fontSize: 24, color: colors.coffee900 },
  subtitle: { fontFamily: fonts.body, fontSize: 14, color: colors.muted, marginTop: 2 },
  list: { gap: spacing.md, paddingBottom: spacing.lg },
  card: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardLg,
    padding: spacing.lg,
    ...cardShadow,
  },
  mesa: { fontFamily: fonts.title, fontSize: 17, color: colors.coffee900 },
  meta: { fontFamily: fonts.body, color: colors.muted, fontSize: 13, marginTop: 2 },
  total: { fontFamily: fonts.title, fontSize: 18, color: colors.coffee900 },
  muted: { fontFamily: fonts.body, color: colors.muted, textAlign: "center", marginVertical: 16 },
  error: { fontFamily: fonts.medium, color: colors.error, textAlign: "center", marginVertical: 8 },
});
