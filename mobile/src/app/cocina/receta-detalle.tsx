import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
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
  addRecetaLinea,
  deleteRecetaLinea,
  getInsumos,
  getReceta,
  Insumo,
  patchRecetaLinea,
  RecetaLinea,
} from "@/api/client";
import { cantidad } from "@/lib/format";
import { aCantidad, cantidadValida, insumosDisponibles } from "@/lib/recetas";
import { useAuth } from "@/store/auth";
import { cardShadow, colors, fonts, radius, sizes, spacing } from "@/theme";

export default function RecetaDetalle() {
  const access = useAuth((s) => s.accessToken);
  const { id_producto, nombre } = useLocalSearchParams<{
    id_producto: string;
    nombre: string;
  }>();
  const pid = Number(id_producto);

  const [receta, setReceta] = useState<RecetaLinea[]>([]);
  const [insumos, setInsumos] = useState<Insumo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  // Edición inline: id de la línea en edición y su texto de cantidad.
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [editTxt, setEditTxt] = useState("");

  // Alta de línea nueva.
  const [nuevoInsumo, setNuevoInsumo] = useState<number | null>(null);
  const [nuevaCant, setNuevaCant] = useState("");

  const cargar = useCallback(async () => {
    if (!access) return;
    setLoading(true);
    setError(null);
    try {
      const [r, i] = await Promise.all([getReceta(access, pid), getInsumos(access)]);
      setReceta(r);
      setInsumos(i);
    } catch {
      setError("No se pudo cargar la receta.");
    } finally {
      setLoading(false);
    }
  }, [access, pid]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  function fallo(e: any, fallback: string) {
    Alert.alert("Error", e?.response?.data?.detail ?? fallback);
  }

  async function guardarEdicion(linea: RecetaLinea) {
    if (!access || !cantidadValida(editTxt)) return;
    setOcupado(true);
    try {
      await patchRecetaLinea(access, pid, linea.id_producto_insumo, aCantidad(editTxt));
      setEditandoId(null);
      setEditTxt("");
      await cargar();
    } catch (e: any) {
      fallo(e, "No se pudo actualizar la cantidad.");
    } finally {
      setOcupado(false);
    }
  }

  function confirmarEliminar(linea: RecetaLinea) {
    Alert.alert(
      "Quitar insumo",
      `¿Quitar ${linea.insumo.nombre_insumo} de la receta?`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Quitar",
          style: "destructive",
          onPress: async () => {
            if (!access) return;
            setOcupado(true);
            try {
              await deleteRecetaLinea(access, pid, linea.id_producto_insumo);
              await cargar();
            } catch (e: any) {
              fallo(e, "No se pudo quitar el insumo.");
            } finally {
              setOcupado(false);
            }
          },
        },
      ]
    );
  }

  async function agregar() {
    if (!access || nuevoInsumo === null || !cantidadValida(nuevaCant)) return;
    setOcupado(true);
    try {
      await addRecetaLinea(access, pid, {
        id_insumo: nuevoInsumo,
        cantidad_requerida: aCantidad(nuevaCant),
      });
      setNuevoInsumo(null);
      setNuevaCant("");
      await cargar();
    } catch (e: any) {
      fallo(e, "No se pudo agregar el insumo.");
    } finally {
      setOcupado(false);
    }
  }

  const disponibles = insumosDisponibles(insumos, receta);
  const puedeAgregar = nuevoInsumo !== null && cantidadValida(nuevaCant) && !ocupado;

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
        <TouchableOpacity onPress={cargar}>
          <Text style={styles.link}>Reintentar</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.replace("/cocina/recetas" as any)}>
          <Text style={styles.link}>Volver</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.replace("/cocina/recetas" as any)}>
          <Text style={styles.link}>‹ Recetas</Text>
        </TouchableOpacity>
        <Text style={styles.title} numberOfLines={1}>
          {nombre ?? "Receta"}
        </Text>
        <View style={{ width: 70 }} />
      </View>
      <Text style={styles.badge}>
        {receta.length === 0
          ? "Sin receta"
          : `${receta.length} ${receta.length === 1 ? "insumo" : "insumos"}`}
      </Text>

      <FlatList
        data={receta}
        keyExtractor={(l) => String(l.id_producto_insumo)}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.muted}>Este producto no tiene insumos aún.</Text>
        }
        renderItem={({ item }) => {
          const editando = editandoId === item.id_producto_insumo;
          return (
            <View style={styles.card}>
              <Text style={styles.nombre} numberOfLines={1}>
                {item.insumo.nombre_insumo}
              </Text>
              {editando ? (
                <View style={styles.editRow}>
                  <TextInput
                    style={styles.inputMini}
                    keyboardType="numeric"
                    value={editTxt}
                    onChangeText={setEditTxt}
                    autoFocus
                  />
                  <TouchableOpacity
                    disabled={!cantidadValida(editTxt) || ocupado}
                    onPress={() => guardarEdicion(item)}
                  >
                    <Text
                      style={[
                        styles.accion,
                        (!cantidadValida(editTxt) || ocupado) && styles.accionOff,
                      ]}
                    >
                      ✓
                    </Text>
                  </TouchableOpacity>
                  <TouchableOpacity onPress={() => setEditandoId(null)}>
                    <Text style={styles.accionCancel}>✕</Text>
                  </TouchableOpacity>
                </View>
              ) : (
                <View style={styles.editRow}>
                  <TouchableOpacity
                    disabled={ocupado}
                    onPress={() => {
                      setEditandoId(item.id_producto_insumo);
                      setEditTxt(String(item.cantidad_requerida));
                    }}
                  >
                    <Text style={styles.cantidad}>
                      {cantidad(item.cantidad_requerida)} {item.insumo.unidad.abreviatura}
                    </Text>
                  </TouchableOpacity>
                  <TouchableOpacity disabled={ocupado} onPress={() => confirmarEliminar(item)}>
                    <Text style={styles.quitar}>✕</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          );
        }}
      />

      <View style={styles.pie}>
        <Text style={styles.label}>Agregar insumo</Text>
        {disponibles.length === 0 ? (
          <Text style={styles.muted}>No quedan insumos por agregar.</Text>
        ) : (
          <>
            <FlatList
              horizontal
              data={disponibles}
              keyExtractor={(i) => String(i.id_insumo)}
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.chips}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[styles.chip, nuevoInsumo === item.id_insumo && styles.chipSel]}
                  onPress={() => setNuevoInsumo(item.id_insumo)}
                >
                  <Text
                    style={[
                      styles.chipTxt,
                      nuevoInsumo === item.id_insumo && styles.chipTxtSel,
                    ]}
                  >
                    {item.nombre_insumo}
                  </Text>
                </TouchableOpacity>
              )}
            />
            <View style={styles.editRow}>
              <TextInput
                style={styles.input}
                keyboardType="numeric"
                value={nuevaCant}
                onChangeText={setNuevaCant}
                placeholder="Cantidad"
              />
              <TouchableOpacity
                style={[styles.btn, !puedeAgregar && styles.btnDisabled]}
                disabled={!puedeAgregar}
                onPress={agregar}
              >
                {ocupado ? (
                  <ActivityIndicator color={colors.onAccent} />
                ) : (
                  <Text style={styles.btnTxt}>Agregar</Text>
                )}
              </TouchableOpacity>
            </View>
          </>
        )}
      </View>
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
    marginBottom: 4,
  },
  title: {
    fontFamily: fonts.title,
    fontSize: 20,
    color: colors.coffee900,
    flex: 1,
    textAlign: "center",
  },
  link: { fontFamily: fonts.semibold, color: colors.accent },
  badge: { fontFamily: fonts.body, color: colors.muted, marginBottom: spacing.sm },
  list: { gap: spacing.sm + 2, paddingBottom: spacing.md },
  card: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardLg,
    padding: spacing.lg,
    gap: spacing.sm,
    ...cardShadow,
  },
  nombre: { fontFamily: fonts.title, fontSize: 15.5, color: colors.coffee900, flex: 1 },
  editRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  cantidad: { fontFamily: fonts.semibold, fontSize: 15, color: colors.accent },
  quitar: { fontSize: 18, color: colors.error, fontFamily: fonts.bold },
  accion: { fontSize: 18, color: colors.okFg, fontFamily: fonts.bold },
  accionOff: { color: colors.disabled },
  accionCancel: { fontSize: 18, color: colors.muted, fontFamily: fonts.bold },
  inputMini: {
    backgroundColor: colors.card,
    borderWidth: 1.5,
    borderColor: colors.inputBorder,
    borderRadius: radius.input,
    paddingHorizontal: 10,
    paddingVertical: 6,
    minWidth: 80,
    textAlign: "right",
    fontFamily: fonts.body,
    color: colors.coffee900,
  },
  pie: {
    borderTopWidth: 1,
    borderTopColor: colors.border,
    paddingTop: spacing.md,
    gap: spacing.sm,
  },
  label: { fontFamily: fonts.semibold, fontSize: 13, color: colors.coffee700 },
  chips: { gap: spacing.sm, paddingVertical: 4 },
  chip: {
    borderWidth: 1.5,
    borderColor: colors.inputBorder,
    borderRadius: radius.pill,
    paddingHorizontal: 15,
    paddingVertical: 8,
    backgroundColor: "transparent",
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
    flex: 1,
  },
  btn: {
    backgroundColor: colors.accent,
    paddingHorizontal: 20,
    height: sizes.input,
    borderRadius: radius.button,
    alignItems: "center",
    justifyContent: "center",
    minWidth: 110,
  },
  btnDisabled: { backgroundColor: colors.disabled },
  btnTxt: { color: colors.onAccent, fontFamily: fonts.bold, fontSize: 15.5 },
  muted: { fontFamily: fonts.body, color: colors.muted, textAlign: "center", marginVertical: 8 },
  errorTxt: { fontFamily: fonts.medium, color: colors.error, textAlign: "center" },
});
