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
      <Stack.Screen name="cocina/index" />
      <Stack.Screen name="mesero/mis-pedidos" />
      <Stack.Screen name="caja/index" />
      <Stack.Screen name="caja/cobro" />
      <Stack.Screen name="caja/gastos" />
      <Stack.Screen name="cocina/inventario" />
      <Stack.Screen name="cocina/ajuste" />
      <Stack.Screen name="cocina/compras" />
      <Stack.Screen name="cocina/compra-nueva" />
    </Stack>
  );
}
