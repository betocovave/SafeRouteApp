import React, { useState } from 'react';
import { Alert, ScrollView, Switch, Text, View } from 'react-native';
import { api, saveTokens } from '../api/client';
import type { OfflinePackage, Point, Preferences, User } from '../api/types';
import { deletePackage, downloadPackage, pendingReports } from '../storage/local';
import { Button, Card, Field, Heading } from '../components/ui';
import type { Palette } from '../theme/colors';

export function SettingsScreen({ colors, user, online, point, pack, onUser, onPack, onLogout, onAdmin, onNotifications }: { colors: Palette; user: User; online: boolean; point: Point | null; pack: OfflinePackage | null; onUser: (user: User) => void; onPack: (pack: OfflinePackage | null) => void; onLogout: () => void; onAdmin: () => void; onNotifications: () => Promise<void> }) {
  const [name, setName] = useState(user.name);
  const [preferences, setPreferences] = useState(user.preferences);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function save() {
    setBusy(true); setError('');
    try { const profile = await api<User>('/users/me', 'PATCH', { name }); const value = await api<Preferences>('/preferences', 'PUT', preferences); onUser({ ...profile, preferences: value }); setError('Cambios guardados.'); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function download() {
    if (!point) { setError('Activa tu ubicación para descargar un sector cercano.'); return; }
    setBusy(true); setError('');
    try { onPack(await downloadPackage(point)); setError('Mapa descargado. Disponible sin conexión.'); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function logout() {
    const items = await pendingReports();
    if (items.length) { setError('Envía tus reportes pendientes antes de cerrar sesión.'); return; }
    if (!online) { setError('Conecta la app para cerrar y revocar tu sesión.'); return; }
    try { await api('/auth/logout', 'POST'); await saveTokens(null); onLogout(); } catch (e) { setError((e as Error).message); }
  }
  return <ScrollView contentContainerStyle={{ padding: 20, gap: 18, paddingBottom: 35 }}><Heading colors={colors}>Tu perfil</Heading><Card colors={colors}><Text style={{ color: colors.muted }}>{user.email}</Text><Field colors={colors} label="Nombre" value={name} onChangeText={setName} /></Card>
    <Card colors={colors}><Heading small colors={colors}>Preferencias</Heading><Text style={{ color: colors.muted }}>Medio de transporte</Text><View style={{ flexDirection: 'row', gap: 8 }}>{(['driving', 'walking'] as const).map(v => <Button key={v} colors={colors} secondary={preferences.transport !== v} label={v === 'driving' ? 'Automóvil' : 'A pie'} onPress={() => setPreferences({ ...preferences, transport: v })} />)}</View>
    <Text style={{ color: colors.muted }}>Tolerancia de riesgo</Text><View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>{(['low', 'medium', 'high'] as const).map(v => <Button key={v} colors={colors} secondary={preferences.risk_tolerance !== v} label={{ low: 'Baja', medium: 'Media', high: 'Alta' }[v]} onPress={() => setPreferences({ ...preferences, risk_tolerance: v })} />)}</View>
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}><Text style={{ color: colors.text }}>Alertas de seguridad</Text><Switch accessibilityLabel="Alertas de seguridad" value={preferences.alerts} onValueChange={v => setPreferences({ ...preferences, alerts: v })} trackColor={{ true: colors.blue }} /></View>
    <Text style={{ color: colors.muted }}>Apariencia</Text><View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>{(['system', 'light', 'dark'] as const).map(v => <Button key={v} colors={colors} secondary={preferences.theme !== v} label={{ system: 'Sistema', light: 'Claro', dark: 'Oscuro' }[v]} onPress={() => setPreferences({ ...preferences, theme: v })} />)}</View>
    <Text style={{ color: colors.muted }}>Horario silencioso de notificaciones (0–23, hora de México). Las alertas críticas conservan su prioridad.</Text><View style={{ flexDirection: 'row', gap: 12 }}><View style={{ flex: 1 }}><Field colors={colors} label="Desde" keyboardType="number-pad" value={preferences.quiet_start === null ? '' : String(preferences.quiet_start)} onChangeText={v => setPreferences({ ...preferences, quiet_start: v === '' ? null : Number(v) })} /></View><View style={{ flex: 1 }}><Field colors={colors} label="Hasta" keyboardType="number-pad" value={preferences.quiet_end === null ? '' : String(preferences.quiet_end)} onChangeText={v => setPreferences({ ...preferences, quiet_end: v === '' ? null : Number(v) })} /></View></View>
    <Button colors={colors} disabled={!online} busy={busy} label="Guardar cambios" onPress={() => void save()} /><Button colors={colors} secondary disabled={!online} label="Activar notificaciones del dispositivo" onPress={() => void onNotifications().then(() => setError('Notificaciones activadas.')).catch(e => setError(e.message))} /></Card>
    <Card colors={colors}><Heading small colors={colors}>Mapa sin conexión</Heading><Text style={{ color: colors.muted }}>Descarga calles y nombres en un radio de 2 km. Máximo 50 MB. Puedes continuar una ruta iniciada; nuevas rutas y alertas requieren conexión.</Text>{pack && <Text style={{ color: colors.text }}>Descargado: {new Date(pack.metadata.created_at).toLocaleString('es-MX')}</Text>}<Button colors={colors} disabled={!online || !point} busy={busy} label={pack ? 'Actualizar sector' : 'Descargar sector cercano'} icon="download-outline" onPress={() => void download()} />{pack && <Button colors={colors} secondary label="Eliminar mapa descargado" onPress={() => Alert.alert('Eliminar mapa', 'Podrás descargarlo nuevamente al conectarte.', [{ text: 'Cancelar', style: 'cancel' }, { text: 'Eliminar', style: 'destructive', onPress: () => { deletePackage(); onPack(null); } }])} />}</Card>
    {!!error && <Text style={{ color: colors.danger }}>{error}</Text>}
    {user.role === 'admin' && <Button colors={colors} secondary label="Administración" onPress={onAdmin} />}
    <Button colors={colors} secondary label="Cerrar sesión" onPress={() => void logout()} />
  </ScrollView>;
}
