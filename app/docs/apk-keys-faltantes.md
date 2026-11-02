# Qué falta para generar el APK sin laptop

Para el APK no falta ninguna key de Azure Maps, Blob ni JWT. Faltan una cuenta de Expo, el UUID de su proyecto y la URL pública del backend, que todavía no existe.

## Lo que ya existe en `backend/.env`

`AZURE_MAPS_API_KEY`, `JWT_SECRET` y `AZURE_BLOB_CONNECTION_STRING` tienen valor. Los grafos de Salamanca también están. Esos valores son del entorno local: la cadena de Blob seguramente apunta a Azurite, así que no se reutiliza en producción.

## Lo que falta

| Qué | Para qué | De dónde sale |
|---|---|---|
| Cuenta Expo y `EXPO_PUBLIC_EAS_PROJECT_ID` (UUID) | `app.config.ts` aborta el build sin él | Crear el proyecto `saferoute-ai` en expo.dev y copiar su Project ID. No es el UUID de Azure Maps. |
| `EXPO_PUBLIC_API_URL` (https) | Backend al que se conecta el APK | La genera `deploy.sh` al desplegar en Azure Container Apps. Sin ella el APK no funciona sin laptop. |
| `POSTGRES_PASSWORD` (16 caracteres o más) | `deploy.sh` la exige | Se inventa y se guarda en un gestor de secretos. |
| `JWT_SECRET` de producción (32 caracteres o más) | Firma los tokens en Azure | Puede ser el actual. Guardarlo: si cambia, se invalidan las sesiones. |
| Keystore de Android | Firmar el APK | EAS lo genera la primera vez que se construye. |

Opcional: `EXPO_ACCESS_TOKEN`, solo para notificaciones push. La cadena de Blob de producción la crea `deploy.sh`.

## Herramientas

- `az` no existe en Git Bash (no se probó en PowerShell).
- `eas-cli` no está instalado ni con sesión iniciada: `npx --yes eas-cli login`.
- Docker y WSL o Git Bash para el script de despliegue.

## Bloqueo que no es una key

`deploy.sh` se niega a correr con cambios sin commitear en `app/`, y hay unos 60 archivos modificados. Hay que hacer commit primero.

## Orden

1. `az login`
2. `bash infrastructure/azure/deploy.sh`
3. `bash infrastructure/azure/configure-eas.sh`
4. `npx --yes eas-cli build --platform android --profile preview` (produce el `.apk`)

Comandos exactos en `deploy.md`. Esos pasos se hacen una sola vez; después el APK no necesita comandos ni laptop.

## Costo

PostgreSQL B1ms, ACR y Container Apps gastan crédito de Azure for Students aunque no haya usuarios. Revisar el saldo antes de desplegar.

## No verificado

Nada se probó contra Azure ni contra Expo. Solo se leyó la configuración y se revisó qué keys tienen valor.
