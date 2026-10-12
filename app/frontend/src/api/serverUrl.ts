/** In local development, the API runs on the same computer as Metro. */
export function serverUrl(configured: string | undefined, development: boolean, hostUri?: string | null): string {
  if (configured?.trim()) return configured.trim().replace(/\/$/, '');
  if (development && hostUri) {
    const host = new URL(hostUri.includes('://') ? hostUri : `http://${hostUri}`).hostname;
    return `http://${host}:8000`;
  }
  return 'http://localhost:8000';
}
