import { router, useFocusEffect } from "expo-router";
import { useCallback, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { cambiarEstadoPedido, getEstados, getPedidos, Pedido } from "@/api/client";
import { accionCocina, minutosDesde } from "@/lib/cocina";
import { useAuth } from "@/store/auth";

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

  async function salir() {
    await logout();
    router.replace("/login" as any);
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Cocina</Text>
        <TouchableOpacity onPress={salir}>
          <Text style={styles.salir}>Salir</Text>
        </TouchableOpacity>
      </View>
      {loading && <ActivityIndicator size="large" color="#2b6cb0" />}
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
          return (
            <View style={styles.card}>
              <View style={styles.cardHead}>
                <Text style={styles.mesa}>Mesa {item.mesa.numero_mesa}</Text>
                <Text style={styles.meta}>
                  #{item.id_pedido} · hace {minutosDesde(item.fecha_pedido)} min
                </Text>
              </View>
              <Text style={[styles.badge, pend ? styles.badgePend : styles.badgePrep]}>
                {item.estado.nombre_estado}
              </Text>
              {item.detalle.map((d, i) => (
                <Text key={i} style={styles.linea}>
                  {d.cantidad} × {d.producto.nombre_producto}
                  {d.observaciones ? `  (${d.observaciones})` : ""}
                </Text>
              ))}
              {item.observaciones ? (
                <Text style={styles.obs}>Nota: {item.observaciones}</Text>
              ) : null}
              {accion && (
                <TouchableOpacity style={styles.btn} onPress={() => avanzar(item)}>
                  <Text style={styles.btnTxt}>{accion.label}</Text>
                </TouchableOpacity>
              )}
            </View>
          );
        }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f4f5f7", padding: 12 },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 24,
    marginBottom: 8,
  },
  title: { fontSize: 24, fontWeight: "700", color: "#2d3748" },
  salir: { color: "#c53030", fontWeight: "600" },
  list: { gap: 12, paddingBottom: 24 },
  card: { backgroundColor: "#fff", borderRadius: 12, padding: 16, gap: 4 },
  cardHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  mesa: { fontSize: 18, fontWeight: "700", color: "#2d3748" },
  meta: { color: "#718096", fontSize: 13 },
  badge: {
    alignSelf: "flex-start",
    marginVertical: 4,
    paddingHorizontal: 10,
    paddingVertical: 2,
    borderRadius: 999,
    fontSize: 12,
    overflow: "hidden",
  },
  badgePend: { backgroundColor: "#feebc8", color: "#7b341e" },
  badgePrep: { backgroundColor: "#bee3f8", color: "#2a4365" },
  linea: { color: "#2d3748" },
  obs: { color: "#718096", fontStyle: "italic" },
  btn: {
    backgroundColor: "#2b6cb0",
    padding: 12,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 8,
  },
  btnTxt: { color: "#fff", fontWeight: "700" },
  muted: { color: "#718096", textAlign: "center", marginVertical: 16 },
  error: { color: "#c53030", textAlign: "center", marginVertical: 8 },
});
