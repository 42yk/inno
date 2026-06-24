import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

test('docker compose runs n8n with persistent volume and localhost port', () => {
  const compose = fs.readFileSync('docker-compose.yml', 'utf8');

  assert.match(compose, /docker\.n8n\.io\/n8nio\/n8n/);
  assert.match(compose, /5678:5678/);
  assert.match(compose, /n8n_data:\/home\/node\/\.n8n/);
  assert.match(compose, /env_file:/);
  assert.match(compose, /\.env/);
  assert.match(compose, /GENERIC_TIMEZONE/);
  assert.match(compose, /N8N_RUNNERS_ENABLED/);
  assert.match(compose, /N8N_BLOCK_ENV_ACCESS_IN_NODE:\s*"false"/);
  assert.match(compose, /NOTION_API_TOKEN:\s*\$\{NOTION_API_TOKEN/);
  assert.match(compose, /NOTION_RSS_CONFIG_DB_ID:\s*\$\{NOTION_RSS_CONFIG_DB_ID/);
});
