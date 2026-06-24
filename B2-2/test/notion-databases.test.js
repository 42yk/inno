import test from 'node:test';
import assert from 'node:assert/strict';

import { buildDatabaseRequests, buildDefaultSeedRequests } from '../scripts/lib/notion-databases.js';

test('builds three Notion database creation requests under the parent page', () => {
  const requests = buildDatabaseRequests('parent-page-id');

  assert.deepEqual(
    requests.map((request) => request.key),
    ['news', 'rssConfig', 'topicConfig'],
  );

  for (const request of requests) {
    assert.equal(request.body.parent.type, 'page_id');
    assert.equal(request.body.parent.page_id, 'parent-page-id');
  }
});

test('news database contains summary result properties', () => {
  const [news] = buildDatabaseRequests('parent-page-id');

  assert.ok(news.body.properties.Title.title);
  assert.ok(news.body.properties.Summary.rich_text);
  assert.ok(news.body.properties['Original URL'].url);
  assert.ok(news.body.properties['Published At'].date);
  assert.ok(news.body.properties['Dedupe Key'].rich_text);
  assert.ok(news.body.properties.Status.select);
});

test('config databases contain editable RSS and topic properties', () => {
  const [, rssConfig, topicConfig] = buildDatabaseRequests('parent-page-id');

  assert.ok(rssConfig.body.properties.Name.title);
  assert.ok(rssConfig.body.properties['Feed URL'].url);
  assert.ok(rssConfig.body.properties.Enabled.checkbox);

  assert.ok(topicConfig.body.properties.Keyword.title);
  assert.ok(topicConfig.body.properties.Enabled.checkbox);
  assert.ok(topicConfig.body.properties['Match Target'].select);
});

test('builds idempotent default config seed requests', () => {
  const requests = buildDefaultSeedRequests({
    notionDatabases: {
      rssConfig: 'rss-db',
      topicConfig: 'topic-db',
    },
  });

  assert.deepEqual(
    requests.map((request) => request.key),
    ['defaultRssSource', 'defaultTopicKeyword'],
  );

  assert.deepEqual(requests[0].queryBody, {
    filter: {
      property: 'Feed URL',
      url: { equals: 'https://api.newswire.co.kr/rss/all' },
    },
  });
  assert.equal(requests[0].createBody.parent.database_id, 'rss-db');
  assert.equal(requests[0].createBody.properties.Name.title[0].text.content, 'Newswire 전체 뉴스');

  assert.deepEqual(requests[1].queryBody, {
    filter: {
      property: 'Keyword',
      title: { equals: 'AI' },
    },
  });
  assert.equal(requests[1].createBody.parent.database_id, 'topic-db');
  assert.equal(requests[1].createBody.properties.Keyword.title[0].text.content, 'AI');
});
