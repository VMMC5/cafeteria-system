import { router } from "expo-router";
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { modulesForRole } from "@/lib/modules";
import { useAuth } from "@/store/auth";

export default function SeleccionModulo() {
  const user = useAuth((s) => s.user);
  const logout = useAuth((s) => s.logout);
  const modulos = user ? modulesForRole(user.rol.nombre_rol) : [];

  async function salir() {
    await logout();
    router.replace("/login" as any);
  }

  return (
    <View style={styles.container}>
      <Text style={styles.hello}>Hola, {user?.nombre ?? ""}</Text>
      <Text style={styles.subtitle}>Selecciona un módulo</Text>
      <ScrollView contentContainerStyle={styles.grid}>
        {modulos.length === 0 && (
          <Text style={styles.muted}>Tu rol no tiene módulos móviles asignados.</Text>
        )}
        {modulos.map((m) => (
          <TouchableOpacity
            key={m.key}
            style={styles.card}
            onPress={() => router.push(m.ruta as any)}
          >
            <Text style={styles.cardText}>{m.label}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
      <TouchableOpacity style={styles.logout} onPress={salir}>
        <Text style={styles.logoutText}>Cerrar sesión</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, backgroundColor: "#f4f5f7" },
  hello: { fontSize: 22, fontWeight: "700", color: "#2d3748", marginTop: 24 },
  subtitle: { fontSize: 16, color: "#4a5568", marginBottom: 16 },
  grid: { gap: 12 },
  card: { backgroundColor: "#2b6cb0", borderRadius: 12, padding: 28, alignItems: "center" },
  cardText: { color: "#fff", fontSize: 18, fontWeight: "600" },
  muted: { color: "#718096" },
  logout: { padding: 14, alignItems: "center" },
  logoutText: { color: "#c53030", fontWeight: "600" },
});
