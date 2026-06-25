import test from 'node:test';
import assert from 'node:assert/strict';

import { loadConfigFromEnv } from '../scripts/lib/config.js';
import { buildDiscordErrorWorkflow, buildWorkflow, buildWorkflows } from '../scripts/lib/workflow.js';

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

test('adds visual sticky note sections that match the assignment workflow example', () => {
  const config = loadConfigFromEnv({
    NOTION_NEWS_DB_ID: 'news-db',
    NOTION_RSS_CONFIG_DB_ID: 'rss-db',
    NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
  });
  const workflow = buildWorkflow(config);
  const errorWorkflow = buildDiscordErrorWorkflow(config);

  const stickyNotes = [...workflow.nodes, ...errorWorkflow.nodes].filter((node) => {
    return node.type === 'n8n-nodes-base.stickyNote';
  });
  const mainStickyNotes = workflow.nodes.filter((node) => node.type === 'n8n-nodes-base.stickyNote');
  const errorStickyNotes = errorWorkflow.nodes.filter((node) => node.type === 'n8n-nodes-base.stickyNote');

  assert.equal(stickyNotes.length, 6);
  assert.equal(mainStickyNotes.length, 5);
  assert.equal(errorStickyNotes.length, 1);
  for (const note of stickyNotes) {
    assert.equal(note.typeVersion, 1);
    assert.equal(typeof note.parameters.content, 'string');
    assert.equal(typeof note.parameters.width, 'number');
    assert.equal(typeof note.parameters.height, 'number');
  }
  assert.deepEqual(
    stickyNotes.map((note) => note.parameters.content.split('\n')[0]),
    [
      '## [1] 스케줄/Webhook 트리거',
      '## [2] RSS 수집',
      '## [3] 주제 필터링',
      '## [4] AI 요약',
      '## [5] 노션 DB 저장',
      '## [6] 예외 처리',
    ],
  );
});

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

