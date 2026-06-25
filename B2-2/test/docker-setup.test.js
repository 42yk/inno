import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

import {
  assignmentsFromCreatedDatabaseResult,
  buildDockerImportCommands,
  buildProductionWebhookUrl,
  missingNotionDatabaseEnvNames,
  mergeEnvAssignments,
} from '../scripts/lib/docker-setup.js';

test('detects missing Notion database ids that setup can create', () => {
  assert.deepEqual(
    missingNotionDatabaseEnvNames({
      NOTION_NEWS_DB_ID: '',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
    }),
    ['NOTION_NEWS_DB_ID', 'NOTION_TOPIC_CONFIG_DB_ID'],
  );
});

test('merges generated Notion database ids into env file content', () => {
  const content = [
    'NOTION_API_TOKEN="secret_xxx"',
    'NOTION_PARENT_PAGE_ID="parent-id"',
    'NOTION_NEWS_DB_ID=',
    'N8N_WORKFLOW_NAME="B2-2 RSS AI News Summary"',
  ].join('\n');

  const result = mergeEnvAssignments(content, {
    NOTION_NEWS_DB_ID: 'news-db',
    NOTION_RSS_CONFIG_DB_ID: 'rss-db',
    NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
  });

  assert.match(result, /^NOTION_NEWS_DB_ID=news-db$/m);
  assert.match(result, /^NOTION_RSS_CONFIG_DB_ID=rss-db$/m);
  assert.match(result, /^NOTION_TOPIC_CONFIG_DB_ID=topic-db$/m);
  assert.match(result, /^NOTION_API_TOKEN="secret_xxx"$/m);
});

test('builds Docker CLI workflow import commands without n8n API key', () => {
  assert.deepEqual(buildDockerImportCommands('dist/workflow.json'), [
    ['docker', 'compose', 'up', '-d'],
    ['docker', 'compose', 'exec', '-T', 'ollama', 'ollama', 'pull', 'gemma3:1b'],
    ['docker', 'compose', 'cp', 'dist/workflow.json', 'n8n:/tmp/b2-2-workflow.json'],
    [
      'docker',
      'compose',
      'exec',
      '-T',
      'n8n',
      'n8n',
      'import:workflow',
      '--input=/tmp/b2-2-workflow.json',
    ],
  ]);
});

test('builds the production webhook URL from the configured path', () => {
  assert.equal(
    buildProductionWebhookUrl('b2-2/rss-ai-news-summary/run'),
    'http://localhost:5678/webhook/b2-2/rss-ai-news-summary/run',
  );
  assert.equal(
    buildProductionWebhookUrl('/custom/run/'),
    'http://localhost:5678/webhook/custom/run',
  );
});

test('builds Docker CLI workflow import commands with activation and restart when workflow is active', (t) => {
  const tempPath = 'dist/test-temp-workflow.json';
  fs.mkdirSync('dist', { recursive: true });
  fs.writeFileSync(
    tempPath,
    JSON.stringify({ id: 'test-id', active: true })
  );

  t.after(() => {
    try { fs.unlinkSync(tempPath); } catch {}
  });

  assert.deepEqual(buildDockerImportCommands(tempPath), [
    ['docker', 'compose', 'up', '-d'],
    ['docker', 'compose', 'exec', '-T', 'ollama', 'ollama', 'pull', 'gemma3:1b'],
    ['docker', 'compose', 'cp', tempPath, 'n8n:/tmp/b2-2-workflow.json'],
    [
      'docker',
      'compose',
      'exec',
      '-T',
      'n8n',
      'n8n',
      'import:workflow',
      '--input=/tmp/b2-2-workflow.json',
    ],
    [
      'docker',
      'compose',
      'exec',
      '-T',
      'n8n',
      'n8n',
      'publish:workflow',
      '--id=test-id',
    ],
    ['docker', 'compose', 'restart', 'n8n'],
  ]);
});

test('builds publish commands for multiple active workflows in one import file', (t) => {
  const tempPath = 'dist/test-temp-workflows.json';
  fs.mkdirSync('dist', { recursive: true });
  fs.writeFileSync(
    tempPath,
    JSON.stringify([
      { id: 'main-id', active: true },
      { id: 'error-id', active: true },
      { id: 'inactive-id', active: false },
    ]),
  );

  t.after(() => {
    try { fs.unlinkSync(tempPath); } catch {}
  });

  assert.deepEqual(buildDockerImportCommands(tempPath, { ollamaModel: 'custom-model:latest' }), [
    ['docker', 'compose', 'up', '-d'],
    ['docker', 'compose', 'exec', '-T', 'ollama', 'ollama', 'pull', 'custom-model:latest'],
    ['docker', 'compose', 'cp', tempPath, 'n8n:/tmp/b2-2-workflow.json'],
    [
      'docker',
      'compose',
      'exec',
      '-T',
      'n8n',
      'n8n',
      'import:workflow',
      '--input=/tmp/b2-2-workflow.json',
    ],
    [
      'docker',
      'compose',
      'exec',
      '-T',
      'n8n',
      'n8n',
      'publish:workflow',
      '--id=main-id',
    ],
    [
      'docker',
      'compose',
      'exec',
      '-T',
      'n8n',
      'n8n',
      'publish:workflow',
      '--id=error-id',
    ],
    ['docker', 'compose', 'restart', 'n8n'],
  ]);
});

test('extracts env assignments from prior Notion database creation result', () => {
  assert.deepEqual(
    assignmentsFromCreatedDatabaseResult({
      created: {
        news: { envName: 'NOTION_NEWS_DB_ID', id: 'news-db' },
        rssConfig: { envName: 'NOTION_RSS_CONFIG_DB_ID', id: 'rss-db' },
        topicConfig: { envName: 'NOTION_TOPIC_CONFIG_DB_ID', id: 'topic-db' },
      },
    }),
    {
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    },
  );
});
