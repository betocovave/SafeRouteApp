import React, { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { Palette } from '../theme/colors';

export function Button({ label, onPress, colors, secondary = false, disabled = false, busy = false, icon }: { label: string; onPress: () => void; colors: Palette; secondary?: boolean; disabled?: boolean; busy?: boolean; icon?: keyof typeof Ionicons.glyphMap }) {
  const fg = secondary ? colors.blue : colors.onBlue;
  return <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{ disabled: disabled || busy, busy }} disabled={disabled || busy} onPress={onPress} style={({ pressed }) => [styles.button, !secondary && styles.lift, { backgroundColor: secondary ? colors.pale : colors.blue, opacity: disabled || busy ? 0.45 : 1, transform: [{ scale: pressed ? 0.98 : 1 }] }]}>
    {busy ? <ActivityIndicator color={fg} /> : icon ? <Ionicons name={icon} size={20} color={fg} /> : null}<Text style={{ color: fg, fontWeight: '700', fontSize: 15, flexShrink: 1, textAlign: 'center' }}>{label}</Text>
  </Pressable>;
}
// Opción de selección (categoría, transporte, tema…): un botón de acción completo se leía como mil botones iguales.
export function Chip({ label, selected, onPress, colors }: { label: string; selected: boolean; onPress: () => void; colors: Palette }) {
  return <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{ selected }} onPress={onPress} style={{ minHeight: 44, paddingHorizontal: 16, borderRadius: 22, borderWidth: 1.5, alignItems: 'center', justifyContent: 'center', borderColor: selected ? colors.blue : colors.border, backgroundColor: selected ? colors.blue : colors.surface }}>
    <Text style={{ color: selected ? colors.onBlue : colors.text, fontWeight: selected ? '700' : '500', fontSize: 14 }}>{label}</Text>
  </Pressable>;
}
export function Field({ label, colors, ...props }: React.ComponentProps<typeof TextInput> & { label: string; colors: Palette }) {
  const [focused, setFocused] = useState(false);
  return <View style={{ gap: 7 }}><Text style={{ color: colors.muted, fontSize: 13, fontWeight: '600' }}>{label}</Text><TextInput accessibilityLabel={label} placeholderTextColor={colors.muted} {...props} onFocus={e => { setFocused(true); props.onFocus?.(e); }} onBlur={e => { setFocused(false); props.onBlur?.(e); }} style={[styles.input, { color: colors.text, borderColor: focused ? colors.blue : colors.border, backgroundColor: colors.surface }, props.style]} /></View>;
}
export function Card({ colors, children }: { colors: Palette; children: React.ReactNode }) {
  return <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>{children}</View>;
}
export function Heading({ children, colors, small = false }: { children: React.ReactNode; colors: Palette; small?: boolean }) {
  return <Text accessibilityRole="header" style={{ color: colors.text, fontSize: small ? 19 : 30, lineHeight: small ? 25 : 36, fontWeight: '800', letterSpacing: -0.6 }}>{children}</Text>;
}
const styles = StyleSheet.create({
  button: { minHeight: 50, borderRadius: 16, paddingHorizontal: 18, paddingVertical: 12, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  lift: { elevation: 2, shadowColor: '#0B2A55', shadowOpacity: 0.18, shadowRadius: 8, shadowOffset: { width: 0, height: 3 } },
  input: { borderWidth: 1.5, borderRadius: 14, paddingHorizontal: 14, paddingVertical: 13, minHeight: 50, fontSize: 16 },
  card: { padding: 18, borderRadius: 22, borderWidth: 1, gap: 12, elevation: 1, shadowColor: '#0B2A55', shadowOpacity: 0.07, shadowRadius: 10, shadowOffset: { width: 0, height: 4 } },
});