test('webhook trigger uses the same runtime entrypoint for production failure testing', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      NEWS_WEBHOOK_PATH: 'custom/news/run',
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  const webhookNode = nodeByName(workflow, 'WebhookTrigger');

  assert.equal(webhookNode.type, 'n8n-nodes-base.webhook');
  assert.equal(webhookNode.typeVersion, 2.1);
  assert.equal(webhookNode.webhookId, 'b2-2-rss-ai-news-summary');
  assert.equal(webhookNode.parameters.httpMethod, 'POST');
  assert.equal(webhookNode.parameters.path, 'custom/news/run');
  assert.equal(webhookNode.parameters.responseMode, 'onReceived');
  assert.equal(webhookNode.parameters.authentication, 'none');
  assert.deepEqual(workflow.connections.WebhookTrigger.main[0], [
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

test('connects the main workflow to a Discord error workflow', () => {
  const config = loadConfigFromEnv({
    NOTION_NEWS_DB_ID: 'news-db',
    NOTION_RSS_CONFIG_DB_ID: 'rss-db',
    NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
  });
  const workflow = buildWorkflow(config);
  const errorWorkflow = buildDiscordErrorWorkflow(config);

  assert.equal(workflow.settings.errorWorkflow, errorWorkflow.id);
  assert.equal(errorWorkflow.name, 'B2-2 Discord Error Notifier');
  assert.equal(nodeByName(errorWorkflow, 'Workflow Error Trigger').type, 'n8n-nodes-base.errorTrigger');
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

test('retries Notion query and save requests up to the configured retry limit', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      MAX_RETRY_COUNT: '2',
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  const notionNodeNames = [
    'Query RSS Sources',
    'Query Topic Keywords',
    'Check Notion Duplicate',
    'Save Notion Summary',
  ];

  for (const nodeName of notionNodeNames) {
    const node = nodeByName(workflow, nodeName);
    assert.equal(node.retryOnFail, true, nodeName);
    assert.equal(node.maxTries, 2, nodeName);
    assert.equal(node.waitBetweenTries, 1000, nodeName);
  }
});

test('retries RSS feed reads up to the configured retry limit', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      MAX_RETRY_COUNT: '2',
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  const rssNode = nodeByName(workflow, 'Read RSS Items');

  assert.equal(rssNode.retryOnFail, true);
  assert.equal(rssNode.maxTries, 2);
  assert.equal(rssNode.waitBetweenTries, 1000);
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

test('notifies Discord after a Notion save succeeds', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  const buildMessageNode = nodeByName(workflow, 'Build Discord Success Message');
  const notifyNode = nodeByName(workflow, 'Notify Discord Success');

  assert.match(buildMessageNode.parameters.jsCode, /\[B2-2\] workflow succeeded/);
  assert.equal(notifyNode.type, 'n8n-nodes-base.httpRequest');
  assert.equal(notifyNode.typeVersion, 4.4);
  assert.equal(notifyNode.parameters.method, 'POST');
  assert.equal(notifyNode.parameters.url, '={{ $env.DISCORD_WEBHOOK_URL }}');
  assert.equal(notifyNode.parameters.contentType, 'json');
  assert.equal(notifyNode.parameters.specifyBody, 'json');
  assert.equal(notifyNode.parameters.jsonBody, '={{ JSON.stringify({ content: $json.discordContent }) }}');
  assert.equal(notifyNode.continueOnFail, true);
  assert.equal(notifyNode.retryOnFail, true);
  assert.deepEqual(workflow.connections['Save Notion Summary'].main[0], [
    { node: 'Log Result', type: 'main', index: 0 },
  ]);
  assert.deepEqual(workflow.connections['Log Result'].main[0], [
    { node: 'Build Discord Success Message', type: 'main', index: 0 },
  ]);
  assert.deepEqual(workflow.connections['Build Discord Success Message'].main[0], [
    { node: 'Notify Discord Success', type: 'main', index: 0 },
  ]);
});

test('retries Ollama summary requests up to the configured retry limit', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      MAX_RETRY_COUNT: '2',
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  const ollamaNode = nodeByName(workflow, 'Summarize With Ollama');

  assert.equal(ollamaNode.retryOnFail, true);
  assert.equal(ollamaNode.maxTries, 2);
  assert.equal(ollamaNode.waitBetweenTries, 1000);
});

test('builds a Discord error workflow for failed executions', () => {
  const errorWorkflow = buildDiscordErrorWorkflow(
    loadConfigFromEnv({
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  const notifyNode = nodeByName(errorWorkflow, 'Notify Discord Failure');
  const buildMessageNode = nodeByName(errorWorkflow, 'Build Discord Failure Message');
  const exceptionNote = nodeByName(errorWorkflow, 'Section 6 Exception Handling');

  assert.equal(errorWorkflow.nodes.length, 5);
  assert.equal(exceptionNote.type, 'n8n-nodes-base.stickyNote');
  assert.match(buildMessageNode.parameters.jsCode, /\[B2-2\] workflow failed/);
  assert.equal(notifyNode.parameters.url, '={{ $env.DISCORD_WEBHOOK_URL }}');
  assert.equal(notifyNode.parameters.jsonBody, '={{ JSON.stringify({ content: $json.discordContent }) }}');
  assert.equal(notifyNode.continueOnFail, true);
  assert.equal(notifyNode.retryOnFail, true);
  assert.deepEqual(errorWorkflow.connections['Workflow Error Trigger'].main[0], [
    { node: 'Build Discord Failure Message', type: 'main', index: 0 },
  ]);
});

test('exports both main and error workflows for n8n import', () => {
  const workflows = buildWorkflows(
    loadConfigFromEnv({
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  assert.deepEqual(workflows.map((workflow) => workflow.name), [
    'B2-2 RSS AI News Summary',
    'B2-2 Discord Error Notifier',
  ]);
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
  assert.equal(ollamaBody.model, 'gemma3:1b');
  assert.match(ollamaBody.prompt, /Sample title/);
  assert.equal(saveBody.properties.Title.title[0].text.content, 'Sample title');
  assert.deepEqual(saveBody.properties['Matched Keywords'].multi_select, [{ name: 'AI' }, { name: 'n8n' }]);
});

test('uses a static Ollama endpoint URL so n8n does not reset the node settings', () => {
  const workflow = buildWorkflow(
    loadConfigFromEnv({
      OLLAMA_BASE_URL: 'http://ollama:11434',
      NOTION_NEWS_DB_ID: 'news-db',
      NOTION_RSS_CONFIG_DB_ID: 'rss-db',
      NOTION_TOPIC_CONFIG_DB_ID: 'topic-db',
    }),
  );

  const node = nodeByName(workflow, 'Summarize With Ollama');
  assert.equal(node.parameters.url, 'http://ollama:11434/api/generate');
  assert.equal(node.parameters.contentType, 'json');
  assert.equal(node.parameters.specifyBody, 'json');
  assert.match(node.parameters.jsonBody, /^=\{\{ JSON\.stringify\(/);
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
