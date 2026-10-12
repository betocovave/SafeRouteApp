import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import type { Palette } from '../theme/colors';

export function Button({ label, onPress, colors, secondary = false, disabled = false, busy = false, icon }: { label: string; onPress: () => void; colors: Palette; secondary?: boolean; disabled?: boolean; busy?: boolean; icon?: keyof typeof Ionicons.glyphMap }) {
  return <Pressable accessibilityRole="button" accessibilityLabel={label} disabled={disabled || busy} onPress={onPress} style={({ pressed }) => [styles.button, { backgroundColor: secondary ? colors.pale : colors.blue, opacity: disabled || busy ? 0.45 : pressed ? 0.75 : 1 }]}>
    {busy ? <ActivityIndicator color={secondary ? colors.blue : '#FFF'} /> : icon ? <Ionicons name={icon} size={20} color={secondary ? colors.blue : '#FFF'} /> : null}<Text style={{ color: secondary ? colors.blue : '#FFF', fontWeight: '700', fontSize: 15 }}>{label}</Text>
  </Pressable>;
}
export function Field({ label, colors, ...props }: React.ComponentProps<typeof TextInput> & { label: string; colors: Palette }) {
  return <View style={{ gap: 7 }}><Text style={{ color: colors.muted, fontSize: 13, fontWeight: '600' }}>{label}</Text><TextInput accessibilityLabel={label} placeholderTextColor={colors.muted} {...props} style={[styles.input, { color: colors.text, borderColor: colors.border, backgroundColor: colors.surface }, props.style]} /></View>;
}
export function Card({ colors, children }: { colors: Palette; children: React.ReactNode }) {
  return <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>{children}</View>;
}
export function Heading({ children, colors, small = false }: { children: React.ReactNode; colors: Palette; small?: boolean }) {
  return <Text style={{ color: colors.text, fontSize: small ? 19 : 28, fontWeight: '800', letterSpacing: -0.5 }}>{children}</Text>;
}
const styles = StyleSheet.create({ button: { minHeight: 48, borderRadius: 15, paddingHorizontal: 17, paddingVertical: 12, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 }, input: { borderWidth: 1, borderRadius: 13, padding: 13, minHeight: 48, fontSize: 16 }, card: { padding: 18, borderRadius: 21, borderWidth: 1, gap: 12 } });
