import { router } from "expo-router";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import {
  crearCompra,
  getInsumos,
  getProveedores,
  Insumo,
  Proveedor,
} from "@/api/client";
import { compraTotal, compraValida, lineaCompraValida } from "@/lib/compras";
import { aCantidad } from "@/lib/decimales";
import { cantidad, money } from "@/lib/format";
import { useAuth } from "@/store/auth";
import { colors, fonts, radius, spacing } from "@/theme";
import { Chip, Input } from "@/ui";

type LineaLocal = {
  id_insumo: number;
  nombre: string;
  unidad: string; // abreviatura ("kg", "L", "pza") para leer "5 kg × Café en grano"
  cantidad: number;
  costo_unitario: number;
};

export default function CompraNueva() {
  const access = useAuth((s) => s.accessToken);
  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [insumos, setInsumos] = useState<Insumo[]>([]);
  const [provSel, setProvSel] = useState<number | null>(null);
  const [insumoSel, setInsumoSel] = useState<number | null>(null);
  const [cantidadTxt, setCantidadTxt] = useState("");
  const [costoTxt, setCostoTxt] = useState("");
  const [folio, setFolio] = useState("");
  const [lineas, setLineas] = useState<LineaLocal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (!access) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [provs, ins] = await Promise.all([
          getProveedores(access),
          getInsumos(access),
        ]);
        setProveedores(provs);
        setInsumos(ins);
        if (provs.length > 0) setProvSel(provs[0].id_proveedor);
      } catch {
        setError("No se pudo cargar el formulario.");
      } finally {
        setLoading(false);
      }
    })();
  }, [access]);

  const puedeAgregar = lineaCompraValida(insumoSel, cantidadTxt, costoTxt);
  const puedeRegistrar = compraValida(provSel, lineas);
  const total = compraTotal(lineas);
  const unidadSel = insumos.find((i) => i.id_insumo === insumoSel)?.unidad.abreviatura;

  function agregarLinea() {
    if (!puedeAgregar || insumoSel === null) return;
    const insumo = insumos.find((i) => i.id_insumo === insumoSel);
    setLineas([
      ...lineas,
      {
        id_insumo: insumoSel,
        nombre: insumo ? insumo.nombre_insumo : String(insumoSel),
        unidad: insumo?.unidad.abreviatura ?? "",
        cantidad: aCantidad(cantidadTxt),
        costo_unitario: Number(costoTxt),
      },
    ]);
    setCantidadTxt("");
    setCostoTxt("");
  }

  async function registrar() {
    if (!access || provSel === null || !puedeRegistrar) return;
    setGuardando(true);
    try {
      await crearCompra(access, {
        id_proveedor: provSel,
        folio_factura: folio.trim() === "" ? null : folio.trim(),
        items: lineas.map((l) => ({
          id_insumo: l.id_insumo,
          cantidad: l.cantidad,
          costo_unitario: l.costo_unitario,
        })),
      });
      router.replace("/cocina/compras" as any);
    } catch {
      Alert.alert("Error", "No se pudo registrar la compra.");
    } finally {
      setGuardando(false);
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
        <TouchableOpacity onPress={() => router.replace("/cocina/compras" as any)}>
          <Text style={styles.link}>Volver</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.replace("/cocina/compras" as any)}>
          <Text style={styles.link}>‹ Compras</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Nueva compra</Text>
        <View style={{ width: 70 }} />
      </View>
      <ScrollView>
        <Text style={styles.label}>Proveedor</Text>
        <View style={styles.chips}>
          {proveedores.map((p) => (
            <Chip
              key={p.id_proveedor}
              label={p.nombre_proveedor}
              active={provSel === p.id_proveedor}
              onPress={() => setProvSel(p.id_proveedor)}
            />
          ))}
        </View>

        <Text style={styles.label}>Insumo</Text>
        <View style={styles.chips}>
          {insumos.map((i) => (
            <Chip
              key={i.id_insumo}
              label={i.nombre_insumo}
              active={insumoSel === i.id_insumo}
              onPress={() => setInsumoSel(i.id_insumo)}
            />
          ))}
        </View>
        <View style={styles.linea}>
          <Input
            style={{ flex: 1 }}
            keyboardType="numeric"
            value={cantidadTxt}
            onChangeText={setCantidadTxt}
            placeholder={unidadSel ? `Cantidad (${unidadSel})` : "Cantidad"}
          />
          <Input
            style={{ flex: 1 }}
            keyboardType="numeric"
            value={costoTxt}
            onChangeText={setCostoTxt}
            placeholder="Costo unit."
          />
          <TouchableOpacity
            style={[styles.add, !puedeAgregar && styles.addDisabled]}
            disabled={!puedeAgregar}
            onPress={agregarLinea}
          >
            <Text style={styles.addTxt}>+</Text>
          </TouchableOpacity>
        </View>

        {lineas.map((l, i) => (
          <View key={i} style={styles.row}>
            <Text style={styles.rowL}>
              {cantidad(l.cantidad)}
              {l.unidad ? ` ${l.unidad}` : ""} × {l.nombre}
            </Text>
            <Text style={styles.rowV}>{money(l.cantidad * l.costo_unitario)}</Text>
          </View>
        ))}
        <Text style={styles.total}>Total: {money(total)}</Text>

        <Text style={styles.label}>Folio de factura (opcional)</Text>
        <Input value={folio} onChangeText={setFolio} placeholder="F-000" />
      </ScrollView>
      <TouchableOpacity
        style={[styles.btn, (!puedeRegistrar || guardando) && styles.btnDisabled]}
        disabled={!puedeRegistrar || guardando}
        onPress={registrar}
      >
        {guardando ? (
          <ActivityIndicator color={colors.onAccent} />
        ) : (
          <Text style={styles.btnTxt}>Registrar compra</Text>
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
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 24,
    marginBottom: spacing.sm,
  },
  title: { fontFamily: fonts.title, fontSize: 20, color: colors.coffee900 },
  link: { fontFamily: fonts.semibold, color: colors.accent },
  label: {
    fontFamily: fonts.semibold,
    fontSize: 13,
    color: colors.coffee700,
    marginTop: spacing.md,
    marginBottom: 6,
  },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  linea: { flexDirection: "row", gap: spacing.sm, alignItems: "center", marginTop: spacing.sm },
  add: {
    width: 48,
    height: 48,
    borderRadius: radius.input,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  addDisabled: { backgroundColor: colors.disabled },
  addTxt: { color: colors.onAccent, fontSize: 22, fontFamily: fonts.bold },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.input,
    padding: spacing.md,
    marginTop: 6,
  },
  rowL: { fontFamily: fonts.body, color: colors.coffee900 },
  rowV: { fontFamily: fonts.title, color: colors.coffee900 },
  total: {
    fontFamily: fonts.title,
    fontSize: 18,
    color: colors.coffee900,
    textAlign: "right",
    marginTop: spacing.md,
  },
  btn: {
    backgroundColor: colors.accent,
    height: 50,
    borderRadius: radius.button,
    alignItems: "center",
    justifyContent: "center",
    marginTop: spacing.sm,
  },
  btnDisabled: { backgroundColor: colors.disabled },
  btnTxt: { color: colors.onAccent, fontFamily: fonts.bold, fontSize: 15.5 },
  errorTxt: { fontFamily: fonts.medium, color: colors.error, textAlign: "center" },
});
