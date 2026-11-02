using './app.bicep'

param location = readEnvironmentVariable('AZURE_LOCATION', 'westus2')
param prefix = readEnvironmentVariable('AZURE_PREFIX')
param imageTag = readEnvironmentVariable('IMAGE_TAG')
param initializeDatabase = bool(readEnvironmentVariable('INITIALIZE_DATABASE', 'true'))
param postgresServerName = readEnvironmentVariable('POSTGRES_SERVER_NAME', '')
param postgresPassword = readEnvironmentVariable('POSTGRES_PASSWORD')
param jwtSecret = readEnvironmentVariable('JWT_SECRET')
param mapsApiKey = readEnvironmentVariable('AZURE_MAPS_API_KEY')
param expoAccessToken = readEnvironmentVariable('EXPO_ACCESS_TOKEN', '')
param blobConnectionString = readEnvironmentVariable('AZURE_BLOB_CONNECTION_STRING', '')
param blobContainer = readEnvironmentVariable('AZURE_BLOB_CONTAINER', 'incident-photos')
param corsOrigins = readEnvironmentVariable('CORS_ORIGINS', '')
