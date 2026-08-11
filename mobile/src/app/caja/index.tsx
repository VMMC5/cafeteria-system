import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { getPedidos, Pedido } from "@/api/client";
import { agruparPorMesa, CuentaMesa } from "@/lib/caja";
import { money } from "@/lib/format";
import { useAuth } from "@/store/auth";
import { cardShadow, colors, fonts, radius, spacing } from "@/theme";
import { Badge, BottomNav } from "@/ui";
import { NAV_CAJA, onNavPress } from "@/ui/nav";

const POLL_MS = 10000;

function CuentaCard({
  cuenta,
  expandida,
  onToggle,
}: {
  cuenta: CuentaMesa;
  expandida: boolean;
  onToggle: () => void;
}) {
  const varias = cuenta.pedidos.length > 1;
  const ids = cuenta.pedidos.map((p) => p.id_pedido).join(",");
  return (
    <View style={styles.card}>
      <View style={styles.cardHead}>
        <View>
          <Text style={styles.mesa}>Mesa {cuenta.numero_mesa}</Text>
          <Text style={styles.meta}>
            {varias
              ? `${cuenta.pedidos.length} rondas`
              : `#${cuenta.pedidos[0].id_pedido}`}
          </Text>
        </View>
        <Text style={styles.total}>{money(cuenta.total)}</Text>
      </View>
      {!cuenta.cobrable && (
        <Badge label="ronda en cocina" variant="warn" style={styles.badge} />
      )}
      <TouchableOpacity
        style={[styles.cobrarBtn, !cuenta.cobrable && styles.cobrarBtnOff]}
        disabled={!cuenta.cobrable}
        onPress={() => router.push(`/caja/cobro?ids=${ids}` as any)}
      >
        <Text style={styles.cobrarTxt}>
          {varias ? "Cobrar cuenta" : "Cobrar"}
        </Text>
      </TouchableOpacity>
      {varias && (
        <TouchableOpacity onPress={onToggle}>
          <Text style={styles.verRondas}>
            {expandida ? "Ocultar rondas" : "Ver rondas"}
          </Text>
        </TouchableOpacity>
      )}
      {expandida &&
        cuenta.pedidos.map((p) => (
          <TouchableOpacity
            key={p.id_pedido}
            style={styles.ronda}
            onPress={() => router.push(`/caja/cobro?ids=${p.id_pedido}` as any)}
          >
            <Text style={styles.rondaTxt}>
              #{p.id_pedido} · {p.estado.nombre_estado}
            </Text>
            <Text style={styles.rondaTotal}>{money(p.total)}</Text>
          </TouchableOpacity>
        ))}
    </View>
  );
}

export default function Caja() {
  const access = useAuth((s) => s.accessToken);
  const logout = useAuth((s) => s.logout);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [expandidas, setExpandidas] = useState<Set<number>>(new Set());
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
          <Text style={styles.subtitle}>Cuentas por mesa</Text>
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
          data={agruparPorMesa(pedidos)}
          keyExtractor={(c) => String(c.id_mesa)}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <CuentaCard
              cuenta={item}
              expandida={expandidas.has(item.id_mesa)}
              onToggle={() =>
                setExpandidas((s) => {
                  const n = new Set(s);
                  n.has(item.id_mesa) ? n.delete(item.id_mesa) : n.add(item.id_mesa);
                  return n;
                })
              }
            />
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
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardLg,
    padding: spacing.lg,
    ...cardShadow,
  },
  cardHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  badge: { alignSelf: "flex-start", marginTop: spacing.sm },
  cobrarBtn: {
    marginTop: spacing.md,
    height: 40,
    borderRadius: radius.button,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  cobrarBtnOff: { backgroundColor: colors.disabled },
  cobrarTxt: { color: colors.onAccent, fontFamily: fonts.bold, fontSize: 14 },
  verRondas: {
    color: colors.accent,
    fontFamily: fonts.semibold,
    fontSize: 13,
    paddingTop: spacing.sm,
    textAlign: "center",
  },
  ronda: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 6,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  rondaTxt: { fontFamily: fonts.body, fontSize: 13, color: colors.coffee700 },
  rondaTotal: { fontFamily: fonts.semibold, fontSize: 13, color: colors.coffee900 },
  mesa: { fontFamily: fonts.title, fontSize: 17, color: colors.coffee900 },
  meta: { fontFamily: fonts.body, color: colors.muted, fontSize: 13, marginTop: 2 },
  total: { fontFamily: fonts.title, fontSize: 18, color: colors.coffee900 },
  muted: { fontFamily: fonts.body, color: colors.muted, textAlign: "center", marginVertical: 16 },
  error: { fontFamily: fonts.medium, color: colors.error, textAlign: "center", marginVertical: 8 },
});
