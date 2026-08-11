import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, TouchableOpacity, View, Alert } from "react-native";

import { getInsumo, Insumo, registrarMovimiento } from "@/api/client";
import { aCantidad } from "@/lib/decimales";
import { cantidad } from "@/lib/format";
import { movimientoValido } from "@/lib/inventario";
import { useAuth } from "@/store/auth";
import { colors, fonts, radius, spacing } from "@/theme";
import { Chip, Input } from "@/ui";

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
        cantidad: aCantidad(cantidadTxt),
      });
      setInsumo(actualizado);
      setCantidadTxt("");
      Alert.alert(
        "Listo",
        `Stock actualizado: ${cantidad(actualizado.stock_actual)} ${actualizado.unidad.abreviatura}`
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
        <ActivityIndicator size="large" color={colors.accent} />
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
        Stock: {cantidad(insumo.stock_actual)} {insumo.unidad.abreviatura}
      </Text>

      <Text style={styles.label}>Tipo</Text>
      <View style={styles.chips}>
        {TIPOS.map((t) => (
          <Chip key={t} label={t} active={tipo === t} onPress={() => setTipo(t)} />
        ))}
      </View>

      <Text style={styles.label}>Motivo</Text>
      <View style={styles.chips}>
        {MOTIVOS.map((m) => (
          <Chip key={m} label={m} active={motivo === m} onPress={() => setMotivo(m)} />
        ))}
      </View>

      <Text style={styles.label}>Cantidad</Text>
      <Input
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
          <ActivityIndicator color={colors.onAccent} />
        ) : (
          <Text style={styles.btnTxt}>Registrar</Text>
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
  nombre: { fontFamily: fonts.title, fontSize: 18, color: colors.coffee900, marginTop: spacing.sm },
  stock: { fontFamily: fonts.body, color: colors.coffee700, marginBottom: spacing.sm },
  label: {
    fontFamily: fonts.semibold,
    fontSize: 13,
    color: colors.coffee700,
    marginTop: spacing.md,
    marginBottom: 6,
  },
  chips: { flexDirection: "row", gap: spacing.sm },
  btn: {
    backgroundColor: colors.accent,
    height: 50,
    borderRadius: radius.button,
    alignItems: "center",
    justifyContent: "center",
    marginTop: spacing.xl,
  },
  btnDisabled: { backgroundColor: colors.disabled },
  btnTxt: { color: colors.onAccent, fontFamily: fonts.bold, fontSize: 15.5 },
  errorTxt: { fontFamily: fonts.medium, color: colors.error, textAlign: "center" },
});
