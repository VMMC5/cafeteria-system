import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import {
  CategoriaGasto,
  Gasto,
  crearGasto,
  getCategoriasGasto,
  getGastos,
} from "@/api/client";
import { money } from "@/lib/format";
import { gastoValido } from "@/lib/gastos";
import { useAuth } from "@/store/auth";

export default function Gastos() {
  const access = useAuth((s) => s.accessToken);
  const [categorias, setCategorias] = useState<CategoriaGasto[]>([]);
  const [gastos, setGastos] = useState<Gasto[]>([]);
  const [catSel, setCatSel] = useState<number | null>(null);
  const [concepto, setConcepto] = useState("");
  const [montoTxt, setMontoTxt] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  const cargar = useCallback(async () => {
    if (!access) return;
    setLoading(true);
    setError(null);
    try {
      const [cats, gs] = await Promise.all([
        getCategoriasGasto(access),
        getGastos(access),
      ]);
      setCategorias(cats);
      setGastos(gs);
      if (catSel === null && cats.length > 0) setCatSel(cats[0].id_categoria_gasto);
    } catch {
      setError("No se pudieron cargar los gastos.");
    } finally {
      setLoading(false);
    }
  }, [access, catSel]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const habilitado = gastoValido(catSel, concepto, montoTxt);

  async function registrar() {
    if (!access || catSel === null || !habilitado) return;
    setGuardando(true);
    try {
      await crearGasto(access, {
        id_categoria_gasto: catSel,
        concepto: concepto.trim(),
        monto: Number(montoTxt),
      });
      setConcepto("");
      setMontoTxt("");
      const gs = await getGastos(access);
      setGastos(gs);
    } catch {
      Alert.alert("Error", "No se pudo registrar el gasto.");
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

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.replace("/caja" as any)}>
          <Text style={styles.link}>‹ Caja</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Gastos</Text>
        <View style={{ width: 48 }} />
      </View>

      {error && (
        <TouchableOpacity onPress={cargar}>
          <Text style={styles.error}>{error} (tocar para reintentar)</Text>
        </TouchableOpacity>
      )}

      <View style={styles.form}>
        <Text style={styles.label}>Categoría</Text>
        <View style={styles.chips}>
          {categorias.map((c) => {
            const sel = catSel === c.id_categoria_gasto;
            return (
              <TouchableOpacity
                key={c.id_categoria_gasto}
                style={[styles.chip, sel && styles.chipSel]}
                onPress={() => setCatSel(c.id_categoria_gasto)}
              >
                <Text style={[styles.chipTxt, sel && styles.chipTxtSel]}>
                  {c.nombre_categoria}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
        <TextInput
          style={styles.input}
          placeholder="Concepto"
          value={concepto}
          onChangeText={setConcepto}
        />
        <TextInput
          style={styles.input}
          placeholder="Monto"
          keyboardType="numeric"
          value={montoTxt}
          onChangeText={setMontoTxt}
        />
        <TouchableOpacity
          style={[styles.btn, (!habilitado || guardando) && styles.btnDisabled]}
          disabled={!habilitado || guardando}
          onPress={registrar}
        >
          {guardando ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.btnTxt}>Registrar</Text>
          )}
        </TouchableOpacity>
      </View>

      <Text style={styles.subtitle}>Recientes</Text>
      <FlatList
        data={gastos}
        keyExtractor={(g) => String(g.id_gasto)}
        contentContainerStyle={styles.list}
        ListEmptyComponent={<Text style={styles.muted}>Aún no hay gastos.</Text>}
        renderItem={({ item }) => (
          <View style={styles.row}>
            <View style={{ flex: 1 }}>
              <Text style={styles.concepto}>{item.concepto}</Text>
              <Text style={styles.meta}>{item.categoria.nombre_categoria}</Text>
            </View>
            <Text style={styles.monto}>{money(item.monto)}</Text>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f4f5f7", padding: 12 },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 24,
    marginBottom: 8,
  },
  title: { fontSize: 20, fontWeight: "700", color: "#2d3748" },
  link: { color: "#2b6cb0", fontWeight: "600" },
  form: { backgroundColor: "#fff", borderRadius: 12, padding: 16, gap: 8 },
  label: { fontWeight: "600", color: "#4a5568" },
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
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
  },
  btn: {
    backgroundColor: "#2b6cb0",
    padding: 14,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 4,
  },
  btnDisabled: { backgroundColor: "#a0aec0" },
  btnTxt: { color: "#fff", fontWeight: "700", fontSize: 16 },
  subtitle: {
    fontWeight: "700",
    color: "#2d3748",
    marginTop: 16,
    marginBottom: 8,
  },
  list: { gap: 8, paddingBottom: 24 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 8,
    padding: 12,
  },
  concepto: { color: "#2d3748", fontWeight: "600" },
  meta: { color: "#718096", fontSize: 13 },
  monto: { color: "#c53030", fontWeight: "700" },
  muted: { color: "#718096", textAlign: "center", marginVertical: 16 },
  error: { color: "#c53030", textAlign: "center", marginVertical: 8 },
});
