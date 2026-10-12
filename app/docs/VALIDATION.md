# Validación de entrega

## Ejecutado

- Backend: 21 pruebas aprobadas, 1 integración PostGIS omitida por falta de servicio. Suite API, autorización, recuperación, revocación, reportes idempotentes,
  corroboración independiente, expiración, EXIF, contratos Azure, corredor dirigido,
  paquetes offline y reglas de iluminación/ausencia de datos.
- Frontend: TypeScript sin errores y 5 pruebas aprobadas de cola/foto, progreso de navegación,
  scripts offline claro/oscuro y proxy sin credenciales Azure.
- Expo SDK 57: exportación de bundles Hermes para Android e iOS; no son APK/IPA.
- Redes OSM reales de Salamanca preparadas para automóvil y caminata.
- Paquete real generado en -101.195, 20.57: 7,764 features; 1,352,772 bytes (aprox. 1.29 MiB).
- SQL PostgreSQL de las tablas geoespaciales compilado con geometry POINT/LINESTRING SRID 4326.
- Contrato OpenAPI exportado y tipos TypeScript generados y consumidos en el frontend.
- PDF de 13 páginas generado y renderizado; revisión visual de páginas y comprobación de 36 IDs,
  9 enlaces oficiales y cero palabras fuera de los márgenes de página.

## Pendiente de entorno

- Ejecutar migraciones y prueba geográfica contra PostgreSQL/PostGIS; Docker no está instalado aquí.
- Azurite y Azure Blob: comprobar carga/lectura autenticada y fallos de red en un entorno operativo.
- Azure Maps: la API KEY permanece vacía hasta que el propietario la introduzca.
- Dispositivos Android/iOS: GPS, permisos, WebView, orientación, tamaños de pantalla, temas y cámara.
- Notificaciones reales: projectId Expo y credenciales APNs/FCM correspondientes.
- Medir latencia con servicio completo: objetivos de 5 s, todavía no verificados.
- Publicación: cuentas, firma, infraestructura HTTPS y revisión de dependencias compatibles.

## Seguridad de dependencias

La auditoría npm informó 22 avisos (15 altos, 7 moderados), con cadenas transitivas
de Expo/Metro/xcode, incluyendo braces, node-forge y uuid. Las versiones más recientes consultadas
de braces y node-forge continúan dentro del rango señalado. La corrección automática propone
retroceder Expo a 44/React Native a 0.72, incompatible con este proyecto; no se aplicó.
Se conservan `frontend/audit-report.json` y `frontend/audit-fix-preview.json` como evidencia.
Antes de publicar, revisar las actualizaciones soportadas del SDK y sus dependencias.

## Aceptación en dispositivos

1. Registrar dos o más cuentas reales y guardar sus códigos privados. Restablecer una cuenta y
   verificar que un dispositivo con sesión antigua pierda acceso.
2. Buscar destino, comparar auto/pie y consultar factores. Crear un incidente cercano a una ruta,
   verificar aviso y elegir una alternativa; repetir con evento crítico sin alternativa adecuada.
3. Reportar con y sin fotografía. Denegar cámara y ubicación; comprobar mensajes y recuperación.
4. Corroborar cerca y lejos, repetir voto, usar autor del reporte y evento crítico. Verificar permisos.
5. Descargar sector, iniciar recorrido, cortar Internet y comprobar mapa/GPS/instrucciones. Crear
   reporte offline, volver a conectar y verificar exactamente un reporte y una fotografía.
6. Poner la app en segundo plano y verificar que el seguimiento de GPS se detenga.
7. Revisar claro/oscuro, orientación y tamaños pequeños/tablet; comprobar que todos los controles
   abran su flujo, mantengan estado y permitan volver.
8. Suspender una cuenta desde administración y comprobar revocación. Ocultar reporte y confirmar
   que deja de influir en rutas, alertas y mapa de calor.
9. Repetir con Azure sin clave, claves inválidas, servidor caído, timeout y Blob no disponible.
10. Registrar tiempos P50/P95 de rutas y actualizaciones, volumen de datos, dispositivo y red utilizados.
