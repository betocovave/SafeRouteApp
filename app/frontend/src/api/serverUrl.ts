/** In local development, the API runs on the same computer as Metro. */
export function serverUrl(configured: string | undefined, development: boolean, hostUri?: string | null): string {
  if (configured?.trim()) {
    const url = new URL(configured.trim());
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || !['', '/'].includes(url.pathname)) {
      throw new Error('EXPO_PUBLIC_API_URL debe ser la URL base HTTP/HTTPS del backend, sin /api/v1 ni credenciales.');
    }
    if (!development && url.protocol !== 'https:') throw new Error('Configura EXPO_PUBLIC_API_URL con la URL HTTPS de tu backend.');
    return url.origin;
  }
  if (development && hostUri) {
    const host = new URL(hostUri.includes('://') ? hostUri : `http://${hostUri}`).hostname;
    if (host.endsWith('.exp.direct') || host.endsWith('.ngrok.io') || host.endsWith('.ngrok-free.app')) {
      throw new Error('Expo está en modo túnel. Inicia infrastructure/start-mobile.ps1 para conectar también el backend.');
    }
    return `http://${host}:8000`;
  }
  if (!development) throw new Error('Configura EXPO_PUBLIC_API_URL con la URL HTTPS de tu backend.');
  return 'http://localhost:8000';
}
