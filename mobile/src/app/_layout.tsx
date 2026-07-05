import { Stack } from "expo-router";

export default function RootLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="login" />
      <Stack.Screen name="seleccion-modulo" />
      <Stack.Screen name="modulo/[key]" />
      <Stack.Screen name="mesero/mesas" />
      <Stack.Screen name="mesero/menu" />
      <Stack.Screen name="mesero/carrito" />
    </Stack>
  );
}
