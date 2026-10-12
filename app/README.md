# SafeRouteAI

Aplicación móvil de rutas, reportes ciudadanos y alertas para Salamanca, Guanajuato.
React Native + Expo + TypeScript; Python + FastAPI; PostgreSQL + PostGIS;
Azure Maps; Azure Blob Storage/Azurite; cartografía OSM local para uso offline.

## Inicio rápido

Requisitos: Python 3.12+, Node 22+, PowerShell, Docker Desktop con contenedores Linux.
Plataformas configuradas: Android 7.0+ (API 24) e iOS 16.4+; aceptación en dispositivos pendiente.
Para ejecutar Android: Android Studio/SDK y un dispositivo o emulador.
Para compilar iOS localmente: macOS con Xcode. También puedes generar builds en tu cuenta Expo.

Desde esta carpeta (`app`):

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt
./infrastructure/setup.ps1
docker compose -f infrastructure/compose.yaml up -d
.venv/Scripts/python.exe -m alembic -c backend/alembic.ini upgrade head
.venv/Scripts/python.exe -m backend.cli seed
.venv/Scripts/python.exe -m backend.cli prepare-osm
.venv/Scripts/python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**TU API KEY SE COLOCA EN `app/backend/.env`, variable `AZURE_MAPS_API_KEY`.**
La plantilla documentada es `backend/.env.example`. La clave no se coloca en el frontend.
Si tu credencial es SAS, usa `AZURE_MAPS_AUTH_MODE=sas` y `AZURE_MAPS_SAS_TOKEN`.
El script genera un secreto JWT aleatorio y configura Azurite. No sobrescribe un `.env` existente.
Las credenciales públicas del emulador se usan exclusivamente en desarrollo.

En otra terminal:

```powershell
cd frontend
Copy-Item .env.example .env
# EXPO_PUBLIC_API_URL vacio detecta la computadora desde Expo en la red Wi-Fi.
npm ci
npm run android
```

El teléfono y la computadora deben compartir red. `localhost` en el teléfono no apunta al backend.
Para abrir la interfaz con Expo Go instalado en el teléfono, ejecuta `npm.cmd start` desde
`frontend` y escanea el QR nuevo: en Android, desde Expo Go; en iPhone, desde la cámara.
El comando fuerza Expo Go y desactiva el selector web con `EXPO_NO_REDIRECT_PAGE=1`.
El QR contiene un enlace `exp://` que abre la aplicación directamente en Expo Go.
La dirección de red que muestra Metro es normal; no necesitas escribirla en el teléfono.
Si ya tenías Metro abierto, detenlo con Ctrl+C antes de volver a iniciar.
El inicio de sesión y las funciones conectadas requieren el backend configurado y accesible.
Con Python ya instalado en `.venv` y Docker Desktop abierto, puedes iniciar la base de datos,
aplicar migraciones, preparar categorías e iniciar la API con un solo comando desde `app`:

```powershell
powershell -ExecutionPolicy Bypass -File .\infrastructure\start-backend.ps1
```

Deja esa terminal abierta. En otra terminal, desde `app/frontend`, ejecuta `npm.cmd start`.
Al usar Expo por la misma red Wi-Fi, el frontend detecta la computadora de Metro en el puerto
8000. Para Metro con `--tunnel`, un backend remoto o producción, configura explícitamente
`EXPO_PUBLIC_API_URL`: el túnel de Expo no publica la API de Python.
Las notificaciones push requieren un build de desarrollo instalado; para ese caso usa
`npm run start:dev` después de `npm run android` o de instalar tu build iOS.
Abre `http://localhost:8000/docs` para la API y `/ready` para comprobar la base de datos.

## Funciones

- Registro, sesiones JWT, perfil y recuperación con código privado de un solo uso.
- Búsqueda, alternativas para automóvil/caminata, índice explicable y navegación visual.
- Reportes de delitos, eventos, iluminación y vialidad, con fotografía opcional.
- Corroboración cercana, estados, caducidad, alertas y mapa de calor histórico.
- Historial, preferencias, modo claro/oscuro y administración por rol.
- Sector OSM descargable de 2 km y hasta 50 MB; continuidad de una ruta ya iniciada.
- Cola local de reportes, sincronización idempotente y reintento independiente de fotografías.

El GPS se utiliza solo con permiso y mientras la app está visible. Sin conexión no se reciben nuevas
alertas ni se calculan nuevas rutas. Un índice es una estimación, nunca una garantía de seguridad.
El proyecto no precarga incidentes ficticios y no utiliza los modelos sintéticos de los prototipos.

## Administrador y notificaciones

```powershell
.venv/Scripts/python.exe -m backend.cli create-admin
```

El comando solicita nombre, correo y contraseña. No existe administrador ni contraseña predeterminada.
Para push, configura `EXPO_PUBLIC_EAS_PROJECT_ID` en el frontend, las credenciales APNs/FCM de tu
proyecto Expo y activa las notificaciones desde Perfil. Puedes seguir usando alertas internas sin push.

## Validación

```powershell
.venv/Scripts/python.exe -m pytest backend/tests -q
# Solo con una base PostGIS aislada de pruebas:
$env:TEST_DATABASE_URL='postgresql+psycopg://usuario:clave@localhost:5432/saferoute_test'
.venv/Scripts/python.exe -m pytest backend/tests/test_postgis_integration.py -q
cd frontend
npm run typecheck
npm test
npx expo export --platform android --platform ios --output-dir dist
```

Los bundles Android/iOS fueron compilados; no son APK/IPA ni sustituyen pruebas en teléfonos.
Consulta `docs/VALIDATION.md` para los resultados y las validaciones pendientes con servicios externos.

## Contratos y documentación

```powershell
# Desde app, después de cambiar contratos:
.venv/Scripts/python.exe -m backend.cli export-openapi
cd frontend
npm run generate:api
```

`docs/openapi.json` es el contrato exportado. `frontend/src/api/generated.ts` se genera desde ese
contrato; el generador usa un entorno temporal de TypeScript 5, separado del TypeScript 6 de Expo.

- [Manual técnico y de usuario](docs/manual.md)
- [Documentación PDF](docs/output/pdf/SafeRouteAI-manual.pdf)
- [Matriz RF/RNF](docs/requirements.csv)
- [Validación](docs/VALIDATION.md)

## Producción

Configura `ENVIRONMENT=production`, HTTPS, PostgreSQL/PostGIS, secretos propios, CORS exacto,
Blob privado y copias de seguridad de la base y los blobs. Usa `APP_ENV=production` para el móvil.
Construye el backend con `docker build -f infrastructure/Dockerfile -t saferoute-backend .`.
El proceso de API debe usar **un solo worker**: el hub de WebSocket, los tickets y el control de
frecuencia son locales al proceso. Una ampliación a múltiples réplicas necesita coordinación externa.
No expongas las credenciales de desarrollo de PostgreSQL/Azurite ni los puertos de Compose a Internet.

Conserva la atribución OpenStreetMap/ODbL y la de Azure Maps. Las redes OSM se preparan en el servidor
una vez; el móvil descarga un GeoJSON generado por este backend, no teselas Azure ni del servidor OSM.
