import React, { useEffect, useState } from 'react';
import { Alert, ScrollView, Text, View } from 'react-native';
import { api } from '../api/client';
import type { AppAlert, History, Incident, PendingReport, Route } from '../api/types';
import { discardPending, pendingReports, read, syncReports, write } from '../storage/local';
import { Button, Card, Heading } from '../components/ui';
import type { Palette } from '../theme/colors';

export function ActivityScreen({ colors, online, changeVersion, onIncident, onRoute }: { colors: Palette; online: boolean; changeVersion: number; onIncident: (item: Incident, own: boolean) => void; onRoute: (item: Route) => void }) {
  const [alerts, setAlerts] = useState<AppAlert[]>([]);
  const [history, setHistory] = useState<History>({ routes: [], reports: [] });
  const [pending, setPending] = useState<PendingReport[]>([]);
  const [shownRoutes, setShownRoutes] = useState(3);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function load() {
    setBusy(true); setError('');
    try {
      const [a, h, p] = online ? await Promise.all([api<AppAlert[]>('/alerts'), api<History>('/history'), pendingReports()]) : await Promise.all([read<AppAlert[]>('alerts', []), read<History>('history', { routes: [], reports: [] }), pendingReports()]);
      setAlerts(a); setHistory(h); setPending(p); setShownRoutes(3);
      await write('alerts', a); await write('history', h);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  // Rutas de 3 en 3; solo se pide otra página al servidor cuando ya se mostraron todas las cargadas.
  async function moreRoutes() {
    if (shownRoutes < history.routes.length) { setShownRoutes(shownRoutes+3); return; }
    setBusy(true); setError('');
    try {
      const h = await api<History>('/history?offset='+history.routes.length);
      if (!h.routes.length) { setError('No hay más rutas consultadas.'); return; }
      setHistory(old => ({ ...old, routes: [...old.routes, ...h.routes] })); setShownRoutes(shownRoutes+3);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  useEffect(() => { void load(); }, [online, changeVersion]);
  async function openAlert(item: AppAlert) {
    try { const incident = await api<Incident>('/incidents/'+item.incident_id); await api('/alerts/'+item.id+'/read', 'PATCH'); onIncident(incident, false); }
    catch (e) { setError((e as Error).message); }
  }
  return <ScrollView contentContainerStyle={{ padding: 20, gap: 17, paddingBottom: 35 }}><Heading colors={colors}>Tu actividad</Heading><Button colors={colors} secondary busy={busy} label="Actualizar" onPress={() => void load()} />
    {!!error && <Text style={{ color: colors.danger }}>{error}</Text>}
    {!!pending.length && <Card colors={colors}><Heading small colors={colors}>Envíos pendientes · {pending.length}</Heading>{pending.map(p => <View key={p.client_id} style={{ gap: 7 }}><Text style={{ color: colors.muted }}>{p.report_id ? 'Reporte enviado; foto pendiente' : 'Reporte pendiente'} · {p.error || p.description}</Text><Button colors={colors} secondary label={p.report_id ? 'Continuar sin foto pendiente' : 'Descartar borrador pendiente'} onPress={() => Alert.alert('Descartar envío local', 'Se eliminará este envío pendiente del dispositivo. Un reporte ya recibido por el servidor permanece registrado.', [{ text: 'Cancelar', style: 'cancel' }, { text: 'Descartar', style: 'destructive', onPress: () => { void discardPending(p.client_id).then(() => load()).catch(e => setError(e.message)); } }])} /></View>)}<Button colors={colors} disabled={!online} label="Reintentar envíos" onPress={() => { setBusy(true); void syncReports().then(() => load()).catch(e => { setError(e.message); setBusy(false); }); }} /></Card>}
    <Heading small colors={colors}>Alertas</Heading>{alerts.length ? alerts.map(a => <Card key={a.id} colors={colors}><Text style={{ color: a.priority === 'critical' ? colors.danger : colors.text, fontWeight: a.read ? '400' : '700' }}>{a.message}</Text><Text style={{ color: colors.muted }}>{new Date(a.created_at).toLocaleString('es-MX')}</Text><Button colors={colors} secondary disabled={!online} label="Consultar incidente" onPress={() => void openAlert(a)} /></Card>) : <Text style={{ color: colors.muted }}>No hay alertas registradas.</Text>}
    <Heading small colors={colors}>Tus reportes</Heading>{history.reports.map(r => <Card key={r.report_id} colors={colors}><Text style={{ color: colors.text }}>{r.incident.category} · {{ pending: 'Activo', confirmed: 'Corroborado', resolved: 'Finalizado', expired: 'Vencido', hidden: 'Oculto' }[r.incident.status] ?? r.incident.status}</Text><Button colors={colors} secondary label="Dar seguimiento" onPress={() => onIncident(r.incident, true)} /></Card>)}
    <Heading small colors={colors}>Rutas consultadas</Heading>{history.routes.slice(0, shownRoutes).map(r => <Card key={r.id} colors={colors}><Text style={{ color: colors.text }}>{(r.distance_m/1000).toFixed(1)} km · {Math.round(r.duration_s/60)} min · {r.evaluation.label}</Text><Button colors={colors} secondary label="Consultar ruta" onPress={() => onRoute(r)} /></Card>)}
    {(online || shownRoutes < history.routes.length) && !!history.routes.length && <Button colors={colors} secondary busy={busy} label="Cargar más rutas" onPress={() => void moreRoutes()} />}
  </ScrollView>;
}
