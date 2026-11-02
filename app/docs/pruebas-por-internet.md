# Probar SafeRouteAI con Wi-Fi o datos móviles

El modo LAN de Expo necesita que el celular pueda alcanzar la computadora por su IP local. Con datos móviles o redes diferentes se necesitan **dos túneles**: Metro (Expo) y FastAPI. El túnel de Expo no publica automáticamente el puerto 8000.

## Inicio

Abre Docker Desktop y espera a que el motor esté listo. En PowerShell:

```powershell
cd "C:\Users\Alberto\OneDrive\Documents\SafeRouteAI\app"
powershell -ExecutionPolicy Bypass -File .\infrastructure\start-backend.ps1
```

Espera `Uvicorn running on http://0.0.0.0:8000`. Deja abierta esa terminal.

En otra terminal:

```powershell
cd "C:\Users\Alberto\OneDrive\Documents\SafeRouteAI\app"
powershell -ExecutionPolicy Bypass -File .\infrastructure\start-mobile.ps1
```

Este comando verifica PostgreSQL y FastAPI, descarga cloudflared en Docker la primera vez, crea un túnel HTTPS temporal para la API y configura `EXPO_PUBLIC_API_URL` solo en el proceso de Expo. Inicia Metro con `--go --tunnel`, sin selector de Development Build. No modifica los archivos `.env` ni copia claves Azure al cliente.

En una copia nueva del repositorio ejecuta primero `npm.cmd ci` desde `app/frontend` para instalar las dependencias, incluyendo `@expo/ngrok`.

Escanea el **nuevo** QR con la cámara del iPhone o desde Expo Go en Android. El teléfono puede usar datos móviles mientras la computadora utiliza Wi-Fi, Ethernet o un hotspot. Ambos necesitan internet; la computadora debe seguir encendida y sin suspenderse. Algunas redes corporativas o servicios de túnel pueden bloquear o interrumpir la conexión: no existe garantía de funcionamiento en todas las redes.

La URL temporal cambia al reiniciar el comando. Cierra la sesión anterior de Expo Go y vuelve a escanear. La API permanece autenticada; las rutas públicas de registro, salud y documentación también son accesibles por la URL del túnel. No hace falta abrir el puerto del router ni ejecutar `allow-phone.ps1` para este modo. El túnel es para pruebas, no un despliegue permanente.

## Servidor remoto estable

Si ya tienes un backend HTTPS desplegado:

```powershell
powershell -ExecutionPolicy Bypass -File .\infrastructure\start-mobile.ps1 -ApiUrl https://tu-backend.example.com
```

Este modo usa el backend indicado sin crear el túnel de Cloudflare. Una aplicación instalada con backend alojado permite probar sin mantener Metro ni tu computadora encendidos; ese despliegue aún requiere configurar el alojamiento y generar el build.

## Diagnóstico

Desde `app`, con el backend iniciado:

```powershell
.\.venv\Scripts\python.exe -m backend.diagnose
```

Comprueba por separado API/PostgreSQL, cartografía Azure, búsqueda, rutas auto/caminata y presencia de redes OSM. Realiza algunas solicitudes reales de Azure y no muestra claves. La clave se configura exclusivamente en `backend/.env`; al cambiarla reinicia el backend.

La app comprueba disponibilidad de la API cada 15 segundos mientras está visible. Si solo la base de datos falla, lo identifica. Si un mapa falla temporalmente, pulsa **Reintentar mapa**; renueva la sesión cuando corresponde y carga el visor de nuevo. Los errores de permisos o límite de Azure se distinguen en el backend sin registrar credenciales.

## Prueba en el celular

1. Entra a la app con el QR nuevo y comprueba que carga el mapa de Salamanca.
2. Desactiva el Wi-Fi del celular, deja datos móviles activos y consulta una ruta.
3. Comprueba cartografía, búsqueda y actividad; crea reportes solo para incidentes reales.
4. Al perder internet, comprueba el aviso y la cola de reportes. Restablece conexión y espera la sincronización.
5. La cobertura geográfica sigue siendo Salamanca: conexión remota no amplía la región soportada.

## Apagar

Pulsa `Ctrl+C` en la terminal del modo internet para detener Metro y su túnel API. Pulsa `Ctrl+C` en la terminal del backend. Desde `app`, ejecuta `docker compose -f infrastructure/compose.yaml stop`. Si cerraste la ventana abruptamente, busca el contenedor `saferoute-mobile-...` en Docker Desktop y detenlo.

## Referencias

Verificación realizada: 28 pruebas de backend aprobadas (una prueba PostGIS aislada omitida por no configurar su base de pruebas), 8 de frontend aprobadas y TypeScript sin errores. El diagnóstico real comprobó API/PostgreSQL, tiles Azure, búsqueda, rutas de automóvil/caminata y archivos OSM. Pendiente: activar el túnel con autorización y verificar físicamente Android/iOS con datos móviles. La disponibilidad por internet no se considera validada solo por pasar las pruebas locales.

- [Expo CLI: túneles](https://docs.expo.dev/more/expo-cli/#tunneling)
- [Cloudflare: túneles temporales](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
