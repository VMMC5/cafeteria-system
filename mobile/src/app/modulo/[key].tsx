import { router, useLocalSearchParams } from "expo-router";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { colors, fonts, radius } from "@/theme";

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
    backgroundColor: colors.cream,
  },
  title: { fontFamily: fonts.title, fontSize: 24, color: colors.coffee900 },
  muted: { fontFamily: fonts.body, color: colors.muted },
  button: {
    backgroundColor: colors.accent,
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: radius.button,
    marginTop: 12,
  },
  buttonText: { color: colors.onAccent, fontFamily: fonts.bold },
});
