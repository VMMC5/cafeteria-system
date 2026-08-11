import { useFocusEffect } from "expo-router";
import { useCallback, useRef, useState } from "react";
import { ActivityIndicator, Alert, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { cambiarEstadoPedido, getEstados, getPedidos, Pedido } from "@/api/client";
import { accionCocina, minutosDesde, nivelRetraso } from "@/lib/cocina";
import { useAuth } from "@/store/auth";
import { cardShadow, colors, fonts, radius, spacing } from "@/theme";
import { Badge, BottomNav, PrimaryButton } from "@/ui";
import { NAV_COCINA, onNavPress } from "@/ui/nav";

const POLL_MS = 10000;

export default function Cocina() {
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
        const activos = [
          estadoIds.current["Pendiente"],
          estadoIds.current["En preparación"],
        ].filter((x): x is number => typeof x === "number");
        const lista = await getPedidos(access, { estados: activos });
        lista.sort(
          (a, b) =>
            new Date(a.fecha_pedido).getTime() - new Date(b.fecha_pedido).getTime()
        );
        setPedidos(lista);
      } catch {
        setError("No se pudieron cargar los pedidos.");
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

  async function avanzar(p: Pedido) {
    const accion = accionCocina(p.estado.nombre_estado);
    if (!access || !accion) return;
    const destino = estadoIds.current[accion.destinoNombre];
    if (destino === undefined) return;
    try {
      await cambiarEstadoPedido(access, p.id_pedido, destino);
    } catch {
      Alert.alert("Aviso", "No se pudo actualizar el pedido; se recargó la lista.");
    } finally {
      cargar(false);
    }
  }

  return (
    <View style={styles.screen}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Cocina</Text>
          <Text style={styles.subtitle}>Pedidos por preparar</Text>
        </View>
        {loading && <ActivityIndicator size="large" color={colors.accent} />}
        {error && (
          <TouchableOpacity onPress={() => cargar(true)}>
            <Text style={styles.error}>{error} (tocar para reintentar)</Text>
          </TouchableOpacity>
        )}
        {!loading && !error && pedidos.length === 0 && (
          <Text style={styles.muted}>No hay pedidos activos.</Text>
        )}
        <FlatList
          data={pedidos}
          keyExtractor={(p) => String(p.id_pedido)}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => {
            const accion = accionCocina(item.estado.nombre_estado);
            const pend = item.estado.nombre_estado === "Pendiente";
            const mins = minutosDesde(item.fecha_pedido);
            const nivel = nivelRetraso(mins);
            return (
              <View style={styles.card}>
                <View style={styles.cardHead}>
                  <Text style={styles.mesa}>Mesa {item.mesa.numero_mesa}</Text>
                  <Text
                    style={[
                      styles.meta,
                      nivel === "alerta" && styles.metaAlerta,
                      nivel === "critico" && styles.metaCritico,
                    ]}
                  >
                    #{item.id_pedido} · hace {mins} min
                  </Text>
                </View>
                <Badge label={item.estado.nombre_estado} variant={pend ? "warn" : "busy"} />
                <View style={styles.lineas}>
                  {item.detalle.map((d, i) => (
                    <Text key={i} style={styles.linea}>
                      {d.cantidad} × {d.producto.nombre_producto}
                      {d.observaciones ? `  (${d.observaciones})` : ""}
                    </Text>
                  ))}
                </View>
                {item.observaciones ? (
                  <Text style={styles.obs}>Nota: {item.observaciones}</Text>
                ) : null}
                {accion && <PrimaryButton title={accion.label} onPress={() => avanzar(item)} />}
              </View>
            );
          }}
        />
      </View>
      <BottomNav items={NAV_COCINA} active="pedidos" onPress={(k) => onNavPress(NAV_COCINA, k, logout)} />
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
  cardHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  mesa: { fontFamily: fonts.title, fontSize: 17, color: colors.coffee900 },
  meta: { fontFamily: fonts.body, color: colors.muted, fontSize: 12.5 },
  metaAlerta: { fontFamily: fonts.bold, color: colors.warnFg },
  metaCritico: { fontFamily: fonts.bold, color: colors.error },
  lineas: { gap: 2 },
  linea: { fontFamily: fonts.body, fontSize: 14, color: colors.coffee700 },
  obs: { fontFamily: fonts.body, color: colors.muted, fontStyle: "italic" },
  muted: { fontFamily: fonts.body, color: colors.muted, textAlign: "center", marginVertical: 16 },
  error: { fontFamily: fonts.medium, color: colors.error, textAlign: "center", marginVertical: 8 },
});
