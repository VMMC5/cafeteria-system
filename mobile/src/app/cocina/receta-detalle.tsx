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
import { aCantidad, cantidadValida, insumosDisponibles } from "@/lib/recetas";
import { useAuth } from "@/store/auth";

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
        <ActivityIndicator size="large" color="#2b6cb0" />
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
                      {item.cantidad_requerida} {item.insumo.unidad.abreviatura}
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
                  <ActivityIndicator color="#fff" />
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
  container: { flex: 1, backgroundColor: "#f4f5f7", padding: 12 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12 },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 24,
    marginBottom: 4,
  },
  title: { fontSize: 20, fontWeight: "700", color: "#2d3748", flex: 1, textAlign: "center" },
  link: { color: "#2b6cb0", fontWeight: "600" },
  badge: { color: "#718096", marginBottom: 8 },
  list: { gap: 10, paddingBottom: 12 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    gap: 8,
  },
  nombre: { fontSize: 16, fontWeight: "700", color: "#2d3748", flex: 1 },
  editRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  cantidad: { fontSize: 16, color: "#2b6cb0", fontWeight: "600" },
  quitar: { fontSize: 18, color: "#c53030", fontWeight: "700" },
  accion: { fontSize: 18, color: "#2f855a", fontWeight: "700" },
  accionOff: { color: "#a0aec0" },
  accionCancel: { fontSize: 18, color: "#718096", fontWeight: "700" },
  inputMini: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    minWidth: 80,
    textAlign: "right",
  },
  pie: {
    borderTopWidth: 1,
    borderTopColor: "#e2e8f0",
    paddingTop: 12,
    gap: 8,
  },
  label: { fontWeight: "600", color: "#4a5568" },
  chips: { gap: 8, paddingVertical: 4 },
  chip: {
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: "#fff",
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
    flex: 1,
  },
  btn: {
    backgroundColor: "#2b6cb0",
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: "center",
    minWidth: 110,
  },
  btnDisabled: { backgroundColor: "#a0aec0" },
  btnTxt: { color: "#fff", fontWeight: "700", fontSize: 16 },
  muted: { color: "#718096", textAlign: "center", marginVertical: 8 },
  errorTxt: { color: "#c53030", textAlign: "center" },
});
