import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { getProductos, Producto } from "@/api/client";
import { filtrarProductos } from "@/lib/recetas";
import { useAuth } from "@/store/auth";

export default function Recetas() {
  const access = useAuth((s) => s.accessToken);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    if (!access) return;
    setLoading(true);
    setError(null);
    try {
      setProductos(await getProductos(access));
    } catch {
      setError("No se pudieron cargar los productos.");
    } finally {
      setLoading(false);
    }
  }, [access]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const visibles = filtrarProductos(productos, query);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.replace("/cocina" as any)}>
          <Text style={styles.link}>‹ Cocina</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Recetas</Text>
        <View style={{ width: 60 }} />
      </View>

      <TextInput
        style={styles.buscador}
        value={query}
        onChangeText={setQuery}
        placeholder="Buscar producto"
        autoCorrect={false}
      />

      {loading && <ActivityIndicator size="large" color="#2b6cb0" />}
      {error && (
        <TouchableOpacity onPress={cargar}>
          <Text style={styles.error}>{error} (tocar para reintentar)</Text>
        </TouchableOpacity>
      )}
      <FlatList
        data={visibles}
        keyExtractor={(p) => String(p.id_producto)}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !loading ? <Text style={styles.muted}>No hay productos.</Text> : null
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() =>
              router.push(
                `/cocina/receta-detalle?id_producto=${item.id_producto}&nombre=${encodeURIComponent(
                  item.nombre_producto
                )}` as any
              )
            }
          >
            <Text style={styles.nombre}>{item.nombre_producto}</Text>
            <Text style={styles.chevron}>›</Text>
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
  title: { fontSize: 20, fontWeight: "700", color: "#2d3748" },
  link: { color: "#2b6cb0", fontWeight: "600" },
  buscador: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
  },
  list: { gap: 10, paddingBottom: 24 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
  },
  nombre: { fontSize: 16, fontWeight: "700", color: "#2d3748", flex: 1 },
  chevron: { fontSize: 22, color: "#a0aec0" },
  muted: { color: "#718096", textAlign: "center", marginVertical: 16 },
  error: { color: "#c53030", textAlign: "center", marginVertical: 8 },
});
