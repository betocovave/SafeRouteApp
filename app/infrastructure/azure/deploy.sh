#!/usr/bin/env bash
set -euo pipefail
set +x
cd "$(dirname "$0")/../.."
: "${AZURE_SUBSCRIPTION_ID:?Exporta el ID de Azure for Students}"
: "${AZURE_RESOURCE_GROUP:?Exporta el grupo de recursos de producción}"
: "${AZURE_PREFIX:?Exporta un prefijo de 3 a 16 caracteres en minúsculas}"
: "${POSTGRES_PASSWORD:?Exporta una contraseña propia de al menos 16 caracteres}"
: "${JWT_SECRET:?Exporta un secreto persistente de al menos 32 caracteres}"
: "${AZURE_MAPS_API_KEY:?Exporta la clave de saferoute-maps}"
export AZURE_LOCATION="${AZURE_LOCATION:-westus2}"
export INITIALIZE_DATABASE=true
[[ "$AZURE_PREFIX" =~ ^[a-z][a-z0-9-]{1,14}[a-z0-9]$ ]] || { echo 'AZURE_PREFIX inválido.' >&2; exit 1; }
[[ ${#POSTGRES_PASSWORD} -ge 16 && ${#JWT_SECRET} -ge 32 ]] || { echo 'Contraseña o JWT_SECRET demasiado corto.' >&2; exit 1; }
if [[ -n "$(git --no-optional-locks status --porcelain --untracked-files=all -- .)" ]]; then
  echo 'Hay cambios sin commit en app/. Revisa y autoriza un commit antes de publicar una imagen etiquetada con su hash.' >&2
  exit 1
fi
export IMAGE_TAG
IMAGE_TAG="$(git rev-parse HEAD)"
for mode in driving walking; do
  test -s "backend/data/osm/salamanca_${mode}.graphml" || { echo "Falta el grafo $mode." >&2; exit 1; }
done

az account set --subscription "$AZURE_SUBSCRIPTION_ID"
az group create --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_LOCATION" --output none
az deployment group create --resource-group "$AZURE_RESOURCE_GROUP" --name saferoute-infra \
  --parameters infrastructure/azure/infra.bicepparam --output none
registry="$(az deployment group show -g "$AZURE_RESOURCE_GROUP" -n saferoute-infra --query properties.outputs.registryName.value -o tsv)"
registry_server="$(az deployment group show -g "$AZURE_RESOURCE_GROUP" -n saferoute-infra --query properties.outputs.registryServer.value -o tsv)"
postgres="$(az deployment group show -g "$AZURE_RESOURCE_GROUP" -n saferoute-infra --query properties.outputs.postgresName.value -o tsv)"
postgres="${POSTGRES_SERVER_NAME:-$postgres}"

# Never overwrite an image associated with a commit (including its ignored OSM data).
repositories="$(az acr repository list --name "$registry" -o tsv)"
for repository in saferoute-backend saferoute-proxy; do
  if grep -Fxq "$repository" <<< "$repositories"; then
    exists="$(az acr repository show-tags --name "$registry" --repository "$repository" --query "contains(@, '$IMAGE_TAG')" -o tsv)"
    if [[ "$exists" == true ]]; then
      echo "Ya existe $repository:$IMAGE_TAG. Usa el procedimiento de redeploy/rollback de docs/deploy.md." >&2
      exit 1
    fi
  fi
done
az acr login --name "$registry"
docker build --platform linux/amd64 -f infrastructure/Dockerfile \
  --label "org.opencontainers.image.revision=$IMAGE_TAG" \
  --label "saferoute.osm.driving=$(sha256sum backend/data/osm/salamanca_driving.graphml | cut -d ' ' -f 1)" \
  --label "saferoute.osm.walking=$(sha256sum backend/data/osm/salamanca_walking.graphml | cut -d ' ' -f 1)" \
  -t "$registry_server/saferoute-backend:$IMAGE_TAG" .
docker build --platform linux/amd64 -f infrastructure/azure/Proxy.Dockerfile \
  --label "org.opencontainers.image.revision=$IMAGE_TAG" -t "$registry_server/saferoute-proxy:$IMAGE_TAG" .
for repository in saferoute-backend saferoute-proxy; do
  docker push "$registry_server/$repository:$IMAGE_TAG"
  az acr repository update --name "$registry" --image "$repository:$IMAGE_TAG" \
    --write-enabled false --delete-enabled false --output none
done

# Azure's synchronous command waits for the backup operation; any error aborts
# before deploying the init container. No public PostgreSQL firewall is needed.
backup="pre-${IMAGE_TAG:0:12}-$(date -u +%Y%m%d%H%M%S)"
az postgres flexible-server backup create --resource-group "$AZURE_RESOURCE_GROUP" \
  --server-name "$postgres" --name "$backup" --output none
az postgres flexible-server backup show --resource-group "$AZURE_RESOURCE_GROUP" \
  --server-name "$postgres" --name "$backup" --output table
az deployment group create --resource-group "$AZURE_RESOURCE_GROUP" --name saferoute-app \
  --parameters infrastructure/azure/app.bicepparam --output none
api_url="$(az deployment group show -g "$AZURE_RESOURCE_GROUP" -n saferoute-app --query properties.outputs.apiUrl.value -o tsv)"
curl --fail --show-error --retry 12 --retry-delay 5 --retry-all-errors "$api_url/ready"
printf '\nAPI: %s\nImagen: %s\nRespaldo: %s\n' "$api_url" "$IMAGE_TAG" "$backup"
