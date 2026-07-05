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
import { minutosDesde } from "@/lib/cocina";
import { entregable, prioridadEstado } from "@/lib/mesero";
import { useAuth } from "@/store/auth";

const POLL_MS = 10000;
const ACTIVOS = ["Pendiente", "En preparación", "Listo"];

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

  async function salir() {
    await logout();
    router.replace("/login" as any);
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.replace("/mesero/mesas" as any)}>
          <Text style={styles.link}>‹ Mesas</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Mis pedidos</Text>
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
              {listo ? (
                <Text style={styles.listoTxt}>¡Listo para entregar!</Text>
              ) : (
                <Text style={styles.badge}>{item.estado.nombre_estado}</Text>
              )}
              {item.detalle.map((d, i) => (
                <Text key={i} style={styles.linea}>
                  {d.cantidad} × {d.producto.nombre_producto}
                </Text>
              ))}
              {listo && (
                <TouchableOpacity style={styles.btn} onPress={() => entregar(item)}>
                  <Text style={styles.btnTxt}>Marcar entregado</Text>
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
  title: { fontSize: 20, fontWeight: "700", color: "#2d3748" },
  link: { color: "#2b6cb0", fontWeight: "600" },
  salir: { color: "#c53030", fontWeight: "600" },
  list: { gap: 12, paddingBottom: 24 },
  card: { backgroundColor: "#fff", borderRadius: 12, padding: 16, gap: 4 },
  cardListo: { borderWidth: 2, borderColor: "#38a169" },
  cardHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  mesa: { fontSize: 18, fontWeight: "700", color: "#2d3748" },
  meta: { color: "#718096", fontSize: 13 },
  badge: { color: "#4a5568", fontSize: 13, marginVertical: 2 },
  listoTxt: { color: "#22543d", fontWeight: "700", marginVertical: 2 },
  linea: { color: "#2d3748" },
  btn: {
    backgroundColor: "#38a169",
    padding: 12,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 8,
  },
  btnTxt: { color: "#fff", fontWeight: "700" },
  muted: { color: "#718096", textAlign: "center", marginVertical: 16 },
  error: { color: "#c53030", textAlign: "center", marginVertical: 8 },
});
