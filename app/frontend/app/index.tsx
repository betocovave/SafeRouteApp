import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, AppState, Platform, Pressable, Text, View, useColorScheme } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import { Ionicons } from '@expo/vector-icons';
import NetInfo from '@react-native-community/netinfo';
import * as Location from 'expo-location';
import * as Notifications from 'expo-notifications';
import * as SecureStore from 'expo-secure-store';
import Constants from 'expo-constants';
import { api, API, ApiError, restoreSession, setExpiredHandler } from '../src/api/client';
import type { AppAlert, Category, Incident, OfflinePackage, Point, Route, User } from '../src/api/types';
import { palettes } from '../src/theme/colors';
import { loadPackage, read, saveActiveRoute, setStorageUser, syncReports, write } from '../src/storage/local';
import { AuthScreen } from '../src/features/AuthScreen';
import { MapScreen } from '../src/features/MapScreen';
import { ReportScreen } from '../src/features/ReportScreen';
import { IncidentDetail } from '../src/features/IncidentDetail';
import { ActivityScreen } from '../src/features/ActivityScreen';
import { SettingsScreen } from '../src/features/SettingsScreen';
import { AdminScreen } from '../src/features/AdminScreen';

Notifications.setNotificationHandler({ handleNotification: async () => ({ shouldPlaySound: true, shouldSetBadge: false, shouldShowBanner: true, shouldShowList: true }) });
type Tab = 'map' | 'report' | 'activity' | 'settings' | 'admin';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [online, setOnline] = useState(true);
  const [visible, setVisible] = useState(AppState.currentState === 'active');
  const [location, setLocation] = useState<Point | null>(null);
  const [reportPoint, setReportPoint] = useState<Point | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [detail, setDetail] = useState<Incident | null>(null);
  const [pack, setPack] = useState<OfflinePackage | null>(null);
  const [activeRoute, setActiveRoute] = useState<Route | null>(null);
  const [viewedRoute, setViewedRoute] = useState<Route | null>(null);
  const [tab, setTab] = useState<Tab>('map');
  const [status, setStatus] = useState('');
  const [changeVersion, setChangeVersion] = useState(0);
  const systemTheme = useColorScheme();
  const dark = user?.preferences.theme === 'dark' || (user?.preferences.theme !== 'light' && systemTheme === 'dark');
  const colors = dark ? palettes.dark : palettes.light;
  const watcher = useRef<Location.LocationSubscription | null>(null);
  const tracking = useRef(false);
  const state = useRef({ online, activeRoute, user, visible });
  state.current = { online, activeRoute, user, visible };
  const position = useRef<Point | null>(null);
  const lastSent = useRef(0);

  const rememberUser = useCallback(async (value: User) => {
    setStorageUser(value.id); setUser(value);
    await SecureStore.setItemAsync('saferoute.profile', JSON.stringify(value));
  }, []);
  const loadSession = useCallback(async (allowOffline = false) => {
    let value: User;
    try { value = await api<User>('/users/me'); }
    catch (e) {
      const cached = allowOffline ? await SecureStore.getItemAsync('saferoute.profile') : null;
      if (!cached || !(e instanceof ApiError) || e.status !== 0) throw e;
      value = JSON.parse(cached) as User; setStatus('Servidor sin conexión. Mostrando información guardada.');
    }
    await rememberUser(value);
    setCategories(await read<Category[]>('categories', []));
    setIncidents(await read<Incident[]>('incidents', []));
    const route = await read<Route | null>('activeRoute', null);
    setActiveRoute(route);
    setPack(loadPackage());
  }, [rememberUser]);
  useEffect(() => {
    setExpiredHandler(() => { setUser(null); tracking.current = false; watcher.current?.remove(); watcher.current = null; setStatus('Tu sesión expiró. Inicia sesión para continuar.'); });
    void restoreSession().then(exists => exists ? loadSession(true) : undefined).catch(e => setStatus(e.message)).finally(() => setLoading(false));
    const net = NetInfo.addEventListener(value => setOnline(value.isConnected === true && value.isInternetReachable !== false));
    const appState = AppState.addEventListener('change', value => {
      setVisible(value === 'active');
      if (value !== 'active') { watcher.current?.remove(); watcher.current = null; if (state.current.user && state.current.online) void api('/locations', 'DELETE').catch(() => undefined); }
    });
    return () => { net(); appState.remove(); watcher.current?.remove(); };
  }, [loadSession]);

  const refreshIncidents = useCallback(async () => {
    const p = position.current;
    if (!p || !state.current.online || !state.current.user) return;
    try { const items = await api<Incident[]>(`/incidents?longitude=${p.longitude}&latitude=${p.latitude}`); setIncidents(items); await write('incidents', items); }
    catch (e) { setStatus((e as Error).message); }
  }, []);

  async function startWatcher() {
    if (watcher.current || !state.current.visible) return;
    watcher.current = await Location.watchPositionAsync({ accuracy: Location.Accuracy.High, timeInterval: 5000, distanceInterval: 5 }, value => {
      if (!state.current.visible) return;
      const p = { longitude: value.coords.longitude, latitude: value.coords.latitude };
      position.current = p; setLocation(p);
      if (state.current.online && Date.now()-lastSent.current >= 5000) {
        lastSent.current = Date.now();
        void api('/locations', 'POST', { ...p, accuracy: value.coords.accuracy ?? 10000, route_id: state.current.activeRoute?.id || null }).then(refreshIncidents).catch(e => setStatus(e.message));
      }
    });
  }
  async function activateLocation() {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (!permission.granted) throw new Error('Ubicación denegada. Puedes seleccionar puntos en el mapa; la navegación necesita permiso de ubicación.');
    const value = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
    const p = { longitude: value.coords.longitude, latitude: value.coords.latitude };
    position.current = p; setLocation(p); setReportPoint(null); tracking.current = true;
    if (online) await api('/locations', 'POST', { ...p, accuracy: value.coords.accuracy ?? 10000, route_id: activeRoute?.id || null });
    await refreshIncidents(); await startWatcher(); setStatus('');
  }
  useEffect(() => {
    if (visible && user && tracking.current) void startWatcher().catch(e => setStatus(e.message));
  }, [visible, user?.id]);
  useEffect(() => {
    if (!user || !online || !visible) return;
    void api<Category[]>('/categories').then(async items => { setCategories(items); await write('categories', items); }).catch(e => setStatus(e.message));
    void syncReports().then(refreshIncidents).catch(e => setStatus(e.message));
    void refreshIncidents();
  }, [online, visible, user?.id, refreshIncidents]);
  useEffect(() => {
    if (!user || !online || !visible) return;
    let disposed = false;
    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout>;
    async function connect() {
      try {
        const { ticket } = await api<{ ticket: string }>('/realtime/ticket', 'POST');
        if (disposed) return;
        socket = new WebSocket(API.replace(/^http/, 'ws')+'/api/v1/realtime');
        socket.onopen = () => socket?.send(JSON.stringify({ ticket }));
        socket.onmessage = e => { try {
          const event = JSON.parse(e.data);
          if (event.type === 'incidents_changed' || event.type === 'alert') { setChangeVersion(v => v+1); void refreshIncidents(); }
          if (event.type === 'alert') void api<AppAlert[]>('/alerts').then(async alerts => {
            const alert = alerts.find(a => a.id === event.id);
            if (alert) setStatus(alert.message);
            await write('alerts', alerts);
          }).catch(e => setStatus(e.message));
        } catch { setStatus('No se pudo leer una actualización.'); } };
        socket.onclose = () => { if (!disposed) retry = setTimeout(() => void connect(), 5000); };
      } catch { if (!disposed) retry = setTimeout(() => void connect(), 5000); }
    }
    void connect();
    const pulse = setInterval(() => { if (socket?.readyState === WebSocket.OPEN) socket.send('ping'); void api('/users/me').catch(() => undefined); }, 60000);
    return () => { disposed = true; clearTimeout(retry); clearInterval(pulse); socket?.close(); };
  }, [online, visible, user?.id, refreshIncidents]);

  async function openIncident(id: string) {
    try { const value = online ? await api<Incident>('/incidents/'+id) : incidents.find(i => i.id === id); if (value) setDetail(value); else setStatus('El incidente no está disponible en la información guardada.'); }
    catch (e) { setStatus((e as Error).message); }
  }
  useEffect(() => {
    const listener = Notifications.addNotificationResponseReceivedListener(value => { const id = value.notification.request.content.data?.incident_id; if (typeof id === 'string' && state.current.user) void openIncident(id); });
    return () => listener.remove();
  }, [online, incidents]);
  async function notifications() {
    if (Platform.OS === 'android') await Notifications.setNotificationChannelAsync('default', { name: 'Alertas de seguridad', importance: Notifications.AndroidImportance.HIGH });
    const permission = await Notifications.requestPermissionsAsync();
    if (!permission.granted) throw new Error('Notificaciones denegadas. Las alertas seguirán disponibles dentro de la app.');
    const projectId = Constants.expoConfig?.extra?.eas?.projectId;
    if (!projectId) throw new Error('Las notificaciones del dispositivo aún no están disponibles en esta versión. Puedes consultar las alertas dentro de la app.');
    const token = await Notifications.getExpoPushTokenAsync({ projectId });
    await api('/devices', 'POST', { token: token.data });
  }
  function chooseActive(route: Route | null) { setActiveRoute(route); setViewedRoute(null); void saveActiveRoute(route); }
  function logoutLocal() { setUser(null); setDetail(null); setActiveRoute(null); setViewedRoute(null); setReportPoint(null); setTab('map'); setIncidents([]); setCategories([]); setLocation(null); position.current = null; setStorageUser(''); tracking.current = false; watcher.current?.remove(); watcher.current = null; void SecureStore.deleteItemAsync('saferoute.profile'); }
  const tabs: { id: Tab; title: string; icon: keyof typeof Ionicons.glyphMap }[] = [{ id: 'map', title: 'Mapa', icon: 'map-outline' }, { id: 'report', title: 'Reportar', icon: 'add-circle-outline' }, { id: 'activity', title: 'Actividad', icon: 'notifications-outline' }, { id: 'settings', title: 'Perfil', icon: 'person-outline' }];
  return <SafeAreaProvider><SafeAreaView style={{ flex: 1, backgroundColor: colors.background }}><StatusBar style={dark ? 'light' : 'dark'} />
    {loading ? <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}><ActivityIndicator color={colors.blue} /></View> : !user ? <AuthScreen colors={colors} onSession={() => loadSession(false)} /> : <>
      {!!status && <Pressable accessibilityLabel="Cerrar aviso" onPress={() => setStatus('')} style={{ padding: 12, backgroundColor: colors.pale }}><Text style={{ color: colors.text, fontSize: 12 }}>{status} · Toca para cerrar</Text></Pressable>}
      <View style={{ flex: 1 }}>
        <View style={{ flex: 1, display: tab === 'map' && !detail ? 'flex' : 'none' }}><MapScreen colors={colors} dark={dark} online={online} location={location} incidents={incidents} pack={pack} user={user} activeRoute={activeRoute} viewedRoute={viewedRoute} changeVersion={changeVersion} onLocation={activateLocation} onIncident={id => void openIncident(id)} onReport={() => setTab('report')} onPoint={setReportPoint} onActive={chooseActive} /></View>
        {detail ? <IncidentDetail colors={colors} online={online} incident={detail} onBack={() => setDetail(null)} onUpdate={value => { setDetail(value); void refreshIncidents(); }} /> : <>
          {tab === 'report' && <ReportScreen colors={colors} point={reportPoint || location} categories={categories} online={online} onDone={() => { setTab('map'); void refreshIncidents(); }} />}
          {tab === 'activity' && <ActivityScreen colors={colors} online={online} changeVersion={changeVersion} onIncident={setDetail} onRoute={route => { setViewedRoute(route); setTab('map'); }} />}
          {tab === 'settings' && <SettingsScreen colors={colors} user={user} online={online} point={location} pack={pack} onUser={value => void rememberUser(value)} onPack={setPack} onLogout={logoutLocal} onAdmin={() => setTab('admin')} onNotifications={notifications} />}
          {tab === 'admin' && <AdminScreen colors={colors} onBack={() => setTab('settings')} />}
        </>}
      </View>
      <View style={{ flexDirection: 'row', backgroundColor: colors.surface, borderTopColor: colors.border, borderTopWidth: 1, paddingTop: 9, paddingBottom: 7 }}>{tabs.map(t => <Pressable key={t.id} accessibilityRole="tab" accessibilityState={{ selected: tab === t.id }} accessibilityLabel={t.title} onPress={() => { setDetail(null); setTab(t.id); }} style={{ flex: 1, alignItems: 'center', gap: 4, padding: 5 }}><Ionicons name={t.icon} size={24} color={tab === t.id ? colors.blue : colors.muted} /><Text style={{ color: tab === t.id ? colors.blue : colors.muted, fontSize: 11, fontWeight: '600' }}>{t.title}</Text></Pressable>)}</View>
    </>}
  </SafeAreaView></SafeAreaProvider>;
}
