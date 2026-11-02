# SafeRouteAI: Azure Container Apps y APK

Destino acordado: Azure for Students, **West US 2** (`westus2`). Azure Maps existente:
`saferoute-maps`. El UUID proporcionado para Maps no es una API key ni el ID de Expo.
Blob se crea en este despliegue. No se modifican las herramientas locales
`infrastructure/start-*.ps1` ni `allow-phone.ps1`.

## Arquitectura y límites iniciales

- `infrastructure/azure/infra.bicep`: red privada, PostgreSQL 16 Flexible Server
  Burstable B1ms (32 GiB, respaldos automáticos de 7 días, sin alta disponibilidad),
  extensión PostGIS permitida, base `saferoute`, Blob privado con HTTPS, ACR Basic,
  identidad con AcrPull y entorno Container Apps Consumption.
- `app.bicep`: ingress público de Azure con TLS administrado, redirección HTTP a
  HTTPS, proxy Nginx en 8080 y Uvicorn escuchando **solo en 127.0.0.1:8000**.
  Los contenedores de la réplica comparten red. `FORWARDED_ALLOW_IPS=127.0.0.1`;
  no se publica 8000 ni se confía en `*`.
- El proxy añade HSTS (`max-age=31536000`), `X-Frame-Options: DENY` y
  `Referrer-Policy: no-referrer`, también en errores. Conserva únicamente la IP
  derecha de `X-Forwarded-For`, añadida por Azure. No exponer Nginx directamente
  ni reutilizar esta regla detrás de otro ingress sin revisar la cadena de confianza.
- Una réplica mínima y máxima, un worker, 1 vCPU/2 GiB en total. Mantiene activos
  los trabajos periódicos. El hub WebSocket y los límites están en memoria: no
  aumentar réplicas sin adaptar esos componentes. El modo de revisión es Single;
  puede haber solapamiento temporal durante un rollout.
- PostgreSQL solo es accesible dentro de la VNet y exige TLS en la conexión.
  Blob permite operaciones autenticadas y no permite contenedores públicos.
  Los secretos se guardan como secretos de Container Apps; Bicep los recibe con
  parámetros `@secure()` leídos desde variables de entorno.
- Los logs de consola se consultan en vivo; no se provisiona Log Analytics ni
  retención histórica de logs. CORS queda vacío para el cliente nativo. Si se
  publica una web, exportar `CORS_ORIGINS` con sus orígenes HTTPS separados por coma.

Estos recursos consumen crédito de Students aunque no haya usuarios. Antes de
aprovisionar, verificar crédito, permisos de asignación de roles, políticas y
disponibilidad de B1ms/PostgreSQL/Container Apps en la suscripción y región.
La elección de región no confirma las cuotas de cada servicio.

## 1. Preparar herramientas y cuentas

Los comandos de despliegue usan **Bash** (WSL con Docker Desktop integrado o Linux),
Git, Docker Linux, Azure CLI actual con Bicep y `curl`. Para EAS: Node/npm y sesión
Expo. En Windows puede usarse Git Bash si `az`, Docker y Node están en su PATH.
Ejecutar desde `SafeRouteAI/app`; en WSL:

```bash
cd /mnt/c/Users/Alberto/OneDrive/Documents/SafeRouteAI/app
az login
az account list --query "[].{nombre:name,id:id}" --output table
export AZURE_SUBSCRIPTION_ID='ID_REAL_DE_AZURE_FOR_STUDENTS'
export AZURE_RESOURCE_GROUP='saferoute-prod'
export AZURE_PREFIX='saferoute'
export AZURE_LOCATION='westus2'
az account set --subscription "$AZURE_SUBSCRIPTION_ID"
az bicep install
az extension add --name containerapp --upgrade
for provider in Microsoft.App Microsoft.DBforPostgreSQL Microsoft.Storage Microsoft.ContainerRegistry Microsoft.Network Microsoft.ManagedIdentity; do
  az provider register --namespace "$provider" --wait
done
```

No publicar desde el árbol actual sin revisar y autorizar un commit. El script
rechaza cambios pendientes dentro de `app/`, porque etiquetar código no guardado
con el hash de un commit sería engañoso. No hace commits ni pushes. Los cambios
fuera de `app/` no se incluyen. Si existe `.git/index.lock`, identificar primero
el proceso dueño; este procedimiento no lo elimina.

