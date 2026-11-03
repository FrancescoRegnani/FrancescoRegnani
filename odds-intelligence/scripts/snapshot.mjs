// Build web/data.json with the exact engine the dashboard runs in the browser.
// The engine sits between /*ENGINE-START*/ and /*ENGINE-END*/ in web/index.html.
// Usage: node scripts/snapshot.mjs [out]   (behind a proxy: NODE_USE_ENV_PROXY=1)
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const html = readFileSync(join(root, 'web/index.html'), 'utf8');
const engine = html.split('/*ENGINE-START*/')[1]?.split('/*ENGINE-END*/')[0];
if (!engine) throw new Error('engine markers not found in web/index.html');
const collectLive = new Function(engine + '\nreturn collectLive;')();
const out = process.argv[2] || join(root, 'web/data.json');
const data = await collectLive();
data.live = false; // a file on disk is a snapshot, never live
for (const e of data.events) for (const k of ['short', 'order']) delete e[k];
writeFileSync(out, JSON.stringify(data));
const by = {};
for (const e of data.events) by[e.sport] = (by[e.sport] || 0) + 1;
console.log('events', data.events.length, by, 'espn ok', data.espnOk, 'errors', data.errors,
  'markets', data.events.reduce((n, e) => n + (e.markets || []).length, 0));
