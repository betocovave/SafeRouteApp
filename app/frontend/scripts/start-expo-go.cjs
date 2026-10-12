const path = require('node:path');

// Expo SDK 57 shows a runtime selector when expo-dev-client is installed,
// even with --go. Disable it before loading the CLI so the QR uses exp://.
process.env.EXPO_NO_REDIRECT_PAGE = '1';
const cli = path.join(path.dirname(require.resolve('expo/package.json')), 'bin', 'cli');
process.argv = [process.execPath, cli, 'start', '--go', ...process.argv.slice(2)];
require(cli);
