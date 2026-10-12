import React, { useEffect, useRef, useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View, useWindowDimensions } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../api/client';
import type { Incident, OfflinePackage, Point, Route, RouteResults, User } from '../api/types';
import { Button, Card, Field, Heading } from '../components/ui';
import { progress, meters } from '../geolocation/navigation';
import { MapView } from '../maps/MapView';
import type { Palette } from '../theme/colors';

export function MapScreen({ colors, dark, online, location, incidents, pack, user, activeRoute, viewedRoute, changeVersion, onLocation, onIncident, onReport, onPoint, onActive }: { colors: Palette; dark: boolean; online: boolean; location: Point | null; incidents: Incident[]; pack: OfflinePackage | null; user: User; activeRoute: Route | null; viewedRoute: Route | null; changeVersion: number; onLocation: () => Promise<void>; onIncident: (id: string) => void; onReport: () => void; onPoint: (point: Point) => void; onActive: (route: Route | null) => void }) {
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<(Point & { label: string })[]>([]);
  const [destination, setDestination] = useState<Point | null>(null);
  const [routes, setRoutes] = useState<Route[]>(activeRoute ? [activeRoute] : []);
  const [selected, setSelected] = useState<Route | null>(activeRoute);
  const [recommended, setRecommended] = useState<string | null>(null);
  const [warning, setWarning] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [detail, setDetail] = useState(false);
  const [heat, setHeat] = useState<unknown>(null);
  const [heatVisible, setHeatVisible] = useState(false);
  const [localMap, setLocalMap] = useState(false);
  const [recenter, setRecenter] = useState(0);
  const nearest = useRef(0);
  const { width, height } = useWindowDimensions();
  const landscape = width > height;
  const navigation = activeRoute && location ? progress(activeRoute, location, nearest.current) : null;
  if (navigation) nearest.current = navigation.nearestIndex;
  useEffect(() => { nearest.current = 0; if (activeRoute) { setSelected(activeRoute); setRoutes(old => old.some(r => r.id === activeRoute.id) ? old : [activeRoute, ...old]); } }, [activeRoute?.id]);
  useEffect(() => { if (viewedRoute) { setRoutes([viewedRoute]); setSelected(viewedRoute); setDetail(true); setWarning('Ruta histórica. Recalcula con información actual antes de iniciar.'); setDestination({ longitude: viewedRoute.geometry.coordinates.at(-1)![0], latitude: viewedRoute.geometry.coordinates.at(-1)![1] }); } }, [viewedRoute]);
  useEffect(() => {
    if (!activeRoute || !online || !changeVersion) return;
    void api<Route['evaluation']>('/routes/'+activeRoute.id+'/evaluate', 'POST').then(evaluation => {
      const previous = activeRoute.evaluation;
      const changed = (evaluation.critical && !previous.critical) || (evaluation.risk_index ?? 0) > (previous.risk_index ?? 0)+10;
      onActive({ ...activeRoute, evaluation });
      setSelected(old => old?.id === activeRoute.id ? { ...old, evaluation } : old);
      setRoutes(old => old.map(r => r.id === activeRoute.id ? { ...r, evaluation } : r));
      if (changed) {
        setWarning(evaluation.critical ? 'Riesgo crítico en tu ruta. Consulta alternativas; evita continuar hacia la zona afectada.' : 'Cambió el riesgo de tu ruta. Consulta una alternativa.');
        const last = activeRoute.geometry.coordinates.at(-1)!;
        setDestination({ longitude: last[0], latitude: last[1] });
        Alert.alert('Cambio en el recorrido', 'Se detectó nueva información de riesgo. Consulta alternativas para elegir cómo continuar.');
      }
    }).catch(e => setError(e.message));
  }, [changeVersion, online, activeRoute?.id]);
  async function search() {
    setBusy(true); setError('');
    try { const results = await api<(Point & { label: string })[]>('/search?q='+encodeURIComponent(query)); setSearchResults(results); if (!results.length) setError('No se encontraron destinos en Salamanca. Puedes seleccionar uno en el mapa.'); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function calculate() {
    if (!destination || !location) { setError('Activa tu ubicación y selecciona un destino.'); return; }
    setBusy(true); setError('');
    try { const result = await api<RouteResults>('/routes', 'POST', { origin: location, destination, transport: user.preferences.transport }); setRoutes(result.routes); setRecommended(result.recommended_id); setSelected(result.routes.find(r => r.id === result.recommended_id) || result.routes[0] || null); setWarning(result.warning || ''); setDetail(false); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  async function toggleHeat() {
    if (heatVisible) { setHeatVisible(false); return; }
    try { setHeat(await api('/incidents/heatmap')); setHeatVisible(true); } catch (e) { setError((e as Error).message); }
  }
  function start() {
    if (!selected || selected.evaluation.critical) return;
    if (viewedRoute?.id === selected.id) { setError('Recalcula la ruta histórica antes de navegar.'); return; }
    const begin = async () => { if (!location) await onLocation(); onActive(selected); nearest.current = 0; };
    void begin().catch(e => setError(e.message));
  }
  return <View style={{ flex: 1 }}><MapView offline={!online || localMap && !!pack} dark={dark} location={location} routes={routes} selected={selected?.id} incidents={incidents} pack={pack} heat={heatVisible ? heat : null} recenter={recenter} onIncident={onIncident} onDestination={p => { setDestination(p); onPoint(p); setQuery('Punto seleccionado en el mapa'); setSearchResults([]); }} />
    <View style={[styles.search, { backgroundColor: colors.surface, borderColor: colors.border, right: landscape ? width*0.43 : 16 }]}>
      <View style={{ flex: 1 }}><Field colors={colors} label="¿A dónde vas?" value={query} onChangeText={setQuery} placeholder="Busca un destino en Salamanca" onSubmitEditing={() => online && query.length >= 2 && void search()} /></View>
      <Pressable accessibilityRole="button" accessibilityLabel="Buscar destino" disabled={!online || busy || query.length < 2} onPress={() => void search()} style={{ padding: 10 }}><Ionicons name="search" size={24} color={colors.blue} /></Pressable>
    </View>
    <View style={[styles.tools, { right: landscape ? width*0.43 : 16 }]}>{[
      { icon: 'locate-outline' as const, label: 'Centrar mi ubicación', action: () => { void onLocation().then(() => setRecenter(v => v+1)).catch(e => setError(e.message)); } },
      { icon: 'layers-outline' as const, label: heatVisible ? 'Ocultar mapa de calor' : 'Mostrar mapa de calor', action: () => online ? void toggleHeat() : setError('El mapa de calor actualizado requiere conexión.') },
      { icon: 'add' as const, label: 'Reportar incidente', action: onReport },
    ].map(tool => <Pressable key={tool.label} accessibilityRole="button" accessibilityLabel={tool.label} onPress={tool.action} style={[styles.tool, { backgroundColor: colors.surface }]}><Ionicons name={tool.icon} size={24} color={colors.blue} /></Pressable>)}</View>
    <View style={[styles.panel, { backgroundColor: colors.background, borderColor: colors.border, maxHeight: landscape ? height-70 : height*0.48, width: landscape ? width*0.4 : '100%', right: 0, bottom: 0 }]}><ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ padding: 18, gap: 12 }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 10 }}><Heading small colors={colors}>{activeRoute ? 'Tu recorrido' : selected ? 'Elige tu ruta' : 'Explora tu entorno'}</Heading><Text style={{ color: online ? colors.green : colors.danger, fontSize: 12 }}>{online ? 'EN LÍNEA' : 'SIN CONEXIÓN'}</Text></View>
      {pack && online && <Button colors={colors} secondary label={localMap ? 'Usar mapa Azure online' : 'Usar mapa descargado y ahorrar datos'} onPress={() => setLocalMap(v => !v)} />}
      {!online && <Text style={{ color: colors.muted }}>Información guardada. No recibirás nuevos incidentes ni alertas hasta reconectar.</Text>}
      {!selected && !destination && <Text style={{ color: colors.muted }}>Busca un destino o toca el mapa. Consulta incidentes cercanos y elige con más información.</Text>}
      {searchResults.map((p, index) => <Button key={index} colors={colors} secondary label={p.label} onPress={() => { setDestination(p); setQuery(p.label); setSearchResults([]); }} />)}
      {destination && <Button colors={colors} disabled={!online || !location} busy={busy} label={activeRoute ? 'Consultar alternativas' : 'Calcular rutas'} onPress={() => void calculate()} />}
      {!!error && <Text accessibilityRole="alert" style={{ color: colors.danger }}>{error}</Text>}{!!warning && <Text style={{ color: colors.danger }}>{warning}</Text>}
      {navigation && <Card colors={colors}><Text style={{ color: colors.blue, fontSize: 19, fontWeight: '800' }}>{navigation.arrived ? 'Llegaste a tu destino' : navigation.instruction}</Text><Text style={{ color: colors.text }}>{(navigation.remaining_m/1000).toFixed(1)} km restantes · {Math.ceil(navigation.remaining_s/60)} min</Text>{navigation.offRoute && <Text style={{ color: colors.danger }}>Estás fuera del recorrido. {online ? 'Consulta una nueva ruta desde tu ubicación.' : 'Reconecta para recalcular.'}</Text>}<Button colors={colors} secondary label="Finalizar recorrido" onPress={() => onActive(null)} /></Card>}
      {routes.map(r => <Pressable key={r.id} accessibilityRole="button" accessibilityLabel={`Seleccionar ruta de ${Math.round(r.duration_s/60)} minutos`} onPress={() => { setSelected(r); setDetail(false); }} style={{ borderWidth: 1.5, borderColor: selected?.id === r.id ? colors.blue : colors.border, borderRadius: 16, backgroundColor: colors.surface, padding: 14, gap: 5 }}><View style={{ flexDirection: 'row', justifyContent: 'space-between' }}><Text style={{ color: colors.text, fontSize: 19, fontWeight: '800' }}>{Math.ceil(r.duration_s/60)} min</Text><Text style={{ color: colors.muted }}>{(r.distance_m/1000).toFixed(1)} km</Text></View><Text style={{ color: r.evaluation.critical ? colors.danger : colors.blue }}>{r.evaluation.label}{recommended === r.id ? ' · Recomendada' : ''}</Text><Text style={{ color: colors.muted, fontSize: 12 }}>{r.evaluation.safety_index === null ? 'Sin datos suficientes' : `Índice estimado de seguridad: ${r.evaluation.safety_index}/100`}</Text></Pressable>)}
      {selected && <><Button colors={colors} secondary label={detail ? 'Ocultar factores' : 'Ver factores de seguridad'} onPress={() => setDetail(v => !v)} />{detail && <Card colors={colors}><Text style={{ color: colors.muted }}>Estimación para comparar alternativas; no garantiza seguridad. Evaluada: {new Date(selected.evaluation.calculated_at).toLocaleString('es-MX')}</Text>{selected.evaluation.factors.map(f => <Button key={f.incident_id} colors={colors} secondary label={`${f.category} · ${Math.round(f.distance_m)} m · confianza ${Math.round(f.confidence*100)}%`} onPress={() => onIncident(f.incident_id)} />)}{!selected.evaluation.factors.length && <Text style={{ color: colors.muted }}>No hay información suficiente en este recorrido.</Text>}</Card>}{selected.id !== activeRoute?.id && <Button colors={colors} disabled={!online || selected.evaluation.critical} label={activeRoute ? 'Elegir esta alternativa' : 'Iniciar recorrido'} icon="navigate-outline" onPress={start} />}</>}
      {!location && <Button colors={colors} secondary label="Activar mi ubicación" onPress={() => void onLocation().catch(e => setError(e.message))} />}
      {location && !online && pack && meters(pack.metadata.center, [location.longitude, location.latitude]) > pack.metadata.radius_m && <Text style={{ color: colors.danger }}>Estás fuera del sector descargado.</Text>}
    </ScrollView></View>
  </View>;
}
const styles = StyleSheet.create({ search: { position: 'absolute', top: 12, left: 16, padding: 12, borderRadius: 21, borderWidth: 1, flexDirection: 'row', alignItems: 'center', gap: 5 }, tools: { position: 'absolute', top: 125, gap: 10 }, tool: { width: 48, height: 48, borderRadius: 16, alignItems: 'center', justifyContent: 'center', elevation: 2, shadowOpacity: 0.1, shadowRadius: 6 }, panel: { position: 'absolute', borderTopLeftRadius: 26, borderTopRightRadius: 26, borderWidth: 1 } });