## 2. Secretos exclusivamente en variables de entorno

Usar la misma contraseña y JWT en redeploys; conservarlos en un gestor de secretos.
Las siguientes lecturas no guardan los valores en el historial. No usar `set -x`,
no compilar los `.bicepparam` a archivos JSON con secretos y no añadir `.env` al repo.

```bash
read -rsp 'POSTGRES_PASSWORD (mínimo 16 caracteres): ' POSTGRES_PASSWORD; printf '\n'
export POSTGRES_PASSWORD
read -rsp 'JWT_SECRET aleatorio (mínimo 32 caracteres): ' JWT_SECRET; printf '\n'
export JWT_SECRET
```

Recuperar la clave de **tu recurso existente**, sin imprimirla:

```bash
export AZURE_MAPS_RESOURCE_GROUP="$(az resource list --name saferoute-maps --resource-type Microsoft.Maps/accounts --query '[0].resourceGroup' -o tsv)"
test -n "$AZURE_MAPS_RESOURCE_GROUP"
export AZURE_MAPS_API_KEY="$(az maps account keys list --resource-group "$AZURE_MAPS_RESOURCE_GROUP" --name saferoute-maps --query primaryKey -o tsv)"
```

Si el comando Maps no está disponible en tu CLI, obtener la clave desde el portal
y cargarla con `read -rsp`, sin pegarla en el chat. El despliegue exige
`${POSTGRES_PASSWORD:?}` sin valor por defecto y codifica los caracteres especiales
al construir `DATABASE_URL`. No usa Azurite. Por defecto construye la cadena Blob
desde la cuenta creada; para reutilizar otra cuenta, exportar
`AZURE_BLOB_CONNECTION_STRING` HTTPS y, opcionalmente, `AZURE_BLOB_CONTAINER`.
`EXPO_ACCESS_TOKEN` es opcional si tu configuración de push lo requiere.

## 3. Grafos obligatorios dentro de la imagen

Se **hornean los dos GraphML** en `/srv/app/backend/data/osm/`. Para una sola ciudad
evita volúmenes compartidos y descargas de OSM durante el arranque. Ya existen
localmente; no regenerarlos para este despliegue. `.gitignore` los excluye de Git,
pero `.dockerignore` permite incluirlos en el contexto Docker. Se excluye la caché.

```bash
test -s backend/data/osm/salamanca_driving.graphml
test -s backend/data/osm/salamanca_walking.graphml
sha256sum backend/data/osm/*.graphml
```

En una máquina nueva, copiar los grafos aprobados antes del build. Si no existen,
prepararlos en un entorno de desarrollo con `python -m backend.cli prepare-osm`.
El Dockerfile falla si alguno falta o está vacío. Las imágenes guardan sus SHA-256
como labels y se bloquean en ACR contra sobreescritura/borrado. No reconstruir un
tag ya publicado: el rollback recupera la imagen original y sus mismos grafos.
Un cambio de grafos requiere una nueva versión/commit que documente sus hashes.

## 4. Validar y desplegar

Pruebas locales (PowerShell, desde `app/`):

```powershell
.venv/Scripts/python.exe -m pytest backend/tests
Set-Location frontend
npm run typecheck
npm test
Set-Location ..
```

Para ejecutar las pruebas de integración, exportar `TEST_DATABASE_URL` apuntando
a una base PostgreSQL/PostGIS **desechable cuyo nombre termine en `_test`**, y correr
la misma suite. Las pruebas recrean su esquema; nunca usar una base de usuarios.
Sin esa variable, las siete pruebas PostGIS/inicialización se omiten.

Compilar los manifiestos y desplegar (Bash, después del commit autorizado):

```bash
az bicep build --file infrastructure/azure/infra.bicep --stdout > /dev/null
az bicep build --file infrastructure/azure/app.bicep --stdout > /dev/null
bash infrastructure/azure/deploy.sh
```

El script crea infraestructura en West US 2, construye y sube dos imágenes
`saferoute-backend:HASH_COMPLETO_DEL_COMMIT` y `saferoute-proxy:HASH_COMPLETO_DEL_COMMIT`,
crea un **respaldo bajo demanda de PostgreSQL antes de desplegar la app**, espera
la operación, despliega y consulta `/ready`. Si el backup falla, no inicia migraciones.
Si una ejecución anterior ya subió el tag, usar el redeploy de la sección 7, sin
reconstruirlo. Azure limita los backups bajo demanda; administrar su retención
sin borrar el respaldo requerido para el rollback.

