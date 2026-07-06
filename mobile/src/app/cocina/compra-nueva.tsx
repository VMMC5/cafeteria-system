import { router } from "expo-router";
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
  crearCompra,
  getInsumos,
  getProveedores,
  Insumo,
  Proveedor,
} from "@/api/client";
import { compraTotal, compraValida, lineaCompraValida } from "@/lib/compras";
import { useAuth } from "@/store/auth";

type LineaLocal = {
  id_insumo: number;
  nombre: string;
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

  function agregarLinea() {
    if (!puedeAgregar || insumoSel === null) return;
    const insumo = insumos.find((i) => i.id_insumo === insumoSel);
    setLineas([
      ...lineas,
      {
        id_insumo: insumoSel,
        nombre: insumo ? insumo.nombre_insumo : String(insumoSel),
        cantidad: Number(cantidadTxt),
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
        <ActivityIndicator size="large" color="#2b6cb0" />
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
          {proveedores.map((p) => {
            const sel = provSel === p.id_proveedor;
            return (
              <TouchableOpacity
                key={p.id_proveedor}
                style={[styles.chip, sel && styles.chipSel]}
                onPress={() => setProvSel(p.id_proveedor)}
              >
                <Text style={[styles.chipTxt, sel && styles.chipTxtSel]}>
                  {p.nombre_proveedor}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        <Text style={styles.label}>Insumo</Text>
        <View style={styles.chips}>
          {insumos.map((i) => {
            const sel = insumoSel === i.id_insumo;
            return (
              <TouchableOpacity
                key={i.id_insumo}
                style={[styles.chip, sel && styles.chipSel]}
                onPress={() => setInsumoSel(i.id_insumo)}
              >
                <Text style={[styles.chipTxt, sel && styles.chipTxtSel]}>
                  {i.nombre_insumo}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
        <View style={styles.linea}>
          <TextInput
            style={[styles.input, { flex: 1 }]}
            keyboardType="numeric"
            value={cantidadTxt}
            onChangeText={setCantidadTxt}
            placeholder="Cantidad"
          />
          <TextInput
            style={[styles.input, { flex: 1 }]}
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
              {l.cantidad} × {l.nombre}
            </Text>
            <Text style={styles.rowV}>
              ${(l.cantidad * l.costo_unitario).toFixed(2)}
            </Text>
          </View>
        ))}
        <Text style={styles.total}>Total: ${total.toFixed(2)}</Text>

        <Text style={styles.label}>Folio de factura (opcional)</Text>
        <TextInput
          style={styles.input}
          value={folio}
          onChangeText={setFolio}
          placeholder="F-000"
        />
      </ScrollView>
      <TouchableOpacity
        style={[styles.btn, (!puedeRegistrar || guardando) && styles.btnDisabled]}
        disabled={!puedeRegistrar || guardando}
        onPress={registrar}
      >
        {guardando ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.btnTxt}>Registrar compra</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f4f5f7", padding: 16 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12 },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 24,
    marginBottom: 8,
  },
  title: { fontSize: 20, fontWeight: "700", color: "#2d3748" },
  link: { color: "#2b6cb0", fontWeight: "600" },
  label: { fontWeight: "600", color: "#4a5568", marginTop: 12, marginBottom: 6 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  chipSel: { backgroundColor: "#2b6cb0", borderColor: "#2b6cb0" },
  chipTxt: { color: "#2d3748" },
  chipTxtSel: { color: "#fff", fontWeight: "700" },
  linea: { flexDirection: "row", gap: 8, alignItems: "center", marginTop: 8 },
  input: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
  },
  add: {
    width: 44,
    height: 44,
    borderRadius: 8,
    backgroundColor: "#2b6cb0",
    alignItems: "center",
    justifyContent: "center",
  },
  addDisabled: { backgroundColor: "#a0aec0" },
  addTxt: { color: "#fff", fontSize: 22, fontWeight: "700" },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    backgroundColor: "#fff",
    borderRadius: 8,
    padding: 10,
    marginTop: 6,
  },
  rowL: { color: "#2d3748" },
  rowV: { color: "#2d3748", fontWeight: "600" },
  total: {
    fontSize: 18,
    fontWeight: "700",
    color: "#2d3748",
    textAlign: "right",
    marginTop: 12,
  },
  btn: {
    backgroundColor: "#2b6cb0",
    padding: 16,
    borderRadius: 8,
    alignItems: "center",
  },
  btnDisabled: { backgroundColor: "#a0aec0" },
  btnTxt: { color: "#fff", fontWeight: "700", fontSize: 16 },
  errorTxt: { color: "#c53030", textAlign: "center" },
});
