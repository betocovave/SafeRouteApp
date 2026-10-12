import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { WebView } from 'react-native-webview';
import { API, accessToken } from '../api/client';
import type { Incident, OfflinePackage, Point, Route } from '../api/types';
import { mapHTML } from './html';

export function MapView({ offline, dark, location, routes, selected, incidents, pack, heat, recenter, onIncident, onDestination }: { offline: boolean; dark: boolean; location: Point | null; routes: Route[]; selected?: string; incidents: Incident[]; pack: OfflinePackage | null; heat: unknown; recenter: number; onIncident: (id: string) => void; onDestination: (point: Point) => void }) {
  const ref = useRef<WebView>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const lastCenter = useRef(-1);
  const source = useMemo(() => ({ html: mapHTML(offline, dark), baseUrl: API }), [offline, dark]);
  useEffect(() => { setReady(false); setError(''); lastCenter.current = -1; }, [source]);
  useEffect(() => {
    if (!ready || offline) return;
    const timer = setInterval(() => ref.current?.injectJavaScript(`window.setSessionToken && window.setSessionToken(${JSON.stringify(accessToken())});true;`), 15000);
    return () => clearInterval(timer);
  }, [ready, offline]);
  useEffect(() => {
    if (!ready) return;
    const data = { api: API, token: accessToken(), location, routes, selected, incidents, package: pack, heat, recenter: recenter !== lastCenter.current };
    ref.current?.injectJavaScript(`window.receive && window.receive(${JSON.stringify(data).replace(/</g, '\\u003c')});true;`);
    lastCenter.current = recenter;
  }, [ready, location, routes, selected, incidents, pack, heat, recenter]);
  return <View style={{ flex: 1 }}><WebView ref={ref} source={source} originWhitelist={['*']} javaScriptEnabled scrollEnabled={false} mixedContentMode="compatibility" onMessage={event => {
    try {
      const data = JSON.parse(event.nativeEvent.data);
      if (data.type === 'ready') setReady(true);
      if (data.type === 'error') setError(data.message);
      if (data.type === 'incident') onIncident(data.id);
      if (data.type === 'destination') onDestination({ longitude: data.longitude, latitude: data.latitude });
    } catch { setError('No se pudo actualizar el mapa.'); }
  }} onError={() => setError('No se pudo cargar el mapa.')} onShouldStartLoadWithRequest={request => request.url === 'about:blank' || request.url.startsWith(API) || request.url.startsWith('https://atlas.microsoft.com/')} />
  {(error || offline && !pack) ? <View pointerEvents="none" style={{ position: 'absolute', top: 120, margin: 18, backgroundColor: dark ? '#12263a' : '#fff', padding: 14, borderRadius: 15 }}><Text style={{ color: dark ? '#e5effc' : '#12324d' }}>{error || 'No tienes un mapa descargado. La ruta guardada y el GPS siguen disponibles.'}</Text></View> : null}</View>;
}
