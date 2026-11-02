using './infra.bicep'

param location = readEnvironmentVariable('AZURE_LOCATION', 'westus2')
param prefix = readEnvironmentVariable('AZURE_PREFIX')
param postgresPassword = readEnvironmentVariable('POSTGRES_PASSWORD')
