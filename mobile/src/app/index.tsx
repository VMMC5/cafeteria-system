import { Redirect } from "expo-router";
import { useEffect } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { homeRoute } from "@/lib/modules";
import { useAuth } from "@/store/auth";

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
        <Text style={styles.brand}>☕ Cafetería</Text>
        <ActivityIndicator size="large" color="#2b6cb0" />
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
    backgroundColor: "#f4f5f7",
  },
  brand: { fontSize: 28, fontWeight: "700", color: "#2d3748" },
});