Antes de servir, el init container ejecuta `python -m backend.initialize`:

1. Adquiere un advisory lock de sesión en PostgreSQL, compartido por revisiones.
2. Ejecuta `python -m alembic -c backend/alembic.ini upgrade head`.
3. Ejecuta `python -m backend.cli seed` solo si falta `initial_seed` en
   `deployment_state`; guarda el marcador después del éxito.
4. Libera el bloqueo. Solo entonces Azure inicia backend y proxy.

Una migración o seed fallido aborta la inicialización. Si se interrumpe después
del commit del seed y antes del marcador, el reintento usa el seed idempotente
existente. No borrar el marcador en reinicios. El bloqueo serializa migraciones;
no hace compatibles migraciones destructivas con una revisión antigua sirviendo.
Para futuras migraciones usar cambios compatibles o una ventana de mantenimiento.

Verificación del servicio:

```bash
export EXPO_PUBLIC_API_URL="$(az deployment group show -g "$AZURE_RESOURCE_GROUP" -n saferoute-app --query properties.outputs.apiUrl.value -o tsv)"
curl --fail "$EXPO_PUBLIC_API_URL/health"
curl --fail "$EXPO_PUBLIC_API_URL/ready"
curl -sS -D - -o /dev/null "$EXPO_PUBLIC_API_URL/health"
curl -sS -o /dev/null -w '%{http_code}\n' "$EXPO_PUBLIC_API_URL/docs"
az containerapp logs show -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_PREFIX-api" --container backend --tail 50
```

Esperar 200 en health/ready, los tres headers y 404 en docs. Comprobar registro,
login, mapa de Salamanca, cálculo de ruta, foto y actualizaciones WebSocket desde
una red externa. HTTPS usa el dominio `*.azurecontainerapps.io`; no hace falta
comprar un dominio. No usar `--debug` al manejar parámetros secretos.

## 5. Vincular EAS y configurar ambos entornos

En `frontend/`, iniciar sesión con `npx --yes eas-cli login`. Si no hay proyecto,
crear **saferoute-ai** en la cuenta Expo y copiar su Project ID desde sus ajustes.
No reutilizar el UUID de Azure Maps. `app.config.ts` lee ese ID desde el entorno;
no necesita escribirlo en el código.

Desde `app/`, con la URL real obtenida arriba:

```bash
export EXPO_PUBLIC_EAS_PROJECT_ID='UUID_REAL_DEL_PROYECTO_EXPO'
bash infrastructure/azure/configure-eas.sh
```

El script valida la configuración Expo, muestra el proyecto seleccionado y usa
`eas env:set` para guardar **EXPO_PUBLIC_API_URL** y **EXPO_PUBLIC_EAS_PROJECT_ID**
en los entornos **preview** y **production** del proyecto. Son valores públicos,
incluidos en el bundle; nunca poner aquí JWT_SECRET, claves de Maps ni de Blob.
El perfil preview selecciona explícitamente `environment: preview`, producción
selecciona `production`; ambos fijan `APP_ENV=production`.

La configuración aborta antes del build si falta una URL base HTTPS válida o un
UUID de EAS. Una URL incorrecta pero sintácticamente válida aún debe probarse
con `/ready`. No existe una URL real hasta desplegar Azure.

## 6. Generar e instalar el APK

Mantener exportadas ambas variables durante la resolución local del proyecto:

```bash
cd frontend
npx --yes eas-cli build --platform android --profile preview
```

La primera vez, seguir la configuración de firma de Android de EAS y conservar
el keystore en EAS. `preview` produce **APK** instalable directamente; descargarlo
desde el enlace del build y abrirlo en Android permitiendo instalar desde esa
fuente. Probar apertura, login, rutas y fotos usando datos móviles y con la
computadora apagada. La compilación y firma requieren una cuenta Expo autenticada.

```bash
# Distribución por Google Play (AAB; no se instala como un APK):
npx --yes eas-cli build --platform android --profile production
```

Cambiar la URL en EAS no modifica un APK ya instalado: generar e instalar otro.
`/ready` se consulta cada 60 segundos solo mientras la app está activa y tiene
red; conserva comprobación al volver a primer plano y reintento manual.

