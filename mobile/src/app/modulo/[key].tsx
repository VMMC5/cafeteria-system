import { router, useLocalSearchParams } from "expo-router";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

const LABELS: Record<string, string> = {
  mesero: "Mesero",
  caja: "Caja",
  cocina: "Cocina",
};

export default function Modulo() {
  const { key } = useLocalSearchParams<{ key: string }>();
  const label = LABELS[key ?? ""] ?? "Módulo";
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Módulo {label}</Text>
      <Text style={styles.muted}>Próximamente</Text>
      <TouchableOpacity
        style={styles.button}
        onPress={() => router.replace("/seleccion-modulo" as any)}
      >
        <Text style={styles.buttonText}>Volver</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    backgroundColor: "#f4f5f7",
  },
  title: { fontSize: 24, fontWeight: "700", color: "#2d3748" },
  muted: { color: "#718096" },
  button: {
    backgroundColor: "#2b6cb0",
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
    marginTop: 12,
  },
  buttonText: { color: "#fff", fontWeight: "600" },
});
