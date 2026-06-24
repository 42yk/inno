import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

import {
  assignmentsFromCreatedDatabaseResult,
  buildDockerImportCommands,
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
