import test from 'node:test';
import assert from 'node:assert/strict';

import { createNotionPage, queryNotionDatabase } from '../scripts/lib/notion-client.js';

test('queries a Notion database with shared API headers', async (t) => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return new Response(JSON.stringify({ results: [] }), { status: 200 });
  };
  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  const result = await queryNotionDatabase('secret-token', 'database-id', { filter: {} });

  assert.deepEqual(result, { results: [] });
  assert.equal(calls[0].url, 'https://api.notion.com/v1/databases/database-id/query');
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer secret-token');
  assert.equal(calls[0].options.headers['Notion-Version'], '2022-06-28');
  assert.equal(calls[0].options.body, JSON.stringify({ filter: {} }));
});

test('creates a Notion page with shared API headers', async (t) => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return new Response(JSON.stringify({ id: 'page-id' }), { status: 200 });
  };
  t.after(() => {
    globalThis.fetch = originalFetch;
  });

  const result = await createNotionPage('secret-token', { parent: { database_id: 'database-id' } });

  assert.deepEqual(result, { id: 'page-id' });
  assert.equal(calls[0].url, 'https://api.notion.com/v1/pages');
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer secret-token');
  assert.equal(calls[0].options.body, JSON.stringify({ parent: { database_id: 'database-id' } }));
});
