import { useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, Alert, FlatList, StyleSheet, Text, TouchableOpacity, View } from "react-native";

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
import { cardShadow, colors, fonts, radius, sizes, spacing } from "@/theme";
import { BottomNav, Chip, Input } from "@/ui";
import { NAV_CAJA, onNavPress } from "@/ui/nav";

export default function Gastos() {
  const access = useAuth((s) => s.accessToken);
  const logout = useAuth((s) => s.logout);
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
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <View style={styles.screen}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>Gastos</Text>
          <Text style={styles.headSub}>Registra egresos de la operación</Text>
        </View>

        {error && (
          <TouchableOpacity onPress={cargar}>
            <Text style={styles.error}>{error} (tocar para reintentar)</Text>
          </TouchableOpacity>
        )}

        <View style={styles.form}>
          <Text style={styles.label}>Categoría</Text>
          <View style={styles.chips}>
            {categorias.map((c) => (
              <Chip
                key={c.id_categoria_gasto}
                label={c.nombre_categoria}
                active={catSel === c.id_categoria_gasto}
                onPress={() => setCatSel(c.id_categoria_gasto)}
              />
            ))}
          </View>
          <Input placeholder="Concepto" value={concepto} onChangeText={setConcepto} />
          <Input
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
              <ActivityIndicator color={colors.onAccent} />
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
      <BottomNav items={NAV_CAJA} active="gastos" onPress={(k) => onNavPress(NAV_CAJA, k, logout)} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.cream },
  container: { flex: 1, padding: spacing.screen },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.cream,
  },
  header: { marginTop: 24, marginBottom: spacing.lg },
  title: { fontFamily: fonts.title, fontSize: 24, color: colors.coffee900 },
  headSub: { fontFamily: fonts.body, fontSize: 14, color: colors.muted, marginTop: 2 },
  form: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardLg,
    padding: spacing.lg,
    gap: spacing.sm + 2,
    ...cardShadow,
  },
  label: { fontFamily: fonts.semibold, fontSize: 13, color: colors.coffee700 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  btn: {
    backgroundColor: colors.accent,
    height: sizes.input,
    borderRadius: radius.button,
    alignItems: "center",
    justifyContent: "center",
    marginTop: 4,
  },
  btnDisabled: { backgroundColor: colors.disabled },
  btnTxt: { color: colors.onAccent, fontFamily: fonts.bold, fontSize: 15.5 },
  subtitle: {
    fontFamily: fonts.bold,
    fontSize: 11.5,
    letterSpacing: 1,
    textTransform: "uppercase",
    color: colors.muted,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  list: { gap: spacing.sm, paddingBottom: spacing.lg },
  row: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.card,
    padding: spacing.md,
    ...cardShadow,
  },
  concepto: { fontFamily: fonts.semibold, color: colors.coffee900 },
  meta: { fontFamily: fonts.body, color: colors.muted, fontSize: 13 },
  monto: { fontFamily: fonts.title, color: colors.error },
  muted: { fontFamily: fonts.body, color: colors.muted, textAlign: "center", marginVertical: 16 },
  error: { fontFamily: fonts.medium, color: colors.error, textAlign: "center", marginVertical: 8 },
});
