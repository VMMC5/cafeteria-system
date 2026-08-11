import * as Print from "expo-print";
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
import { ticketHtml } from "@/lib/ticket";
import { useAuth } from "@/store/auth";
import { cardShadow, colors, fonts, radius, sizes, spacing } from "@/theme";

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

  async function imprimir(v: Venta) {
    try {
      await Print.printAsync({ html: ticketHtml(v, pedido) });
    } catch {
      // Cancelar el diálogo de impresión también rechaza: no es un error real.
    }
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
        <ActivityIndicator size="large" color={colors.accent} />
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
    const fecha = new Date(venta.fecha_venta).toLocaleString("es-MX", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Comprobante</Text>
        <ScrollView>
          <View style={styles.ticket}>
            <View style={styles.ticketHead}>
              <Text style={styles.ticketBrand}>
                Cafetería <Text style={styles.ticketBrandEm}>Aroma</Text>
              </Text>
              <Text style={styles.ticketMeta}>Folio {venta.folio}</Text>
              <Text style={styles.ticketMeta}>{fecha}</Text>
              {pedido && <Text style={styles.ticketMeta}>Mesa {pedido.mesa.numero_mesa}</Text>}
            </View>
            <View style={styles.sep} />
            {pedido?.detalle.map((d, i) => (
              <View key={i} style={styles.itemRow}>
                <Text style={styles.itemName} numberOfLines={1}>
                  {d.producto.nombre_producto}
                </Text>
                <Text style={styles.itemQty}>
                  {d.cantidad} × {money(d.precio_unitario)}
                </Text>
                <Text style={styles.itemTotal}>{money(d.subtotal)}</Text>
              </View>
            ))}
            <View style={styles.sep} />
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
            <Text style={styles.ticketGracias}>¡Gracias por su visita!</Text>
          </View>
        </ScrollView>
        <TouchableOpacity style={styles.btnOutline} onPress={() => imprimir(venta)}>
          <Text style={styles.btnOutlineTxt}>Imprimir Ticket</Text>
        </TouchableOpacity>
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
          <ActivityIndicator color={colors.onAccent} />
        ) : (
          <Text style={styles.btnTxt}>Confirmar cobro</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.cream, padding: spacing.screen },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    backgroundColor: colors.cream,
  },
  title: {
    fontFamily: fonts.title,
    fontSize: 22,
    color: colors.coffee900,
    marginTop: 24,
    marginBottom: spacing.md,
  },
  linea: { fontFamily: fonts.body, color: colors.coffee700, paddingVertical: 2 },
  total: {
    fontFamily: fonts.title,
    fontSize: 18,
    color: colors.coffee900,
    textAlign: "right",
    marginVertical: spacing.md,
  },
  label: { fontFamily: fonts.semibold, fontSize: 13, color: colors.coffee700 },
  lineaPago: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.card,
    padding: spacing.md,
    marginBottom: spacing.sm + 2,
    gap: spacing.sm,
    ...cardShadow,
  },
  lineaHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  quitar: { color: colors.error, fontSize: 16, fontFamily: fonts.bold, padding: 4 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: {
    borderWidth: 1.5,
    borderColor: colors.inputBorder,
    borderRadius: radius.pill,
    paddingHorizontal: 15,
    paddingVertical: 10,
  },
  chipSel: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipTxt: { fontFamily: fonts.semibold, fontSize: 13, color: colors.coffee700 },
  chipTxtSel: { color: colors.onAccent, fontFamily: fonts.bold },
  input: {
    backgroundColor: colors.card,
    borderWidth: 1.5,
    borderColor: colors.inputBorder,
    borderRadius: radius.input,
    height: sizes.input,
    paddingHorizontal: 14,
    fontSize: 15,
    fontFamily: fonts.body,
    color: colors.coffee900,
  },
  agregar: {
    color: colors.accent,
    fontFamily: fonts.bold,
    paddingVertical: spacing.sm,
    marginBottom: 4,
  },
  resumen: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.card,
    padding: spacing.md,
    gap: 6,
    marginBottom: spacing.sm,
    ...cardShadow,
  },
  aviso: { fontFamily: fonts.medium, color: colors.warnFg, marginBottom: spacing.sm, textAlign: "right" },
  ticket: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardLg,
    padding: spacing.lg,
    gap: 6,
    ...cardShadow,
  },
  ticketHead: { alignItems: "center", gap: 2, marginBottom: 4 },
  ticketBrand: { fontFamily: fonts.title, fontSize: 19, color: colors.coffee900 },
  ticketBrandEm: { fontFamily: fonts.titleItalic, color: colors.accent },
  ticketMeta: { fontFamily: fonts.body, fontSize: 12.5, color: colors.muted },
  itemRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  itemName: { flex: 1, fontFamily: fonts.semibold, fontSize: 13.5, color: colors.coffee900 },
  itemQty: { fontFamily: fonts.body, fontSize: 12.5, color: colors.muted },
  itemTotal: {
    minWidth: 64,
    textAlign: "right",
    fontFamily: fonts.body,
    fontSize: 13.5,
    color: colors.coffee900,
  },
  ticketGracias: {
    fontFamily: fonts.titleItalic,
    fontSize: 13,
    color: colors.muted,
    textAlign: "center",
    marginTop: spacing.sm,
  },
  row: { flexDirection: "row", justifyContent: "space-between" },
  rowL: { fontFamily: fonts.body, color: colors.coffee700 },
  rowV: { fontFamily: fonts.body, color: colors.coffee900 },
  bold: { fontFamily: fonts.bold },
  sep: { height: 1, backgroundColor: colors.border, marginVertical: 6 },
  btn: {
    backgroundColor: colors.accent,
    height: sizes.button,
    borderRadius: radius.button,
    alignItems: "center",
    justifyContent: "center",
    marginTop: spacing.sm,
  },
  btnOutline: {
    height: sizes.button,
    borderRadius: radius.button,
    borderWidth: 1.5,
    borderColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
    marginTop: spacing.md,
  },
  btnOutlineTxt: { color: colors.accent, fontFamily: fonts.bold, fontSize: 15.5 },
  btnDisabled: { backgroundColor: colors.disabled },
  btnTxt: { color: colors.onAccent, fontFamily: fonts.bold, fontSize: 15.5 },
  errorTxt: { fontFamily: fonts.medium, color: colors.error, textAlign: "center" },
  link: { fontFamily: fonts.semibold, color: colors.accent },
});
