import { router } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { crearPedido } from "@/api/client";
import { useAuth } from "@/store/auth";
import { cartTotal, toPayload, useCart } from "@/store/cart";

export default function Carrito() {
  const access = useAuth((s) => s.accessToken);
  const cart = useCart();
  const [enviando, setEnviando] = useState(false);
  const total = cartTotal(cart.items);
  const vacio = cart.items.length === 0;

  async function confirmar() {
    if (!access || vacio) return;
    setEnviando(true);
    try {
      await crearPedido(access, toPayload(useCart.getState()));
      cart.clear();
      Alert.alert("Pedido enviado", "El pedido se envió a cocina.");
      router.replace("/mesero/mesas" as any);
    } catch (e: any) {
      const msg =
        e?.response?.status === 409
          ? "La mesa ya no está disponible."
          : "No se pudo enviar el pedido.";
      Alert.alert("Error", msg);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Pedido — Mesa {cart.mesa_numero ?? ""}</Text>
      <ScrollView>
        {cart.items.map((it) => (
          <View key={it.producto.id_producto} style={styles.row}>
            <Text style={styles.nombre}>{it.producto.nombre_producto}</Text>
            <View style={styles.stepper}>
              <TouchableOpacity
                style={styles.step}
                onPress={() => cart.decItem(it.producto.id_producto)}
              >
                <Text style={styles.stepTxt}>−</Text>
              </TouchableOpacity>
              <Text style={styles.qty}>{it.cantidad}</Text>
              <TouchableOpacity style={styles.step} onPress={() => cart.addItem(it.producto)}>
                <Text style={styles.stepTxt}>+</Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.sub}>
              ${(it.cantidad * it.producto.precio_venta).toFixed(2)}
            </Text>
          </View>
        ))}
        {vacio && <Text style={styles.muted}>El carrito está vacío.</Text>}
        <TextInput
          style={styles.obs}
          placeholder="Observaciones del pedido"
          value={cart.observaciones}
          onChangeText={cart.setObservaciones}
        />
      </ScrollView>
      <Text style={styles.total}>Total: ${total.toFixed(2)}</Text>
      <TouchableOpacity
        style={[styles.btn, (vacio || enviando) && styles.btnDisabled]}
        disabled={vacio || enviando}
        onPress={confirmar}
      >
        {enviando ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.btnTxt}>Confirmar pedido</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f4f5f7", padding: 16 },
  title: {
    fontSize: 20,
    fontWeight: "700",
    color: "#2d3748",
    marginTop: 24,
    marginBottom: 12,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    gap: 8,
  },
  nombre: { flex: 1, color: "#2d3748" },
  stepper: { flexDirection: "row", alignItems: "center", gap: 10 },
  step: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: "#2b6cb0",
    alignItems: "center",
    justifyContent: "center",
  },
  stepTxt: { color: "#fff", fontSize: 18, fontWeight: "700" },
  qty: { minWidth: 20, textAlign: "center" },
  sub: { minWidth: 64, textAlign: "right", color: "#2d3748", fontWeight: "600" },
  muted: { color: "#718096", textAlign: "center", marginVertical: 16 },
  obs: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 8,
    padding: 12,
    marginTop: 8,
  },
  total: {
    fontSize: 18,
    fontWeight: "700",
    color: "#2d3748",
    textAlign: "right",
    marginVertical: 12,
  },
  btn: { backgroundColor: "#2b6cb0", padding: 16, borderRadius: 8, alignItems: "center" },
  btnDisabled: { backgroundColor: "#a0aec0" },
  btnTxt: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
