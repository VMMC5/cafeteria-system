// Cafetería Aroma — componentes base de la app, según los mockups.
// Dependen solo de src/theme y react-native (+ react-native-svg para iconos).
import { ReactNode } from "react";
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
  ViewStyle,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Svg, { Path } from "react-native-svg";

import { cardShadow, colors, fonts, radius, sizes } from "@/theme";

// ── Iconos de línea de la barra inferior (los mismos paths de los mockups) ──
export const ICON_PATHS = {
  mesas: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z",
  pedidos: "M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6",
  recetas: "M4 5a2 2 0 012-2h14v16H6a2 2 0 00-2 2zM4 5v16M8 7h8",
  compras: "M3 5h2l2.5 11h10L20 8H7M10.5 19.5h.01M16.5 19.5h.01",
  inventario: "M3 8l9-5 9 5v8l-9 5-9-5zM3 8l9 5 9-5M12 13v8",
  cobrar: "M3 7h18v10H3zM14 12a2 2 0 11-4 0 2 2 0 014 0",
  gastos: "M4 7V6a2 2 0 012-2h12v3M4 7h15a2 2 0 012 2v8a2 2 0 01-2 2H6a2 2 0 01-2-2zM16 13h.5",
  salir: "M9 4h-4v16h4M14 8l4 4-4 4M18 12H8",
} as const;

export type IconName = keyof typeof ICON_PATHS;

export function NavIcon({ name, color, size = 21 }: { name: IconName; color: string; size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d={ICON_PATHS[name]} stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}

export type NavItem = { key: string; label: string; icon: IconName };

// Barra inferior por rol — p. ej. rol mesero:
//   [{key:'mesas', label:'Mesas', icon:'mesas'}, {key:'pedidos', label:'Pedidos', icon:'pedidos'}, {key:'salir', label:'Salir', icon:'salir'}]
export function BottomNav({
  items,
  active,
  onPress,
}: {
  items: NavItem[];
  active: string;
  onPress: (key: string) => void;
}) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[s.nav, { paddingBottom: Math.max(insets.bottom, 18) }]}>
      {items.map((it) => {
        const on = it.key === active;
        const color = on ? colors.caramelLight : colors.navInactive;
        return (
          <Pressable
            key={it.key}
            style={s.navItem}
            onPress={() => onPress(it.key)}
            accessibilityRole="tab"
            accessibilityState={{ selected: on }}
          >
            <NavIcon name={it.icon} color={color} />
            <Text style={[s.navLabel, { color, fontFamily: on ? fonts.bold : fonts.medium }]}>{it.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: ViewStyle | ViewStyle[] }) {
  return <View style={[s.card, style]}>{children}</View>;
}

export function PrimaryButton({
  title,
  onPress,
  disabled,
}: {
  title: string;
  onPress?: () => void;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      style={({ pressed }) => [
        s.btn,
        disabled && { backgroundColor: colors.disabled },
        pressed && !disabled && { backgroundColor: colors.accentDark },
      ]}
    >
      <Text style={s.btnText}>{title}</Text>
    </Pressable>
  );
}

// Chip segmentado (métodos de pago, Entrada/Salida, proveedores, categorías)
export function Chip({ label, active, onPress }: { label: string; active?: boolean; onPress?: () => void }) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: !!active }}
      style={[s.chip, active && s.chipActive]}
    >
      <Text style={[s.chipText, active && s.chipTextActive]}>{label}</Text>
    </Pressable>
  );
}

export function Input(props: TextInputProps) {
  return <TextInput placeholderTextColor={colors.placeholder} {...props} style={[s.input, props.style]} />;
}

export type BadgeVariant = "ok" | "warn" | "busy" | "error";

// Badge de estado: 'ok' (Disponible) | 'warn' (Pendiente) | 'busy' (Ocupada) | 'error' (Stock bajo)
export function Badge({ label, variant = "ok" }: { label: string; variant?: BadgeVariant }) {
  const map: Record<BadgeVariant, [string, string]> = {
    ok: [colors.okBg, colors.okFg],
    warn: [colors.warnBg, colors.warnFg],
    busy: [colors.busyBg, colors.busyFg],
    error: [colors.errorBg, colors.error],
  };
  const [bg, fg] = map[variant];
  return (
    <View style={[s.badge, { backgroundColor: bg }]}>
      <Text style={[s.badgeText, { color: fg }]}>{label.toUpperCase()}</Text>
    </View>
  );
}

// Stepper −/+ de los menús
export function Stepper({ value, onAdd, onRemove }: { value: number; onAdd: () => void; onRemove: () => void }) {
  return (
    <View style={s.stepperRow}>
      <Pressable onPress={onRemove} accessibilityLabel="Quitar" style={s.stepBtnOutline}>
        <Text style={s.stepMinus}>−</Text>
      </Pressable>
      <Text style={s.stepValue}>{value}</Text>
      <Pressable onPress={onAdd} accessibilityLabel="Agregar" style={s.stepBtnFill}>
        <Text style={s.stepPlus}>+</Text>
      </Pressable>
    </View>
  );
}

const s = StyleSheet.create({
  nav: { flexDirection: "row", backgroundColor: colors.coffee950, paddingTop: 10, paddingHorizontal: 6 },
  navItem: { flex: 1, alignItems: "center", justifyContent: "center", gap: 4, minHeight: sizes.navItem },
  navLabel: { fontSize: 10.5 },
  card: {
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.cardLg,
    padding: 16,
    ...cardShadow,
  },
  btn: {
    height: sizes.button,
    borderRadius: radius.button,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  btnText: { color: colors.onAccent, fontFamily: fonts.bold, fontSize: 15.5 },
  chip: {
    height: sizes.chip,
    paddingHorizontal: 15,
    borderRadius: radius.pill,
    borderWidth: 1.5,
    borderColor: colors.inputBorder,
    alignItems: "center",
    justifyContent: "center",
  },
  chipActive: { borderColor: colors.accent, backgroundColor: colors.accent },
  chipText: { color: colors.coffee700, fontFamily: fonts.semibold, fontSize: 13 },
  chipTextActive: { color: colors.onAccent, fontFamily: fonts.bold },
  input: {
    height: sizes.input,
    paddingHorizontal: 14,
    borderRadius: radius.input,
    borderWidth: 1.5,
    borderColor: colors.inputBorder,
    backgroundColor: colors.card,
    fontFamily: fonts.body,
    fontSize: 15,
    color: colors.coffee900,
  },
  badge: { alignSelf: "flex-start", paddingHorizontal: 12, paddingVertical: 4, borderRadius: radius.pill },
  badgeText: { fontSize: 10.5, fontFamily: fonts.bold, letterSpacing: 0.5 },
  stepperRow: { flexDirection: "row", alignItems: "center", gap: 12 },
  stepBtnOutline: {
    width: sizes.stepper,
    height: sizes.stepper,
    borderRadius: sizes.stepper / 2,
    borderWidth: 1.5,
    borderColor: colors.inputBorder,
    alignItems: "center",
    justifyContent: "center",
  },
  stepBtnFill: {
    width: sizes.stepper,
    height: sizes.stepper,
    borderRadius: sizes.stepper / 2,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  stepMinus: { color: colors.accent, fontSize: 17, fontFamily: fonts.bold },
  stepPlus: { color: colors.onAccent, fontSize: 17, fontFamily: fonts.bold },
  stepValue: { minWidth: 16, textAlign: "center", fontSize: 14.5, fontFamily: fonts.bold, color: colors.coffee900 },
});
