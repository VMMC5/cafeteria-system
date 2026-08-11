import {
  Karla_400Regular,
  Karla_500Medium,
  Karla_600SemiBold,
  Karla_700Bold,
} from "@expo-google-fonts/karla";
import { Lora_400Regular_Italic, Lora_600SemiBold } from "@expo-google-fonts/lora";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";

import { instalarAuthInterceptor } from "@/api/authInterceptor";
import { colors } from "@/theme";

instalarAuthInterceptor();

export default function RootLayout() {
  const [fontsLoaded] = useFonts({
    Lora_600SemiBold,
    Lora_400Regular_Italic,
    Karla_400Regular,
    Karla_500Medium,
    Karla_600SemiBold,
    Karla_700Bold,
  });
  if (!fontsLoaded) return null;

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.cream },
      }}
    >
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
