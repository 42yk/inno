import test from 'node:test';
import assert from 'node:assert/strict';

import { loadConfigFromEnv } from '../scripts/lib/config.js';
import { buildWorkflow } from '../scripts/lib/workflow.js';

function names(workflow) {
  return workflow.nodes.map((node) => node.name);
}

function indexOf(workflow, nodeName) {
  return names(workflow).indexOf(nodeName);
}

function nodeByName(workflow, nodeName) {
  return workflow.nodes.find((node) => node.name === nodeName);
}

function parseJsonBodyExpression(jsonBody, itemJson) {
  assert.match(jsonBody, /^=\{\{ JSON\.stringify\(/);
  const expression = jsonBody.slice(3, -2).trim();
  const result = Function('$json', `return (${expression});`)(itemJson);
  return JSON.parse(result);
}

test('manual start and schedule use the same runtime entrypoint', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  assert.equal(workflow.name, 'B2-2 RSS AI News Summary');
  assert.equal(indexOf(workflow, 'Seed Default RSS Source'), -1);
  assert.equal(indexOf(workflow, 'Seed Default Topic Keywords'), -1);
  assert.deepEqual(workflow.connections['Manual Start'].main[0], [
    { node: 'Query RSS Sources', type: 'main', index: 0 },
  ]);
  assert.deepEqual(workflow.connections['Daily Schedule'].main[0], [
    { node: 'Query RSS Sources', type: 'main', index: 0 },
  ]);
});

test('includes a stable workflow id for n8n CLI imports', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  assert.equal(workflow.id, '6f9f5eec-3a5a-4ac7-901b-bb12c1f9f322');
});

test('uses the activation flag for the workflow active state', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      N8N_ACTIVATE_WORKFLOW: 'true',
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  assert.equal(workflow.active, true);
});

test('uses NOTION_API_TOKEN environment variable on every Notion HTTP node', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  const notionNodes = workflow.nodes.filter((node) => {
    return String(node.parameters.url || '').includes('api.notion.com');
  });
  assert.ok(notionNodes.length >= 4);

  for (const node of notionNodes) {
    assert.equal(node.typeVersion, 4.4, node.name);
    assert.equal(node.parameters.method, 'POST', node.name);
    assert.equal(node.parameters.requestMethod, undefined, node.name);
    assert.equal(node.parameters.sendBody, true, node.name);
    assert.equal(node.parameters.contentType, 'json', node.name);
    assert.equal(node.parameters.specifyBody, 'json', node.name);
    assert.equal(typeof node.parameters.jsonBody, 'string', node.name);
    const headers = node.parameters.headerParameters.parameters;
    const authorization = headers.find((header) => header.name === 'Authorization');
    assert.equal(authorization?.value, '={{ "Bearer " + $env.NOTION_API_TOKEN }}', node.name);
    assert.equal(String(node.parameters.url).startsWith('='), false, node.name);
    assert.equal(node.credentials, undefined, node.name);
  }
});

test('sends JSON bodies through the HTTP Request JSON body mode', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  const httpNodes = workflow.nodes.filter((node) => {
    return node.type === 'n8n-nodes-base.httpRequest' && node.parameters.sendBody;
  });

  assert.ok(httpNodes.length > 0);
  for (const node of httpNodes) {
    assert.equal(node.typeVersion, 4.4, node.name);
    assert.equal(node.parameters.contentType, 'json', node.name);
    assert.equal(node.parameters.specifyBody, 'json', node.name);
    assert.equal(typeof node.parameters.jsonBody, 'string', node.name);
  }
});

test('serializes dynamic HTTP JSON bodies before n8n parses them', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  for (const nodeName of ['Check Notion Duplicate', 'Summarize With Ollama', 'Save Notion Summary']) {
    const node = nodeByName(workflow, nodeName);
    assert.match(node.parameters.jsonBody, /^=\{\{ JSON\.stringify\(/, nodeName);
    assert.doesNotMatch(node.parameters.jsonBody, /^=\{(?!\{)/, nodeName);
  }

  const sampleItem = {
    title: 'Sample title',
    summary: 'Line 1\nLine 2',
    originalUrl: 'https://example.com/news/1',
    dedupeKey: 'guid-1',
    publishedAt: '2026-06-24T00:00:00.000Z',
    source: 'Sample RSS',
    content: 'Sample body',
    matchedKeywords: ['AI', 'n8n'],
  };
  const duplicateBody = parseJsonBodyExpression(
    nodeByName(workflow, 'Check Notion Duplicate').parameters.jsonBody,
    sampleItem,
  );
  const ollamaBody = parseJsonBodyExpression(
    nodeByName(workflow, 'Summarize With Ollama').parameters.jsonBody,
    sampleItem,
  );
  const saveBody = parseJsonBodyExpression(
    nodeByName(workflow, 'Save Notion Summary').parameters.jsonBody,
    sampleItem,
  );

  assert.equal(duplicateBody.filter.or[0].rich_text.equals, 'guid-1');
  assert.equal(duplicateBody.filter.or[1].url.equals, 'https://example.com/news/1');
  assert.equal(ollamaBody.model, 'qwen3.6:latest');
  assert.match(ollamaBody.prompt, /Sample title/);
  assert.equal(saveBody.properties.Title.title[0].text.content, 'Sample title');
  assert.deepEqual(saveBody.properties['Matched Keywords'].multi_select, [{ name: 'AI' }, { name: 'n8n' }]);
});

test('checks Notion duplicate records before Ollama summary call', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  assert.ok(indexOf(workflow, 'Check Notion Duplicate') < indexOf(workflow, 'Summarize With Ollama'));
});

test('restores the selected candidate after duplicate lookup before calling Ollama', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  const validateNode = workflow.nodes.find((node) => node.name === 'Validate Summary');

  assert.ok(indexOf(workflow, 'Skip Duplicate') < indexOf(workflow, 'Restore Selected Candidate'));
  assert.ok(indexOf(workflow, 'Restore Selected Candidate') < indexOf(workflow, 'Summarize With Ollama'));
  assert.deepEqual(workflow.connections['Skip Duplicate'].main[1], [
    { node: 'Restore Selected Candidate', type: 'main', index: 0 },
  ]);
  assert.match(validateNode.parameters.jsCode, /\$items\('Restore Selected Candidate'\)/);
});

test('reads RSS URLs and topic keywords from Notion config results at runtime', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  const readRssNode = workflow.nodes.find((node) => node.name === 'Read RSS Items');
  const filterNode = workflow.nodes.find((node) => node.name === 'Filter Candidates');

  assert.ok(indexOf(workflow, 'Build RSS Source Items') < indexOf(workflow, 'Read RSS Items'));
  assert.equal(readRssNode.parameters.url, '={{ $json.feedUrl }}');
  assert.match(filterNode.parameters.jsCode, /\$items\('Query Topic Keywords'\)/);
});

test('daily schedule allows zero RSS sources without reseeding defaults', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  assert.deepEqual(workflow.connections['Daily Schedule'].main[0], [
    { node: 'Query RSS Sources', type: 'main', index: 0 },
  ]);
  assert.deepEqual(workflow.connections['RSS Sources Empty?'].main[0], [
    { node: 'Log No RSS Sources', type: 'main', index: 0 },
  ]);
  assert.deepEqual(workflow.connections['RSS Sources Empty?'].main[1], [
    { node: 'Query Topic Keywords', type: 'main', index: 0 },
  ]);
});
