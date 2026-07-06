import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { getInsumo, Insumo, registrarMovimiento } from "@/api/client";
import { movimientoValido } from "@/lib/inventario";
import { useAuth } from "@/store/auth";

const TIPOS = ["Entrada", "Salida"];
const MOTIVOS = ["Ajuste", "Merma"];

export default function Ajuste() {
  const access = useAuth((s) => s.accessToken);
  const { id_insumo } = useLocalSearchParams<{ id_insumo: string }>();
  const iid = Number(id_insumo);
  const [insumo, setInsumo] = useState<Insumo | null>(null);
  const [tipo, setTipo] = useState<string | null>("Salida");
  const [motivo, setMotivo] = useState<string | null>("Merma");
  const [cantidadTxt, setCantidadTxt] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    if (!access) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        setInsumo(await getInsumo(access, iid));
      } catch {
        setError("No se pudo cargar el insumo.");
      } finally {
        setLoading(false);
      }
    })();
  }, [access, iid]);

  const habilitado = movimientoValido(tipo, motivo, cantidadTxt);

  async function registrar() {
    if (!access || tipo === null || motivo === null || !habilitado) return;
    setGuardando(true);
    try {
      const actualizado = await registrarMovimiento(access, iid, {
        tipo,
        motivo,
        cantidad: Number(cantidadTxt),
      });
      setInsumo(actualizado);
      setCantidadTxt("");
      Alert.alert(
        "Listo",
        `Stock actualizado: ${actualizado.stock_actual} ${actualizado.unidad.abreviatura}`
      );
    } catch (e: any) {
      const msg =
        e?.response?.status === 422
          ? "Cantidad inválida (¿supera el stock?)."
          : "No se pudo registrar el movimiento.";
      Alert.alert("Error", msg);
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

  if (error || !insumo) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorTxt}>{error ?? "Insumo no encontrado."}</Text>
        <TouchableOpacity onPress={() => router.replace("/cocina/inventario" as any)}>
          <Text style={styles.link}>Volver</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.replace("/cocina/inventario" as any)}>
          <Text style={styles.link}>‹ Inventario</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Ajuste</Text>
        <View style={{ width: 80 }} />
      </View>
      <Text style={styles.nombre}>{insumo.nombre_insumo}</Text>
      <Text style={styles.stock}>
        Stock: {insumo.stock_actual} {insumo.unidad.abreviatura}
      </Text>

      <Text style={styles.label}>Tipo</Text>
      <View style={styles.chips}>
        {TIPOS.map((t) => (
          <TouchableOpacity
            key={t}
            style={[styles.chip, tipo === t && styles.chipSel]}
            onPress={() => setTipo(t)}
          >
            <Text style={[styles.chipTxt, tipo === t && styles.chipTxtSel]}>{t}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>Motivo</Text>
      <View style={styles.chips}>
        {MOTIVOS.map((m) => (
          <TouchableOpacity
            key={m}
            style={[styles.chip, motivo === m && styles.chipSel]}
            onPress={() => setMotivo(m)}
          >
            <Text style={[styles.chipTxt, motivo === m && styles.chipTxtSel]}>{m}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>Cantidad</Text>
      <TextInput
        style={styles.input}
        keyboardType="numeric"
        value={cantidadTxt}
        onChangeText={setCantidadTxt}
        placeholder="0"
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
  nombre: { fontSize: 18, fontWeight: "700", color: "#2d3748", marginTop: 8 },
  stock: { color: "#4a5568", marginBottom: 8 },
  label: { fontWeight: "600", color: "#4a5568", marginTop: 12, marginBottom: 6 },
  chips: { flexDirection: "row", gap: 8 },
  chip: {
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 999,
    paddingHorizontal: 16,
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
  btn: {
    backgroundColor: "#2b6cb0",
    padding: 16,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 20,
  },
  btnDisabled: { backgroundColor: "#a0aec0" },
  btnTxt: { color: "#fff", fontWeight: "700", fontSize: 16 },
  errorTxt: { color: "#c53030", textAlign: "center" },
});
