import { useFocusEffect } from "expo-router";
import { useCallback, useRef, useState } from "react";
import { ActivityIndicator, Alert, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { cambiarEstadoPedido, getEstados, getPedidos, Pedido } from "@/api/client";
import { minutosDesde } from "@/lib/cocina";
import { entregable, prioridadEstado } from "@/lib/mesero";
import { useAuth } from "@/store/auth";
import { cardShadow, colors, fonts, radius, spacing } from "@/theme";
import { Badge, BadgeVariant, BottomNav, PrimaryButton } from "@/ui";
import { NAV_MESERO, onNavPress } from "@/ui/nav";

const POLL_MS = 10000;
const ACTIVOS = ["Pendiente", "En preparación", "Listo"];

const BADGE_DE: Record<string, BadgeVariant> = {
  Pendiente: "warn",
  "En preparación": "busy",
  Listo: "ok",
};

export default function MisPedidos() {
  const access = useAuth((s) => s.accessToken);
  const logout = useAuth((s) => s.logout);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const estadoIds = useRef<Record<string, number>>({});

  const cargar = useCallback(
    async (mostrarSpinner: boolean) => {
      if (!access) return;
      if (mostrarSpinner) setLoading(true);
      setError(null);
      try {
        if (Object.keys(estadoIds.current).length === 0) {
          const estados = await getEstados(access);
          estadoIds.current = Object.fromEntries(
            estados.map((e) => [e.nombre_estado, e.id_estado])
          );
        }
        const ids = ACTIVOS.map((n) => estadoIds.current[n]).filter(
          (x): x is number => typeof x === "number"
        );
        const lista = await getPedidos(access, { mias: true, estados: ids });
        lista.sort((a, b) => {
          const pa = prioridadEstado(a.estado.nombre_estado);
          const pb = prioridadEstado(b.estado.nombre_estado);
          if (pa !== pb) return pa - pb;
          return (
            new Date(a.fecha_pedido).getTime() - new Date(b.fecha_pedido).getTime()
          );
        });
        setPedidos(lista);
      } catch {
        setError("No se pudieron cargar tus pedidos.");
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

  async function entregar(p: Pedido) {
    if (!access) return;
    const destino = estadoIds.current["Entregado"];
    if (destino === undefined) return;
    try {
      await cambiarEstadoPedido(access, p.id_pedido, destino);
    } catch {
      Alert.alert("Aviso", "No se pudo entregar el pedido; se recargó la lista.");
    } finally {
      cargar(false);
    }
  }

  return (
    <View style={styles.screen}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Mis pedidos</Text>
          <Text style={styles.subtitle}>Pedidos activos de tus mesas</Text>
        </View>
        {loading && <ActivityIndicator size="large" color={colors.accent} />}
        {error && (
          <TouchableOpacity onPress={() => cargar(true)}>
            <Text style={styles.error}>{error} (tocar para reintentar)</Text>
          </TouchableOpacity>
        )}
        {!loading && !error && pedidos.length === 0 && (
          <Text style={styles.muted}>No tienes pedidos activos.</Text>
        )}
        <FlatList
          data={pedidos}
          keyExtractor={(p) => String(p.id_pedido)}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => {
            const listo = entregable(item.estado.nombre_estado);
            return (
              <View style={[styles.card, listo && styles.cardListo]}>
                <View style={styles.cardHead}>
                  <Text style={styles.mesa}>Mesa {item.mesa.numero_mesa}</Text>
                  <Text style={styles.meta}>
                    #{item.id_pedido} · hace {minutosDesde(item.fecha_pedido)} min
                  </Text>
                </View>
                <Badge
                  label={listo ? "Listo para entregar" : item.estado.nombre_estado}
                  variant={BADGE_DE[item.estado.nombre_estado] ?? "warn"}
                />
                <View style={styles.lineas}>
                  {item.detalle.map((d, i) => (
                    <Text key={i} style={styles.linea}>
                      {d.cantidad} × {d.producto.nombre_producto}
                    </Text>
                  ))}
                </View>
                {listo && <PrimaryButton title="Marcar entregado" onPress={() => entregar(item)} />}
              </View>
            );
          }}
        />
      </View>
      <BottomNav items={NAV_MESERO} active="pedidos" onPress={(k) => onNavPress(NAV_MESERO, k, logout)} />
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
    gap: spacing.sm,
    ...cardShadow,
  },
  cardListo: { borderWidth: 2, borderColor: colors.okFg },
  cardHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  mesa: { fontFamily: fonts.title, fontSize: 17, color: colors.coffee900 },
  meta: { fontFamily: fonts.body, color: colors.muted, fontSize: 12.5 },
  lineas: { gap: 2 },
  linea: { fontFamily: fonts.body, fontSize: 14, color: colors.coffee700 },
  muted: { fontFamily: fonts.body, color: colors.muted, textAlign: "center", marginVertical: 16 },
  error: { fontFamily: fonts.medium, color: colors.error, textAlign: "center", marginVertical: 8 },
});
