import { router } from "expo-router";
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { Modulo, modulesForRole } from "@/lib/modules";
import { useAuth } from "@/store/auth";
import { cardShadow, colors, fonts, radius, spacing } from "@/theme";
import { IconName, NavIcon } from "@/ui";

const MODULO_ICON: Record<Modulo["key"], IconName> = {
  mesero: "mesas",
  caja: "cobrar",
  cocina: "pedidos",
};

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
            <View style={styles.cardIcon}>
              <NavIcon name={MODULO_ICON[m.key]} color={colors.accent} size={24} />
            </View>
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
  container: { flex: 1, padding: spacing.xl, backgroundColor: colors.cream },
  hello: { fontFamily: fonts.title, fontSize: 24, color: colors.coffee900, marginTop: 24 },
  subtitle: { fontFamily: fonts.body, fontSize: 15, color: colors.muted, marginBottom: spacing.lg },
  grid: { gap: spacing.md },
  card: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardLg,
    padding: spacing.xl,
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.lg,
    ...cardShadow,
  },
  cardIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: colors.busyBg,
    alignItems: "center",
    justifyContent: "center",
  },
  cardText: { fontFamily: fonts.title, fontSize: 17, color: colors.coffee900 },
  muted: { fontFamily: fonts.body, color: colors.muted },
  logout: { padding: spacing.lg, alignItems: "center" },
  logoutText: { fontFamily: fonts.bold, color: colors.error },
});
