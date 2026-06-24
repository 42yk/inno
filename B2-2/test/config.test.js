import test from 'node:test';
import assert from 'node:assert/strict';

import { loadConfigFromEnv } from '../scripts/lib/config.js';

test('uses qwen3:6b and Newswire RSS as defaults', () => {
  const config = loadConfigFromEnv({});

  assert.equal(config.ollamaModel, 'qwen3:6b');
  assert.deepEqual(config.defaultRssSources, [
    {
      name: 'Newswire 전체 뉴스',
      url: 'https://api.newswire.co.kr/rss/all',
    },
  ]);
});

test('loads Notion database ids without requiring n8n credentials', () => {
  const config = loadConfigFromEnv({
    NOTION_NEWS_DB_ID: 'news-db',
    NOTION_RSS_CONFIG_DB_ID: 'rss-db',
    NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
  });

  assert.equal(config.notionDatabases.news, 'news-db');
  assert.equal(config.notionDatabases.rssConfig, 'rss-db');
  assert.equal(config.notionDatabases.topicConfig, 'topic-db');
});

test('does not expose local n8n API configuration', () => {
  const config = loadConfigFromEnv({
    N8N_BASE_URL: 'http://localhost:5678',
    N8N_API_KEY: 'unused',
  });

  assert.equal('n8nBaseUrl' in config, false);
  assert.equal('n8nApiKey' in config, false);
});
