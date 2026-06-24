import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

test('exposes only the supported local commands', () => {
  const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));

  assert.deepEqual(packageJson.scripts, {
    test: 'node --test',
    'setup:docker': 'node scripts/setup-docker.js',
  });
});
