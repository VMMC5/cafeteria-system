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
import {
  aPayload,
  cambioPagos,
  excedeNoEfectivo,
  faltante,
  PagoLinea,
  puedeCobrarPagos,
  sumaPagos,
} from "@/lib/caja";
import { money } from "@/lib/format";
import { useAuth } from "@/store/auth";

type LineaUI = {
  id_metodo_pago: number | null;
  montoTxt: string;
  referencia: string;
};

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
  const [lineas, setLineas] = useState<LineaUI[]>([]);
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
        setLineas([
          {
            id_metodo_pago: ms[0]?.id_metodo_pago ?? null,
            montoTxt: "",
            referencia: "",
          },
        ]);
      } catch {
        setError("No se pudo cargar el cobro.");
      } finally {
        setLoading(false);
      }
    })();
  }, [access, pid]);

  const total = Number(pedido?.total ?? 0);
  const idEfectivo =
    metodos.find((m) => m.nombre_metodo === "Efectivo")?.id_metodo_pago ?? null;

  const parseadas: PagoLinea[] = lineas
    .filter((l) => l.id_metodo_pago !== null)
    .map((l) => ({
      id_metodo_pago: l.id_metodo_pago as number,
      monto: Number(l.montoTxt) || 0,
      referencia: l.referencia,
    }));
  const completas = parseadas.length === lineas.length;
  const habilitado = completas && puedeCobrarPagos(parseadas, total, idEfectivo);
  const avisoExcedente =
    completas && excedeNoEfectivo(parseadas, total, idEfectivo);

  function setLinea(i: number, patch: Partial<LineaUI>) {
    setLineas((ls) => ls.map((l, j) => (j === i ? { ...l, ...patch } : l)));
  }

  function agregarLinea() {
    setLineas((ls) => [
      ...ls,
      {
        id_metodo_pago: metodos[0]?.id_metodo_pago ?? null,
        montoTxt: "",
        referencia: "",
      },
    ]);
  }

  function quitarLinea(i: number) {
    setLineas((ls) => ls.filter((_, j) => j !== i));
  }

  async function confirmar() {
    if (!access || !habilitado) return;
    setCobrando(true);
    try {
      const v = await cobrarVenta(access, pid, aPayload(parseadas));
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
            <Row
              key={pg.id_pago}
              label={
                pg.metodo.nombre_metodo +
                (pg.referencia ? ` (${pg.referencia})` : "")
              }
              value={pg.monto}
            />
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
        <Text style={styles.total}>Total: {money(total)}</Text>

        {lineas.map((l, i) => (
          <View key={i} style={styles.lineaPago}>
            <View style={styles.lineaHead}>
              <Text style={styles.label}>Pago {i + 1}</Text>
              {lineas.length > 1 && (
                <TouchableOpacity
                  onPress={() => quitarLinea(i)}
                  accessibilityLabel={`Quitar pago ${i + 1}`}
                >
                  <Text style={styles.quitar}>✕</Text>
                </TouchableOpacity>
              )}
            </View>
            <View style={styles.chips}>
              {metodos.map((m) => {
                const sel = l.id_metodo_pago === m.id_metodo_pago;
                return (
                  <TouchableOpacity
                    key={m.id_metodo_pago}
                    style={[styles.chip, sel && styles.chipSel]}
                    onPress={() =>
                      setLinea(i, {
                        id_metodo_pago: m.id_metodo_pago,
                        referencia: m.id_metodo_pago === idEfectivo ? "" : l.referencia,
                      })
                    }
                  >
                    <Text style={[styles.chipTxt, sel && styles.chipTxtSel]}>
                      {m.nombre_metodo}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
            <TextInput
              style={styles.input}
              keyboardType="numeric"
              value={l.montoTxt}
              onChangeText={(t) => setLinea(i, { montoTxt: t })}
              placeholder="0.00"
            />
            {l.id_metodo_pago !== idEfectivo && (
              <TextInput
                style={styles.input}
                value={l.referencia}
                onChangeText={(t) => setLinea(i, { referencia: t })}
                placeholder="Referencia (opcional)"
              />
            )}
          </View>
        ))}

        <TouchableOpacity onPress={agregarLinea}>
          <Text style={styles.agregar}>+ Agregar pago</Text>
        </TouchableOpacity>

        <View style={styles.resumen}>
          <Row label="Total" value={total} bold />
          <Row label="Pagado" value={sumaPagos(parseadas)} />
          <Row label="Falta" value={faltante(parseadas, total)} />
          <Row label="Cambio" value={cambioPagos(parseadas, total)} bold />
        </View>
        {avisoExcedente && (
          <Text style={styles.aviso}>El excedente solo se permite en Efectivo</Text>
        )}
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
  label: { fontWeight: "600", color: "#4a5568" },
  lineaPago: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 12,
    marginBottom: 10,
    gap: 8,
  },
  lineaHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  quitar: { color: "#c53030", fontSize: 16, fontWeight: "700", padding: 4 },
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
    backgroundColor: "#f7fafc",
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
  },
  agregar: {
    color: "#2b6cb0",
    fontWeight: "700",
    paddingVertical: 8,
    marginBottom: 4,
  },
  resumen: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 12,
    gap: 6,
    marginBottom: 8,
  },
  aviso: { color: "#c05621", marginBottom: 8, textAlign: "right" },
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
