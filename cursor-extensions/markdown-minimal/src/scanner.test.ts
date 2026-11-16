import assert from 'node:assert/strict';
import test from 'node:test';
import { scanMarkdown } from './scanner.ts';

test('scans headings, bold, inline code, and dimmed bracket links without colliding', () => {
  const doc = [
    '---',
    'pr: 3031',
    '---',
    '## Thread 1: Move `Create workspace` action',
    '',
    '**Target:**',
    '- [HomeSettingsWorkspaces.tsx:80-89](/components/home-page/HomeSettingsWorkspaces.tsx#L80-L89)',
    '',
    '**Posted comment ([link](https://github.com/mach9robotics/bagel/pull/3031#discussion_r4532320685)):**',
    '',
    '<!-- enrichment:start -->',
    'Plain prose with `snake_case_identifier` intact.',
  ].join('\n');

  const result = scanMarkdown(doc);

  assert.equal(result.links.length, 2);
  assert.equal(result.links[0].url, '/components/home-page/HomeSettingsWorkspaces.tsx#L80-L89');
  assert.equal(
    doc.slice(result.links[0].labelFrom, result.links[0].labelTo),
    'HomeSettingsWorkspaces.tsx:80-89',
  );
  assert.equal(
    result.links[1].url,
    'https://github.com/mach9robotics/bagel/pull/3031#discussion_r4532320685',
  );
  assert.equal(doc.slice(result.links[1].labelFrom, result.links[1].labelTo), 'link');

  // Ensure snake_case_identifier was not treated as italic
  const italicSlices = result.tokens
    .filter((t) => t.kind === 'italic')
    .map((t) => doc.slice(t.from, t.to));
  assert.deepEqual(italicSlices, []);

  // Ensure bold header containing nested link stayed a single bold span
  const boldSlices = result.tokens
    .filter((t) => t.kind === 'bold')
    .map((t) => doc.slice(t.from, t.to));
  assert.ok(
    boldSlices.includes(
      'Posted comment ([link](https://github.com/mach9robotics/bagel/pull/3031#discussion_r4532320685)):',
    ),
  );

  // Ensure Obsidian [[wikilinks]] are left untouched
  const wikilinkScan = scanMarkdown('Transcript: [[chats/2026-11-10-foo|2026-11-10: Foo]]');
  assert.equal(wikilinkScan.links.length, 0);
});

test('skips markdown constructs inside fenced code blocks', () => {
  const doc = [
    '```ts',
    'const x = "[not-a-link](/foo.ts#L1)";',
    '```',
  ].join('\n');

  const result = scanMarkdown(doc);
  assert.equal(result.links.length, 0);
  assert.equal(result.tokens.filter((t) => t.kind === 'codeBlockLine').length, 3);
});
