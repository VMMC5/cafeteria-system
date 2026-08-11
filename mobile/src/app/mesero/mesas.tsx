import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { getMesas, Mesa } from "@/api/client";
import { mesaSeleccionable } from "@/lib/mesero";
import { useAuth } from "@/store/auth";
import { useCart } from "@/store/cart";
import { cardShadow, colors, fonts, radius, spacing } from "@/theme";
import { Badge, BottomNav } from "@/ui";
import { NAV_MESERO, onNavPress } from "@/ui/nav";

export default function Mesas() {
  const access = useAuth((s) => s.accessToken);
  const logout = useAuth((s) => s.logout);
  const setMesa = useCart((s) => s.setMesa);
  const clear = useCart((s) => s.clear);
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    if (!access) return;
    setLoading(true);
    setError(null);
    try {
      setMesas(await getMesas(access));
    } catch {
      setError("No se pudieron cargar las mesas.");
    } finally {
      setLoading(false);
    }
  }, [access]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  function elegir(m: Mesa) {
    clear();
    setMesa(m.id_mesa, m.numero_mesa);
    router.push("/mesero/menu" as any);
  }

  return (
    <View style={styles.screen}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Mesas</Text>
          <Text style={styles.subtitle}>Elige una mesa; las ocupadas aceptan otra ronda</Text>
        </View>
        {loading && <ActivityIndicator size="large" color={colors.accent} />}
        {error && (
          <TouchableOpacity onPress={cargar}>
            <Text style={styles.error}>{error} (tocar para reintentar)</Text>
          </TouchableOpacity>
        )}
        <FlatList
          data={mesas}
          keyExtractor={(m) => String(m.id_mesa)}
          numColumns={2}
          columnWrapperStyle={styles.rowGap}
          contentContainerStyle={styles.grid}
          renderItem={({ item }) => {
            const libre = item.estado === "Disponible";
            const seleccionable = mesaSeleccionable(item.estado);
            return (
              <TouchableOpacity
                style={[styles.card, !seleccionable && styles.cardBusy]}
                disabled={!seleccionable}
                onPress={() => elegir(item)}
              >
                <Text style={styles.numero}>Mesa {item.numero_mesa}</Text>
                <Text style={styles.cap}>{item.capacidad} personas</Text>
                <Badge
                  label={item.estado}
                  variant={libre ? "ok" : item.estado === "Ocupada" ? "busy" : "warn"}
                  style={{ alignSelf: "center" }}
                />
                {item.estado === "Ocupada" && (
                  <Text style={styles.hint}>Toca para agregar otro pedido</Text>
                )}
              </TouchableOpacity>
            );
          }}
        />
      </View>
      <BottomNav items={NAV_MESERO} active="mesas" onPress={(k) => onNavPress(NAV_MESERO, k, logout)} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.cream },
  container: { flex: 1, padding: spacing.screen },
  header: { marginTop: 24, marginBottom: spacing.lg },
  title: { fontFamily: fonts.title, fontSize: 24, color: colors.coffee900 },
  subtitle: { fontFamily: fonts.body, fontSize: 14, color: colors.muted, marginTop: 2 },
  grid: { gap: spacing.md, paddingBottom: spacing.lg },
  rowGap: { gap: spacing.md },
  card: {
    flex: 1,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardLg,
    padding: spacing.xl,
    alignItems: "center",
    gap: 6,
    ...cardShadow,
  },
  cardBusy: { opacity: 0.55 },
  numero: { fontFamily: fonts.title, fontSize: 17, color: colors.coffee900 },
  cap: { fontFamily: fonts.body, color: colors.muted, fontSize: 13 },
  hint: { fontFamily: fonts.body, fontSize: 12, color: colors.muted, textAlign: "center" },
  error: { fontFamily: fonts.medium, color: colors.error, textAlign: "center", marginVertical: 8 },
});
