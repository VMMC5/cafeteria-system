import { router } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { crearPedido } from "@/api/client";
import { money } from "@/lib/format";
import { useAuth } from "@/store/auth";
import { cartTotal, toPayload, useCart } from "@/store/cart";
import { cardShadow, colors, fonts, radius, spacing } from "@/theme";
import { Input, PrimaryButton, Stepper } from "@/ui";

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
      <TouchableOpacity onPress={() => router.back()} hitSlop={10}>
        <Text style={styles.back}>‹ Menú</Text>
      </TouchableOpacity>
      <Text style={styles.title}>Pedido — Mesa {cart.mesa_numero ?? ""}</Text>
      <ScrollView>
        {cart.items.map((it) => (
          <View key={it.producto.id_producto} style={styles.row}>
            <Text style={styles.nombre}>{it.producto.nombre_producto}</Text>
            <Stepper
              value={it.cantidad}
              onRemove={() => cart.decItem(it.producto.id_producto)}
              onAdd={() => cart.addItem(it.producto)}
            />
            <Text style={styles.sub}>{money(it.cantidad * it.producto.precio_venta)}</Text>
          </View>
        ))}
        {vacio && <Text style={styles.muted}>El carrito está vacío.</Text>}
        <Input
          placeholder="Observaciones del pedido"
          value={cart.observaciones}
          onChangeText={cart.setObservaciones}
          style={styles.obs}
        />
      </ScrollView>
      <Text style={styles.total}>
        Total: <Text style={styles.totalNum}>{money(total)}</Text>
      </Text>
      {enviando ? (
        <View style={styles.loadingBtn}>
          <ActivityIndicator color={colors.onAccent} />
        </View>
      ) : (
        <PrimaryButton title="Confirmar pedido" onPress={confirmar} disabled={vacio} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.cream, padding: spacing.screen },
  back: { fontFamily: fonts.semibold, fontSize: 14, color: colors.accent, marginTop: 24 },
  title: {
    fontFamily: fonts.title,
    fontSize: 24,
    color: colors.coffee900,
    marginTop: 4,
    marginBottom: spacing.md,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    borderRadius: radius.card,
    marginBottom: spacing.sm,
    gap: spacing.sm,
    ...cardShadow,
  },
  nombre: { flex: 1, fontFamily: fonts.semibold, fontSize: 14.5, color: colors.coffee900 },
  sub: { minWidth: 64, textAlign: "right", fontFamily: fonts.title, fontSize: 15, color: colors.coffee900 },
  muted: { fontFamily: fonts.body, color: colors.muted, textAlign: "center", marginVertical: 16 },
  obs: { marginTop: spacing.sm },
  total: {
    fontFamily: fonts.semibold,
    fontSize: 15,
    color: colors.coffee700,
    textAlign: "right",
    marginVertical: spacing.md,
  },
  totalNum: { fontFamily: fonts.title, fontSize: 19, color: colors.coffee900 },
  loadingBtn: {
    height: 50,
    borderRadius: radius.button,
    backgroundColor: colors.disabled,
    alignItems: "center",
    justifyContent: "center",
  },
});
