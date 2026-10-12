import React, { useState } from 'react';
import { Image, ScrollView, Text } from 'react-native';
import { api, API, accessToken } from '../api/client';
import type { Incident } from '../api/types';
import { Button, Card, Heading } from '../components/ui';
import type { Palette } from '../theme/colors';

export function IncidentDetail({ colors, incident, online, onBack, onUpdate }: { colors: Palette; incident: Incident; online: boolean; onBack: () => void; onUpdate: (item: Incident) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function corroborate(answer: string) {
    setBusy(true); setError('');
    try { onUpdate(await api<Incident>('/incidents/'+incident.id+'/corroborations', 'POST', { answer, version: incident.version })); setError('Tu corroboración quedó registrada.'); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  return <ScrollView contentContainerStyle={{ padding: 20, gap: 17 }}><Button colors={colors} secondary label="Volver" onPress={onBack} /><Heading colors={colors}>{incident.category}</Heading>
    <Card colors={colors}><Text style={{ color: incident.critical ? colors.danger : colors.blue, fontWeight: '700' }}>{incident.status === 'pending' ? 'Pendiente de corroboración' : incident.status === 'confirmed' ? 'Corroborado' : incident.status === 'resolved' ? 'Finalizado' : incident.status === 'expired' ? 'Vencido' : 'Oculto'}</Text><Text style={{ color: colors.text, fontSize: 16 }}>{incident.description}</Text><Text style={{ color: colors.muted }}>{new Date(incident.occurred_at).toLocaleString('es-MX')}</Text><Text style={{ color: colors.muted }}>{incident.latitude.toFixed(5)}, {incident.longitude.toFixed(5)}</Text></Card>
    {incident.photo_id && online && <Image accessibilityLabel="Evidencia del incidente" source={{ uri: API+'/api/v1/photos/'+incident.photo_id, headers: { Authorization: 'Bearer '+accessToken() } }} style={{ height: 240, borderRadius: 18 }} />}
    {incident.critical ? <Text style={{ color: colors.danger }}>Evita acercarte a la zona. No se solicita corroboración de este incidente.</Text> : <Card colors={colors}><Heading small colors={colors}>¿Sigue presente?</Heading><Text style={{ color: colors.muted }}>Responde únicamente si estás cerca y puedes hacerlo con seguridad. El servidor verificará tu ubicación reciente.</Text><Button colors={colors} busy={busy} disabled={!online} label="Continúa" onPress={() => void corroborate('present')} /><Button colors={colors} secondary busy={busy} disabled={!online} label="Finalizó" onPress={() => void corroborate('ended')} /><Button colors={colors} secondary busy={busy} disabled={!online} label="No puedo confirmar" onPress={() => void corroborate('unknown')} /></Card>}
    {!!error && <Text accessibilityRole="alert" style={{ color: colors.muted }}>{error}</Text>}
  </ScrollView>;
}
