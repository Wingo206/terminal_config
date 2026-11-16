import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

await build({
  bundle: true,
  platform: 'node',
  target: 'node18',
  format: 'cjs',
  sourcemap: true,
  logLevel: 'info',
  entryPoints: [resolve(root, 'src/extension.ts')],
  outfile: resolve(root, 'out/extension.js'),
  external: ['vscode'],
});
