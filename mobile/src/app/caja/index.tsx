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

import { getPedidos, Pedido } from "@/api/client";
import { useAuth } from "@/store/auth";

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

  async function salir() {
    await logout();
    router.replace("/login" as any);
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Caja — por cobrar</Text>
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
            <Text style={styles.total}>${item.total.toFixed(2)}</Text>
          </TouchableOpacity>
        )}
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
  title: { fontSize: 22, fontWeight: "700", color: "#2d3748" },
  salir: { color: "#c53030", fontWeight: "600" },
  list: { gap: 12, paddingBottom: 24 },
  card: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
  },
  mesa: { fontSize: 18, fontWeight: "700", color: "#2d3748" },
  meta: { color: "#718096", fontSize: 13 },
  total: { fontSize: 18, fontWeight: "700", color: "#2b6cb0" },
  muted: { color: "#718096", textAlign: "center", marginVertical: 16 },
  error: { color: "#c53030", textAlign: "center", marginVertical: 8 },
});
