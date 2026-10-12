import AsyncStorage from '@react-native-async-storage/async-storage';
import { File, Paths } from 'expo-file-system';
import * as Crypto from 'expo-crypto';
import { api, raw, sendPhoto } from '../api/client';
import type { Incident, OfflinePackage, PendingReport, ReportResult, Route } from '../api/types';
import { flushReports } from './queueCore';

let scope = '';
let syncing: Promise<PendingReport[]> | null = null;
let queueLock: Promise<void> = Promise.resolve();
async function locked<T>(operation: () => Promise<T>): Promise<T> {
  const previous = queueLock;
  let release!: () => void;
  queueLock = new Promise<void>(resolve => { release = resolve; });
  await previous;
  try { return await operation(); } finally { release(); }
}
const key = (name: string) => 'saferoute.'+scope+'.'+name;
export const setStorageUser = (userId: string) => { scope = userId; };
export async function read<T>(name: string, fallback: T): Promise<T> {
  const data = await AsyncStorage.getItem(key(name));
  return data ? JSON.parse(data) as T : fallback;
}
export async function write(name: string, value: unknown) { await AsyncStorage.setItem(key(name), JSON.stringify(value)); }
export const pendingReports = () => read<PendingReport[]>('queue', []);
export async function enqueue(item: PendingReport) {
  const owner = scope;
  await locked(async () => {
    if (scope !== owner) throw new Error('La sesión cambió. Vuelve a iniciar el reporte.');
    const items = await pendingReports();
    if (!items.some(r => r.client_id === item.client_id)) { items.push(item); await write('queue', items); }
  });
}
export async function keepPhoto(uri: string, ident: string) {
  const destination = new File(Paths.document, 'report-'+scope+'-'+ident+'.jpg');
  new File(uri).copy(destination);
  return destination.uri;
}
export function syncReports() {
  const owner = scope;
  const queueKey = key('queue');
  if (!syncing) syncing = (async () => {
    const initial = await pendingReports();
    return flushReports(initial, item => {
      if (scope !== owner) throw new Error('La sesión cambió. El reporte permanece guardado en su cuenta.');
      const { local_photo, report_id, error, ...data } = item;
      return api<ReportResult>('/incidents', 'POST', data);
    }, async (id, uri) => { if (scope !== owner) throw new Error('La sesión cambió. La foto permanece pendiente.'); await sendPhoto(id, uri); new File(uri).delete(); }, async remaining => locked(async () => {
      // Conservar elementos añadidos mientras se procesa la cola.
      const stored = await AsyncStorage.getItem(queueKey);
      const current = stored ? JSON.parse(stored) as PendingReport[] : [];
      const ids = new Set(initial.map(i => i.client_id));
      await AsyncStorage.setItem(queueKey, JSON.stringify([...remaining, ...current.filter(i => !ids.has(i.client_id))]));
    }));
  })().finally(() => { syncing = null; });
  return syncing;
}
export async function discardPending(clientId: string) {
  // Esperar el envio en curso antes de descartar una entrada local.
  if (syncing) await syncing;
  await locked(async () => {
    const items = await pendingReports();
    const item = items.find(i => i.client_id === clientId);
    if (item?.local_photo) { const file = new File(item.local_photo); if (file.exists) file.delete(); }
    await write('queue', items.filter(i => i.client_id !== clientId));
  });
}
export async function downloadPackage(point: { longitude: number; latitude: number }) {
  const response = await raw('/offline-packages', { method: 'POST', body: JSON.stringify({ ...point, radius_m: 2000 }) });
  const text = await response.text();
  if (new TextEncoder().encode(text).length > 50*1024*1024) throw new Error('El paquete supera 50 MB.');
  const digest = await Crypto.digestStringAsync(Crypto.CryptoDigestAlgorithm.SHA256, text);
  if (digest !== response.headers.get('X-Package-SHA256')) throw new Error('La descarga está incompleta. Reintenta.');
  const parsed = JSON.parse(text) as OfflinePackage;
  const file = new File(Paths.document, 'offline-map.geojson');
  file.write(text);
  return parsed;
}
export function loadPackage(): OfflinePackage | null {
  const file = new File(Paths.document, 'offline-map.geojson');
  try { return file.exists ? JSON.parse(file.textSync()) as OfflinePackage : null; } catch { return null; }
}
export function deletePackage() { const file = new File(Paths.document, 'offline-map.geojson'); if (file.exists) file.delete(); }
export const saveActiveRoute = (route: Route | null) => write('activeRoute', route);
export const cacheIncidents = (items: Incident[]) => write('incidents', items);
