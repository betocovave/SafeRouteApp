import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api, saveTokens } from '../api/client';
import type { Tokens } from '../api/types';
import { Button, Card, Field, Heading } from '../components/ui';
import type { Palette } from '../theme/colors';

export function AuthScreen({ colors, onSession }: { colors: Palette; onSession: () => Promise<void> }) {
  const [mode, setMode] = useState<'login' | 'register' | 'recover'>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [newCode, setNewCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit() {
    setBusy(true); setError('');
    try {
      const result = await api<Tokens>('/auth/'+mode, 'POST', { email, password, ...(mode === 'register' ? { name } : {}), ...(mode === 'recover' ? { recovery_code: code } : {}) });
      await saveTokens(result);
      if (result.recovery_code) setNewCode(result.recovery_code); else await onSession();
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}><ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: 'center', padding: 26, gap: 25 }} keyboardShouldPersistTaps="handled">
    <View style={{ gap: 12 }}><Ionicons name="shield-checkmark" size={48} color={colors.blue} /><Heading colors={colors}>SafeRouteAI</Heading><Text style={{ color: colors.muted, fontSize: 17 }}>Tu camino, con más información.</Text></View>
    {newCode ? <Card colors={colors}><Heading small colors={colors}>Guarda tu código privado</Heading><Text style={{ color: colors.muted }}>Lo necesitarás para recuperar tu cuenta. Se muestra una sola vez. Guárdalo en un lugar privado antes de continuar.</Text><Text selectable style={{ color: colors.text, fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace', fontSize: 16 }}>{newCode}</Text><Button colors={colors} label="Ya guardé mi código" onPress={() => { setNewCode(''); void onSession(); }} /></Card> : <Card colors={colors}>
      <Heading small colors={colors}>{mode === 'login' ? 'Bienvenido de nuevo' : mode === 'register' ? 'Crea tu cuenta' : 'Recupera tu acceso'}</Heading>
      {mode === 'register' && <Field colors={colors} label="Nombre" value={name} onChangeText={setName} autoComplete="name" />}
      <Field colors={colors} label="Correo electrónico" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" autoComplete="email" />
      {mode === 'recover' && <Field colors={colors} label="Código privado de recuperación" value={code} onChangeText={setCode} autoCapitalize="none" />}
      <Field colors={colors} label={mode === 'recover' ? 'Nueva contraseña' : 'Contraseña'} value={password} onChangeText={setPassword} secureTextEntry autoCapitalize="none" placeholder="Al menos 10 caracteres" />
      {!!error && <Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text>}
      <Button colors={colors} busy={busy} label={mode === 'login' ? 'Entrar' : mode === 'register' ? 'Crear cuenta' : 'Restablecer contraseña'} onPress={() => void submit()} />
      <Button colors={colors} secondary label={mode === 'login' ? 'Crear una cuenta' : 'Volver a iniciar sesión'} onPress={() => { setError(''); setMode(mode === 'login' ? 'register' : 'login'); }} />
      {mode === 'login' && <Button colors={colors} secondary label="Olvidé mi contraseña" onPress={() => setMode('recover')} />}
    </Card>}
    <Text style={{ color: colors.muted, fontSize: 12 }}>Salamanca, Guanajuato · Rutas e información de la comunidad</Text>
  </ScrollView></KeyboardAvoidingView>;
}
