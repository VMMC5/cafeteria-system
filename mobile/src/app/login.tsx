import { router } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { homeRoute } from "@/lib/modules";
import { useAuth } from "@/store/auth";
import { cardShadow, colors, fonts, radius, spacing } from "@/theme";
import { Input, PrimaryButton } from "@/ui";

export default function Login() {
  const login = useAuth((s) => s.login);
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit() {
    setError(null);
    setLoading(true);
    try {
      await login(correo.trim(), password);
      const user = useAuth.getState().user;
      const destino = user ? homeRoute(user.rol.nombre_rol) : "/seleccion-modulo";
      router.replace(destino as any);
    } catch (e: any) {
      if (e?.response?.status === 401) setError("Correo o contraseña incorrectos.");
      else setError("No se pudo conectar con el servidor.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      <View style={styles.brand}>
        <View style={styles.steam}>
          <View style={[styles.steamBar, { height: 10 }]} />
          <View style={[styles.steamBar, { height: 16 }]} />
          <View style={[styles.steamBar, { height: 12 }]} />
        </View>
        <Text style={styles.brandName}>
          Cafetería <Text style={styles.brandEm}>Aroma</Text>
        </Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.title}>Iniciar sesión</Text>
        <Text style={styles.subtitle}>Accede con tu cuenta del equipo</Text>
        {error && (
          <View style={styles.alert}>
            <Text style={styles.alertText}>{error}</Text>
          </View>
        )}
        <View style={styles.field}>
          <Text style={styles.label}>Correo electrónico</Text>
          <Input
            placeholder="tu@cafeteria.com"
            autoCapitalize="none"
            keyboardType="email-address"
            autoComplete="email"
            value={correo}
            onChangeText={setCorreo}
          />
        </View>
        <View style={styles.field}>
          <Text style={styles.label}>Contraseña</Text>
          <Input
            placeholder="••••••••"
            secureTextEntry
            autoComplete="password"
            value={password}
            onChangeText={setPassword}
          />
        </View>
        {loading ? (
          <View style={styles.loadingBtn}>
            <ActivityIndicator color={colors.onAccent} />
            <Text style={styles.loadingText}>Verificando…</Text>
          </View>
        ) : (
          <PrimaryButton title="Iniciar sesión" onPress={onSubmit} />
        )}
      </View>

      <Text style={styles.muted}>¿Olvidaste tu contraseña? Contacta al administrador.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    padding: spacing.xl,
    gap: spacing.lg,
    backgroundColor: colors.cream,
  },
  brand: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 10 },
  steam: { flexDirection: "row", alignItems: "flex-end", gap: 3, height: 18 },
  steamBar: { width: 3, borderRadius: 2, backgroundColor: colors.caramel },
  brandName: { fontFamily: fonts.title, fontSize: 24, color: colors.coffee900, letterSpacing: 0.5 },
  brandEm: { fontFamily: fonts.titleItalic, color: colors.accent },
  card: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardLg,
    padding: spacing.xl,
    gap: spacing.md,
    ...cardShadow,
  },
  title: { fontFamily: fonts.title, fontSize: 22, color: colors.coffee900 },
  subtitle: { fontFamily: fonts.body, fontSize: 14, color: colors.muted, marginTop: -6 },
  field: { gap: 6 },
  label: { fontFamily: fonts.semibold, fontSize: 13, color: colors.coffee700 },
  alert: {
    backgroundColor: colors.errorBg,
    borderWidth: 1,
    borderColor: colors.errorBorder,
    borderRadius: radius.input,
    padding: spacing.md,
  },
  alertText: { fontFamily: fonts.medium, fontSize: 13.5, color: colors.error },
  loadingBtn: {
    height: 50,
    borderRadius: radius.button,
    backgroundColor: colors.disabled,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  loadingText: { color: colors.onAccent, fontFamily: fonts.bold, fontSize: 15.5 },
  muted: { fontFamily: fonts.body, color: colors.muted, textAlign: "center", fontSize: 13 },
});
