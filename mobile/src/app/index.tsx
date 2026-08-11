import { Redirect } from "expo-router";
import { useEffect } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { homeRoute } from "@/lib/modules";
import { useAuth } from "@/store/auth";
import { colors, fonts } from "@/theme";

export default function Index() {
  const status = useAuth((s) => s.status);
  const user = useAuth((s) => s.user);
  const bootstrap = useAuth((s) => s.bootstrap);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  if (status === "loading") {
    return (
      <View style={styles.center}>
        <Text style={styles.brand}>
          Cafetería <Text style={styles.brandEm}>Aroma</Text>
        </Text>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }
  if (status === "auth") {
    const destino = user ? homeRoute(user.rol.nombre_rol) : "/login";
    return <Redirect href={destino as any} />;
  }
  return <Redirect href={"/login" as any} />;
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
    backgroundColor: colors.cream,
  },
  brand: { fontFamily: fonts.title, fontSize: 28, color: colors.coffee900 },
  brandEm: { fontFamily: fonts.titleItalic, color: colors.accent },
});
