import * as SecureStore from 'expo-secure-store';
import Constants from 'expo-constants';
import type { Tokens } from './types';
import { serverUrl } from './serverUrl';

export const API = serverUrl(process.env.EXPO_PUBLIC_API_URL, __DEV__, Constants.expoConfig?.hostUri);
let tokens: Tokens | null = null;
let expiresAt = 0;
let refreshPromise: Promise<void> | null = null;
let onExpired: (() => void) | null = null;
export const accessToken = () => tokens?.access_token || '';
export const setExpiredHandler = (handler: () => void) => { onExpired = handler; };

export async function saveTokens(value: Tokens | null) {
  tokens = value;
  expiresAt = value ? Date.now() + (value.expires_in ?? 900)*1000 : 0;
  if (value) await SecureStore.setItemAsync('saferoute.session', JSON.stringify({ ...value, recovery_code: undefined, expiresAt }));
  else await SecureStore.deleteItemAsync('saferoute.session');
}
export async function restoreSession() {
  const value = await SecureStore.getItemAsync('saferoute.session');
  tokens = value ? JSON.parse(value) as Tokens : null;
  expiresAt = value ? (JSON.parse(value).expiresAt ?? 0) : 0;
  return !!tokens;
}
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
async function responseError(response: Response) {
  const body = await response.json().catch(() => ({}));
  return new ApiError(response.status, typeof body.detail === 'string' ? body.detail : response.status === 422 ? 'Revisa los campos y vuelve a intentar.' : 'No se pudo completar la operación.');
}
async function rotate() {
  if (!refreshPromise) refreshPromise = (async () => {
    if (!tokens) throw new ApiError(401, 'Inicia sesión.');
    const response = await fetch(API+'/api/v1/auth/refresh', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: tokens.refresh_token }) });
    if (!response.ok) {
      if (response.status === 401) { await saveTokens(null); onExpired?.(); }
      throw await responseError(response);
    }
    await saveTokens(await response.json() as Tokens);
  })().finally(() => { refreshPromise = null; });
  return refreshPromise;
}
export async function raw(path: string, options: RequestInit = {}, retry = true): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), path.includes('offline') ? 30000 : 15000);
  try {
    if (tokens && expiresAt < Date.now()+60000 && !path.startsWith('/auth/')) await rotate();
    const sentRefresh = tokens?.refresh_token;
    const response = await fetch(API+'/api/v1'+path, { ...options, signal: controller.signal, headers: { ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(tokens ? { Authorization: 'Bearer '+tokens.access_token } : {}), ...options.headers } });
    if (response.status === 401 && retry && tokens && tokens.refresh_token === sentRefresh && !path.startsWith('/auth/')) { await rotate(); return raw(path, options, false); }
    if (!response.ok) throw await responseError(response);
    return response;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, 'Sin conexión con el servidor. Revisa tu red e inténtalo nuevamente.');
  } finally { clearTimeout(timer); }
}
export async function api<T>(path: string, method = 'GET', data?: unknown): Promise<T> {
  const response = await raw(path, { method, ...(data === undefined ? {} : { body: JSON.stringify(data) }) });
  return response.status === 204 ? undefined as T : await response.json() as T;
}
export async function sendPhoto(reportId: string, uri: string) {
  const form = new FormData();
  form.append('file', { uri, name: 'incident.jpg', type: 'image/jpeg' } as unknown as Blob);
  return raw('/reports/'+reportId+'/photo', { method: 'POST', body: form });
}
