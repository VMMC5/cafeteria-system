import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { getInsumos, Insumo } from "@/api/client";
import { cantidad } from "@/lib/format";
import { stockBajo } from "@/lib/inventario";
import { useAuth } from "@/store/auth";
import { cardShadow, colors, fonts, radius, spacing } from "@/theme";
import { Badge, BottomNav } from "@/ui";
import { NAV_COCINA, onNavPress } from "@/ui/nav";

export default function Inventario() {
  const access = useAuth((s) => s.accessToken);
  const logout = useAuth((s) => s.logout);
  const [insumos, setInsumos] = useState<Insumo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    if (!access) return;
    setLoading(true);
    setError(null);
    try {
      setInsumos(await getInsumos(access));
    } catch {
      setError("No se pudo cargar el inventario.");
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
          <Text style={styles.title}>Inventario</Text>
          <Text style={styles.subtitle}>Toca un insumo para ajustar su stock</Text>
        </View>
        {loading && <ActivityIndicator size="large" color={colors.accent} />}
        {error && (
          <TouchableOpacity onPress={cargar}>
            <Text style={styles.error}>{error} (tocar para reintentar)</Text>
          </TouchableOpacity>
        )}
        <FlatList
          data={insumos}
          keyExtractor={(i) => String(i.id_insumo)}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            !loading ? <Text style={styles.muted}>No hay insumos.</Text> : null
          }
          renderItem={({ item }) => {
            const bajo = stockBajo(item);
            return (
              <TouchableOpacity
                style={[styles.card, bajo && styles.cardBajo]}
                onPress={() =>
                  router.push(`/cocina/ajuste?id_insumo=${item.id_insumo}` as any)
                }
              >
                <View style={{ flex: 1 }}>
                  <Text style={styles.nombre}>{item.nombre_insumo}</Text>
                  <Text style={styles.meta}>
                    mín. {cantidad(item.stock_minimo)} {item.unidad.abreviatura}
                  </Text>
                </View>
                <View style={styles.derecha}>
                  <Text style={[styles.stock, bajo && styles.stockBajoTxt]}>
                    {cantidad(item.stock_actual)} {item.unidad.abreviatura}
                  </Text>
                  {bajo && <Badge label="Stock bajo" variant="error" />}
                </View>
              </TouchableOpacity>
            );
          }}
        />
      </View>
      <BottomNav items={NAV_COCINA} active="inventario" onPress={(k) => onNavPress(NAV_COCINA, k, logout)} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.cream },
  container: { flex: 1, padding: spacing.screen },
  header: { marginTop: 24, marginBottom: spacing.lg },
  title: { fontFamily: fonts.title, fontSize: 24, color: colors.coffee900 },
  subtitle: { fontFamily: fonts.body, fontSize: 14, color: colors.muted, marginTop: 2 },
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
  cardBajo: { borderWidth: 2, borderColor: colors.error },
  nombre: { fontFamily: fonts.title, fontSize: 15.5, color: colors.coffee900 },
  meta: { fontFamily: fonts.body, color: colors.muted, fontSize: 13, marginTop: 2 },
  derecha: { alignItems: "flex-end", gap: 4 },
  stock: { fontFamily: fonts.title, fontSize: 16, color: colors.coffee900 },
  stockBajoTxt: { color: colors.error },
  muted: { fontFamily: fonts.body, color: colors.muted, textAlign: "center", marginVertical: 16 },
  error: { fontFamily: fonts.medium, color: colors.error, textAlign: "center", marginVertical: 8 },
});
