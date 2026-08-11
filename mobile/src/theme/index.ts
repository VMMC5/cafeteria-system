// Cafetería Aroma — tokens de diseño de la app (mockups "Cafetería Aroma móvil").
// Lora (títulos, cifras) · Karla (UI, cuerpo) — cargadas en app/_layout.tsx.

export const colors = {
  coffee950: "#2B1E16", // barra de navegación inferior, fondos oscuros
  coffee900: "#33241B", // texto principal, botón secundario oscuro
  coffee700: "#5A4636", // labels, texto secundario fuerte
  accent: "#8A5A3B", // botón primario, links, chips activos
  accentDark: "#6F4630", // pressed del primario
  caramel: "#C89B6D", // acentos, logo vapor, barras de gráfica
  caramelLight: "#E0B487", // ítem activo en la nav inferior, "Aroma" en el logo
  cream: "#F4EDE2", // fondo de pantalla
  card: "#FFFDF9", // fondo de tarjetas
  border: "#E6DBCB", // borde de tarjetas
  inputBorder: "#D8CBBA", // borde de inputs
  muted: "#8A7A68", // texto terciario
  placeholder: "#B9A794",
  error: "#B3402E", // stock bajo, montos de gasto, acciones destructivas
  errorBg: "#FBEFEC",
  errorBorder: "#E5B8AD",
  okBg: "#EAEFE3",
  okFg: "#5E7247", // badge Disponible
  warnBg: "#F7ECD8",
  warnFg: "#9A6B2F", // badge Pendiente
  busyBg: "#F3E3CE",
  busyFg: "#8A5A3B", // badge Ocupada
  disabled: "#C9B8A3", // botón deshabilitado
  navInactive: "rgba(244,237,226,0.62)",
  onAccent: "#FFF8EF",
} as const;

export const fonts = {
  title: "Lora_600SemiBold", // headers de pantalla (24), títulos de tarjeta (17)
  titleItalic: "Lora_400Regular_Italic",
  body: "Karla_400Regular",
  medium: "Karla_500Medium",
  semibold: "Karla_600SemiBold",
  bold: "Karla_700Bold",
} as const;

export const radius = { input: 10, card: 12, cardLg: 14, button: 12, pill: 999 } as const;

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, screen: 16 } as const;

// Medidas clave usadas en los mockups
export const sizes = {
  input: 48, // alto de inputs (touch target >= 44)
  button: 50, // alto del botón primario
  chip: 44, // alto de chips segmentados (Entrada/Salida, métodos de pago)
  stepper: 34, // botones +/- circulares
  navItem: 44, // alto mínimo de cada ítem de la barra inferior
} as const;

// Sombra de tarjeta (iOS) + elevation (Android)
export const cardShadow = {
  shadowColor: "#3B2A20",
  shadowOpacity: 0.05,
  shadowRadius: 12,
  shadowOffset: { width: 0, height: 4 },
  elevation: 2,
} as const;
