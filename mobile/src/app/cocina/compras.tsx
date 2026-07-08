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

import { Compra, getCompras } from "@/api/client";
import { money } from "@/lib/format";
import { useAuth } from "@/store/auth";

export default function Compras() {
  const access = useAuth((s) => s.accessToken);
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
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.replace("/cocina" as any)}>
          <Text style={styles.link}>‹ Cocina</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Compras</Text>
        <TouchableOpacity onPress={() => router.push("/cocina/compra-nueva" as any)}>
          <Text style={styles.link}>Nueva</Text>
        </TouchableOpacity>
      </View>
      {loading && <ActivityIndicator size="large" color="#2b6cb0" />}
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
  title: { fontSize: 20, fontWeight: "700", color: "#2d3748" },
  link: { color: "#2b6cb0", fontWeight: "600" },
  list: { gap: 10, paddingBottom: 24 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
  },
  prov: { fontSize: 16, fontWeight: "700", color: "#2d3748" },
  meta: { color: "#718096", fontSize: 13 },
  total: { fontSize: 16, fontWeight: "700", color: "#2b6cb0" },
  muted: { color: "#718096", textAlign: "center", marginVertical: 16 },
  error: { color: "#c53030", textAlign: "center", marginVertical: 8 },
});
