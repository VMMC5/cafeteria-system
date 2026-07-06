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

import { getInsumos, Insumo } from "@/api/client";
import { stockBajo } from "@/lib/inventario";
import { useAuth } from "@/store/auth";

export default function Inventario() {
  const access = useAuth((s) => s.accessToken);
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
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.replace("/cocina" as any)}>
          <Text style={styles.link}>‹ Cocina</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Inventario</Text>
        <View style={{ width: 60 }} />
      </View>
      {loading && <ActivityIndicator size="large" color="#2b6cb0" />}
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
                  mín. {item.stock_minimo} {item.unidad.abreviatura}
                </Text>
              </View>
              <View style={{ alignItems: "flex-end" }}>
                <Text style={[styles.stock, bajo && styles.stockBajoTxt]}>
                  {item.stock_actual} {item.unidad.abreviatura}
                </Text>
                {bajo && <Text style={styles.alerta}>Stock bajo</Text>}
              </View>
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
  cardBajo: { borderWidth: 2, borderColor: "#e53e3e" },
  nombre: { fontSize: 16, fontWeight: "700", color: "#2d3748" },
  meta: { color: "#718096", fontSize: 13 },
  stock: { fontSize: 16, fontWeight: "700", color: "#2d3748" },
  stockBajoTxt: { color: "#c53030" },
  alerta: { color: "#c53030", fontSize: 12, fontWeight: "600" },
  muted: { color: "#718096", textAlign: "center", marginVertical: 16 },
  error: { color: "#c53030", textAlign: "center", marginVertical: 8 },
});
