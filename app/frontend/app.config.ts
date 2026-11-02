import type { ExpoConfig } from 'expo/config';

const development = process.env.APP_ENV !== 'production';
if (!development) {
  const apiUrl = new URL(process.env.EXPO_PUBLIC_API_URL || 'https://invalid');
  if (!process.env.EXPO_PUBLIC_API_URL || apiUrl.protocol !== 'https:' || apiUrl.username || apiUrl.password || apiUrl.search || apiUrl.hash || !['', '/'].includes(apiUrl.pathname)) {
    throw new Error('Configura EXPO_PUBLIC_API_URL con la URL base HTTPS del backend antes de compilar.');
  }
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(process.env.EXPO_PUBLIC_EAS_PROJECT_ID || '')) {
    throw new Error('Configura EXPO_PUBLIC_EAS_PROJECT_ID con el UUID de tu proyecto Expo antes de compilar.');
  }
}
const config: ExpoConfig = {
  name: 'SafeRouteAI', slug: 'saferoute-ai', version: '1.0.0',
  orientation: 'default', userInterfaceStyle: 'automatic',
  scheme: 'saferoute',
  ios: { bundleIdentifier: 'com.saferouteai.mobile', supportsTablet: true,
    infoPlist: { NSAppTransportSecurity: development ? { NSAllowsArbitraryLoads: true } : {}, NSLocationWhenInUseUsageDescription: 'Tu ubicación permite consultar rutas y alertas cercanas mientras usas la app.' } },
  android: { package: 'com.saferouteai.mobile', allowBackup: false, permissions: ['ACCESS_COARSE_LOCATION', 'ACCESS_FINE_LOCATION'],
    ...(development ? { usesCleartextTraffic: true } : {}) },
  plugins: ['expo-secure-store', 'expo-notifications', ['expo-build-properties', { android: { usesCleartextTraffic: development, minSdkVersion: 24 }, ios: { deploymentTarget: '16.4' } }], ['expo-location', { locationWhenInUsePermission: 'Permite usar tu ubicación para rutas y alertas cercanas.' }], ['expo-image-picker', { photosPermission: 'Selecciona una fotografía opcional para tu reporte.', cameraPermission: 'Adjunta una fotografía solo si puedes hacerlo con seguridad.', microphonePermission: false }]],
  extra: { eas: { projectId: process.env.EXPO_PUBLIC_EAS_PROJECT_ID || '' } },
};
export default config;
