import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { Compra, getCompras, getInsumos } from "@/api/client";
import { cantidad, money } from "@/lib/format";
import { useAuth } from "@/store/auth";
import { cardShadow, colors, fonts, radius, spacing } from "@/theme";

export default function CompraDetalle() {
  const access = useAuth((s) => s.accessToken);
  const { id_compra } = useLocalSearchParams<{ id_compra: string }>();
  const cid = Number(id_compra);
  const [compra, setCompra] = useState<Compra | null>(null);
  // La API no expone GET /compras/{id}: se busca en la lista y se cruza con
  // los insumos para mostrar la unidad de cada línea ("5 kg × Café en grano").
  const [unidades, setUnidades] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    if (!access) return;
    setLoading(true);
    setError(null);
    try {
      const [compras, insumos] = await Promise.all([getCompras(access), getInsumos(access)]);
      const encontrada = compras.find((c) => c.id_compra === cid) ?? null;
      if (!encontrada) {
        setError("No se encontró la compra.");
      } else {
        setCompra(encontrada);
        setUnidades(
          Object.fromEntries(insumos.map((i) => [i.id_insumo, i.unidad.abreviatura]))
        );
      }
    } catch {
      setError("No se pudo cargar la compra.");
    } finally {
      setLoading(false);
    }
  }, [access, cid]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  if (error || !compra) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorTxt}>{error ?? "No se encontró la compra."}</Text>
        <TouchableOpacity onPress={cargar}>
          <Text style={styles.link}>Reintentar</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.replace("/cocina/compras" as any)}>
          <Text style={styles.link}>Volver</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const fecha = new Date(compra.fecha_compra).toLocaleString("es-MX", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.replace("/cocina/compras" as any)}>
          <Text style={styles.link}>‹ Compras</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Compra #{compra.id_compra}</Text>
        <View style={{ width: 70 }} />
      </View>
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.card}>
          <Text style={styles.prov}>{compra.proveedor.nombre_proveedor}</Text>
          <Text style={styles.meta}>{fecha}</Text>
          <Text style={styles.meta}>
            {compra.folio_factura ? `Factura ${compra.folio_factura}` : "Sin folio de factura"}
          </Text>
        </View>

        <View style={styles.card}>
          {compra.detalle.map((d) => {
            const abrev = unidades[d.id_insumo] ?? "";
            return (
              <View key={d.id_detalle_compra} style={styles.linea}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.insumo}>{d.insumo.nombre_insumo}</Text>
                  <Text style={styles.meta}>
                    {cantidad(d.cantidad)}
                    {abrev ? ` ${abrev}` : ""} × {money(d.costo_unitario)}
                  </Text>
                </View>
                <Text style={styles.subtotal}>{money(d.subtotal)}</Text>
              </View>
            );
          })}
          <View style={styles.sep} />
          <View style={styles.linea}>
            <Text style={styles.totalLbl}>Total</Text>
            <Text style={styles.totalNum}>{money(compra.total)}</Text>
          </View>
        </View>
      </ScrollView>
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
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 24,
    marginBottom: spacing.md,
  },
  title: { fontFamily: fonts.title, fontSize: 20, color: colors.coffee900 },
  link: { fontFamily: fonts.semibold, color: colors.accent },
  scroll: { gap: spacing.md, paddingBottom: spacing.lg },
  card: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardLg,
    padding: spacing.lg,
    gap: 6,
    ...cardShadow,
  },
  prov: { fontFamily: fonts.title, fontSize: 17, color: colors.coffee900 },
  meta: { fontFamily: fonts.body, fontSize: 13, color: colors.muted },
  linea: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  insumo: { fontFamily: fonts.semibold, fontSize: 14.5, color: colors.coffee900 },
  subtotal: { fontFamily: fonts.title, fontSize: 15, color: colors.coffee900 },
  sep: { height: 1, backgroundColor: colors.border, marginVertical: 6 },
  totalLbl: { flex: 1, fontFamily: fonts.bold, fontSize: 15, color: colors.coffee700 },
  totalNum: { fontFamily: fonts.title, fontSize: 18, color: colors.coffee900 },
  errorTxt: { fontFamily: fonts.medium, color: colors.error, textAlign: "center" },
});