## 7. Redeploy y rollback

Guardar por versión: hash de imagen, digests de ACR, hashes de grafos, nombre del
backup previo y hora UTC. No usar `latest`. Las dos imágenes deben existir con
el mismo tag. Para reintentar un despliegue cuyas imágenes ya se subieron:

```bash
# Desde app/, con los mismos secretos y AZURE_* exportados.
export IMAGE_TAG='HASH_COMPLETO_YA_PUBLICADO'
export INITIALIZE_DATABASE=true
postgres="$(az deployment group show -g "$AZURE_RESOURCE_GROUP" -n saferoute-infra --query properties.outputs.postgresName.value -o tsv)"
postgres="${POSTGRES_SERVER_NAME:-$postgres}"
backup="pre-${IMAGE_TAG:0:12}-$(date -u +%Y%m%d%H%M%S)"
az postgres flexible-server backup create -g "$AZURE_RESOURCE_GROUP" --server-name "$postgres" --name "$backup" -o none
az postgres flexible-server backup show -g "$AZURE_RESOURCE_GROUP" --server-name "$postgres" --name "$backup" -o table
az deployment group create -g "$AZURE_RESOURCE_GROUP" -n saferoute-app --parameters infrastructure/azure/app.bicepparam -o none
```

Para rollback **si el esquema actual es compatible con la imagen anterior**:

```bash
export IMAGE_TAG='HASH_COMPLETO_DE_LA_VERSION_ANTERIOR'
export INITIALIZE_DATABASE=false
az deployment group create -g "$AZURE_RESOURCE_GROUP" -n saferoute-app --parameters infrastructure/azure/app.bicepparam -o none
curl --fail "$EXPO_PUBLIC_API_URL/ready"
unset INITIALIZE_DATABASE
```

Esto redepliega las dos imágenes anteriores sin reconstruirlas ni ejecutar el
Alembic antiguo contra una revisión que no conoce. No es un downgrade de la base.
No usar `INITIALIZE_DATABASE=false` para instalar una versión nueva.

Si el cambio de esquema es incompatible, detener escrituras antes de restaurar
(por ejemplo, deshabilitar temporalmente el ingress; habrá indisponibilidad).
Restaurar a **otro servidor** al instante UTC anterior a las migraciones; se
perderán en ese servidor los cambios posteriores a ese instante, por lo que
debe acordarse la recuperación antes de ejecutarla:

```bash
az containerapp ingress disable -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_PREFIX-api"
export POSTGRES_SERVER_NAME='NOMBRE_UNICO_DEL_SERVIDOR_RESTAURADO'
export RESTORE_TIME='INSTANTE_UTC_ANTERIOR_A_LAS_MIGRACIONES'
az postgres flexible-server restore -g "$AZURE_RESOURCE_GROUP" \
  --name "$POSTGRES_SERVER_NAME" --source-server "$postgres" --restore-time "$RESTORE_TIME"
```

Confirmar que el nuevo servidor conserva conectividad privada/DNS, PostGIS,
credenciales y datos. Conservar `POSTGRES_SERVER_NAME` exportado para apuntar a
él, cargar `IMAGE_TAG` anterior y ejecutar el rollback con
`INITIALIZE_DATABASE=false`; el manifiesto restablece el ingress HTTPS. Conservar
el servidor original mientras se verifica la recuperación. Los jobs internos
pueden seguir trabajando aunque se cierre el ingress: para una congelación total,
desactivar también la revisión activa antes de restaurar y volver a activarla
solo según el procedimiento de recuperación. No ejecutar `alembic downgrade`
automáticamente: la migración inicial elimina tablas al bajar.

## Fuentes operativas

- [Ingress, TLS y confianza de X-Forwarded-For en ACA](https://learn.microsoft.com/en-us/azure/container-apps/ingress-overview).
- [Init containers y recursos](https://learn.microsoft.com/en-us/azure/container-apps/containers).
- [CLI de respaldos PostgreSQL](https://learn.microsoft.com/en-us/cli/azure/postgres/flexible-server/backup).
- [Restauración PostgreSQL](https://learn.microsoft.com/en-us/cli/azure/postgres/flexible-server#az-postgres-flexible-server-restore).
- [Variables de EAS](https://docs.expo.dev/eas/environment-variables/usage/) y [CLI env:set](https://docs.expo.dev/eas/cli/).
