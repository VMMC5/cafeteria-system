import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
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

import {
  cobrarVenta,
  getMetodosPago,
  getPedido,
  MetodoPago,
  Pedido,
  Venta,
} from "@/api/client";
import { cambio, puedeCobrar } from "@/lib/caja";
import { money } from "@/lib/format";
import { useAuth } from "@/store/auth";

function Row({
  label,
  value,
  bold,
}: {
  label: string;
  value: number | string;
  bold?: boolean;
}) {
  return (
    <View style={styles.row}>
      <Text style={[styles.rowL, bold && styles.bold]}>{label}</Text>
      <Text style={[styles.rowV, bold && styles.bold]}>{money(value)}</Text>
    </View>
  );
}

export default function Cobro() {
  const access = useAuth((s) => s.accessToken);
  const { id_pedido } = useLocalSearchParams<{ id_pedido: string }>();
  const pid = Number(id_pedido);
  const [pedido, setPedido] = useState<Pedido | null>(null);
  const [metodos, setMetodos] = useState<MetodoPago[]>([]);
  const [metodoSel, setMetodoSel] = useState<number | null>(null);
  const [recibidoTxt, setRecibidoTxt] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cobrando, setCobrando] = useState(false);
  const [venta, setVenta] = useState<Venta | null>(null);

  useEffect(() => {
    if (!access) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [p, ms] = await Promise.all([
          getPedido(access, pid),
          getMetodosPago(access),
        ]);
        setPedido(p);
        setMetodos(ms);
        if (ms.length > 0) setMetodoSel(ms[0].id_metodo_pago);
      } catch {
        setError("No se pudo cargar el cobro.");
      } finally {
        setLoading(false);
      }
    })();
  }, [access, pid]);

  const total = Number(pedido?.total ?? 0);
  const recibido = Number(recibidoTxt) || 0;
  const habilitado = metodoSel !== null && puedeCobrar(recibido, total);

  async function confirmar() {
    if (!access || metodoSel === null || !habilitado) return;
    setCobrando(true);
    try {
      const v = await cobrarVenta(access, pid, [
        { id_metodo_pago: metodoSel, monto: recibido },
      ]);
      setVenta(v);
    } catch (e: any) {
      const msg =
        e?.response?.status === 409
          ? "El pedido ya no está disponible para cobro."
          : "No se pudo cobrar.";
      Alert.alert("Error", msg, [
        { text: "OK", onPress: () => router.replace("/caja" as any) },
      ]);
    } finally {
      setCobrando(false);
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2b6cb0" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorTxt}>{error}</Text>
        <TouchableOpacity onPress={() => router.replace("/caja" as any)}>
          <Text style={styles.link}>Volver</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (venta) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Comprobante</Text>
        <View style={styles.ticket}>
          <Text style={styles.folio}>Folio {venta.folio}</Text>
          <Row label="Subtotal" value={venta.subtotal} />
          <Row label="IVA" value={venta.iva} />
          <Row label="Total" value={venta.total} bold />
          <View style={styles.sep} />
          {venta.pagos.map((pg) => (
            <Row key={pg.id_pago} label={pg.metodo.nombre_metodo} value={pg.monto} />
          ))}
          <Row label="Cambio" value={venta.cambio} bold />
        </View>
        <TouchableOpacity
          style={styles.btn}
          onPress={() => router.replace("/caja" as any)}
        >
          <Text style={styles.btnTxt}>Terminar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Cobro — Mesa {pedido?.mesa.numero_mesa}</Text>
      <ScrollView>
        {pedido?.detalle.map((d, i) => (
          <Text key={i} style={styles.linea}>
            {d.cantidad} × {d.producto.nombre_producto}
          </Text>
        ))}
        <Text style={styles.total}>Total: ${total.toFixed(2)}</Text>

        <Text style={styles.label}>Método de pago</Text>
        <View style={styles.chips}>
          {metodos.map((m) => {
            const sel = metodoSel === m.id_metodo_pago;
            return (
              <TouchableOpacity
                key={m.id_metodo_pago}
                style={[styles.chip, sel && styles.chipSel]}
                onPress={() => setMetodoSel(m.id_metodo_pago)}
              >
                <Text style={[styles.chipTxt, sel && styles.chipTxtSel]}>
                  {m.nombre_metodo}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        <Text style={styles.label}>Monto recibido</Text>
        <TextInput
          style={styles.input}
          keyboardType="numeric"
          value={recibidoTxt}
          onChangeText={setRecibidoTxt}
          placeholder="0.00"
        />
        <Text style={styles.cambio}>Cambio: ${cambio(recibido, total).toFixed(2)}</Text>
      </ScrollView>
      <TouchableOpacity
        style={[styles.btn, (!habilitado || cobrando) && styles.btnDisabled]}
        disabled={!habilitado || cobrando}
        onPress={confirmar}
      >
        {cobrando ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.btnTxt}>Confirmar cobro</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f4f5f7", padding: 16 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12 },
  title: {
    fontSize: 20,
    fontWeight: "700",
    color: "#2d3748",
    marginTop: 24,
    marginBottom: 12,
  },
  linea: { color: "#2d3748", paddingVertical: 2 },
  total: {
    fontSize: 18,
    fontWeight: "700",
    color: "#2d3748",
    textAlign: "right",
    marginVertical: 12,
  },
  label: { fontWeight: "600", color: "#4a5568", marginTop: 8, marginBottom: 6 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  chipSel: { backgroundColor: "#2b6cb0", borderColor: "#2b6cb0" },
  chipTxt: { color: "#2d3748" },
  chipTxtSel: { color: "#fff", fontWeight: "700" },
  input: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
  },
  cambio: {
    fontSize: 16,
    fontWeight: "700",
    color: "#22543d",
    marginTop: 10,
    textAlign: "right",
  },
  ticket: { backgroundColor: "#fff", borderRadius: 12, padding: 16, gap: 6 },
  folio: { fontWeight: "700", color: "#2d3748", marginBottom: 6 },
  row: { flexDirection: "row", justifyContent: "space-between" },
  rowL: { color: "#4a5568" },
  rowV: { color: "#2d3748" },
  bold: { fontWeight: "700" },
  sep: { height: 1, backgroundColor: "#e2e8f0", marginVertical: 6 },
  btn: {
    backgroundColor: "#2b6cb0",
    padding: 16,
    borderRadius: 8,
    alignItems: "center",
  },
  btnDisabled: { backgroundColor: "#a0aec0" },
  btnTxt: { color: "#fff", fontWeight: "700", fontSize: 16 },
  errorTxt: { color: "#c53030", textAlign: "center" },
  link: { color: "#2b6cb0", fontWeight: "600" },
});
