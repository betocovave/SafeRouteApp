import fs from 'node:fs';
import path from 'node:path';
const root = process.cwd();
const js = fs.readFileSync(path.join(root, 'node_modules/leaflet/dist/leaflet.js'), 'utf8');
const css = fs.readFileSync(path.join(root, 'node_modules/leaflet/dist/leaflet.css'), 'utf8');
fs.mkdirSync(path.join(root, 'src/maps'), { recursive: true });
fs.writeFileSync(path.join(root, 'src/maps/leafletAssets.ts'), `// Generated from Leaflet 1.9.4; BSD-2-Clause. No CDN needed.\nexport const leafletJS = ${JSON.stringify(js)};\nexport const leafletCSS = ${JSON.stringify(css)};\n`);
fs.mkdirSync(path.join(root, 'licenses'), { recursive: true });
fs.copyFileSync(path.join(root, 'node_modules/leaflet/LICENSE'), path.join(root, 'licenses/Leaflet.txt'));
