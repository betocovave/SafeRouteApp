param location string = resourceGroup().location
param prefix string
param imageTag string
param initializeDatabase bool = true
// Set only when switching to a server restored from backup.
param postgresServerName string = ''
@secure()
@minLength(16)
param postgresPassword string
@secure()
@minLength(32)
param jwtSecret string
@secure()
@minLength(1)
param mapsApiKey string
@secure()
param expoAccessToken string = ''
// Empty uses the private container in the storage account created by infra.bicep.
@secure()
param blobConnectionString string = ''
param blobContainer string = 'incident-photos'
param corsOrigins string = ''

var suffix = uniqueString(resourceGroup().id)
resource environment 'Microsoft.App/managedEnvironments@2025-01-01' existing = { name: '${prefix}-env' }
resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = { name: 'sr${suffix}' }
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = { name: '${prefix}-pull' }
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' existing = { name: empty(postgresServerName) ? '${prefix}-pg-${suffix}' : postgresServerName }
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = { name: 'sr${suffix}' }
var apiUrl = 'https://${prefix}-api.${environment.properties.defaultDomain}'
var backendImage = '${registry.properties.loginServer}/saferoute-backend:${imageTag}'
var backendEnv = [
  { name: 'ENVIRONMENT', value: 'production' }
  { name: 'DATABASE_URL', secretRef: 'database-url' }
  { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
  { name: 'AZURE_MAPS_API_KEY', secretRef: 'maps-key' }
  { name: 'AZURE_MAPS_AUTH_MODE', value: 'key' }
  { name: 'AZURE_BLOB_CONNECTION_STRING', secretRef: 'blob-connection' }
  { name: 'AZURE_BLOB_CONTAINER', value: blobContainer }
  { name: 'EXPO_ACCESS_TOKEN', secretRef: 'expo-token' }
  { name: 'PUBLIC_API_URL', value: apiUrl }
  { name: 'CORS_ORIGINS', value: corsOrigins }
  { name: 'FORWARDED_ALLOW_IPS', value: '127.0.0.1' }
  { name: 'ENABLE_JOBS', value: 'true' }
]

resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: '${prefix}-api'
  location: location
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${identity.id}': {} } }
  properties: {
    environmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: { external: true, targetPort: 8080, transport: 'auto', allowInsecure: false }
      registries: [{ server: registry.properties.loginServer, identity: identity.id }]
      secrets: [
        { name: 'database-url', value: 'postgresql+psycopg://saferouteadmin:${uriComponent(postgresPassword)}@${postgres.properties.fullyQualifiedDomainName}:5432/saferoute?sslmode=require' }
        { name: 'jwt-secret', value: jwtSecret }
        { name: 'maps-key', value: mapsApiKey }
        { name: 'expo-token', value: expoAccessToken }
        { name: 'blob-connection', value: empty(blobConnectionString) ? 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=${az.environment().suffixes.storage}' : blobConnectionString }
      ]
    }
    template: {
      // One worker and one replica: jobs, websocket hub and rate limits are in memory.
      scale: { minReplicas: 1, maxReplicas: 1 }
      initContainers: initializeDatabase ? [
        {
          name: 'migrate'
          image: backendImage
          command: ['python', '-m', 'backend.initialize']
          env: backendEnv
          resources: { cpu: json('0.75'), memory: '1.5Gi' }
        }
      ] : []
      containers: [
        {
          name: 'backend'
          image: backendImage
          // Only the local proxy can reach Uvicorn. Port 8000 is never exposed.
          command: ['uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000', '--workers', '1']
          env: backendEnv
          resources: { cpu: json('0.75'), memory: '1.5Gi' }
        }
        {
          name: 'proxy'
          image: '${registry.properties.loginServer}/saferoute-proxy:${imageTag}'
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
          probes: [
            { type: 'Startup', httpGet: { path: '/health', port: 8080 }, periodSeconds: 5, timeoutSeconds: 2, failureThreshold: 60 }
            { type: 'Liveness', httpGet: { path: '/health', port: 8080 }, periodSeconds: 30, timeoutSeconds: 5, failureThreshold: 3 }
            { type: 'Readiness', httpGet: { path: '/ready', port: 8080 }, periodSeconds: 30, timeoutSeconds: 10, failureThreshold: 3 }
          ]
        }
      ]
    }
  }
}

output apiUrl string = apiUrl
