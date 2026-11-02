#!/usr/bin/env bash
set -euo pipefail
set +x
cd "$(dirname "$0")/../../frontend"
: "${EXPO_PUBLIC_API_URL:?Exporta la URL HTTPS publicada en Azure}"
: "${EXPO_PUBLIC_EAS_PROJECT_ID:?Exporta el UUID del proyecto EAS}"
export APP_ENV=production

# Validate the same config EAS resolves, before changing remote environment values.
npx expo config --type public > /dev/null
npx --yes eas-cli project:info
for environment in preview production; do
  npx --yes eas-cli env:set "$environment" --scope project --name EXPO_PUBLIC_API_URL \
    --value "$EXPO_PUBLIC_API_URL" --visibility plaintext --non-interactive
  npx --yes eas-cli env:set "$environment" --scope project --name EXPO_PUBLIC_EAS_PROJECT_ID \
    --value "$EXPO_PUBLIC_EAS_PROJECT_ID" --visibility plaintext --non-interactive
done
