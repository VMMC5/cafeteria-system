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
import { useAuth } from "@/store/auth";
import { useCart } from "@/store/cart";

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

  async function salir() {
    await logout();
    router.replace("/login" as any);
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Mesas</Text>
        <TouchableOpacity onPress={salir}>
          <Text style={styles.salir}>Salir</Text>
        </TouchableOpacity>
      </View>
      {loading && <ActivityIndicator size="large" color="#2b6cb0" />}
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
          return (
            <TouchableOpacity
              style={[styles.card, !libre && styles.cardBusy]}
              disabled={!libre}
              onPress={() => elegir(item)}
            >
              <Text style={styles.numero}>Mesa {item.numero_mesa}</Text>
              <Text style={styles.cap}>{item.capacidad} personas</Text>
              <Text style={[styles.badge, libre ? styles.badgeOk : styles.badgeBusy]}>
                {item.estado}
              </Text>
            </TouchableOpacity>
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
  grid: { gap: 12 },
  rowGap: { gap: 12 },
  card: {
    flex: 1,
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 20,
    alignItems: "center",
    gap: 4,
  },
  cardBusy: { opacity: 0.5 },
  numero: { fontSize: 18, fontWeight: "700", color: "#2d3748" },
  cap: { color: "#718096", fontSize: 13 },
  badge: {
    marginTop: 6,
    paddingHorizontal: 10,
    paddingVertical: 2,
    borderRadius: 999,
    fontSize: 12,
    overflow: "hidden",
  },
  badgeOk: { backgroundColor: "#c6f6d5", color: "#22543d" },
  badgeBusy: { backgroundColor: "#fed7d7", color: "#742a2a" },
  error: { color: "#c53030", textAlign: "center", marginVertical: 8 },
});
