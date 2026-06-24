function node({ name, type, position, parameters = {}, typeVersion = 1 }) {
  return {
    parameters,
    id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''),
    name,
    type,
    typeVersion,
    position,
  };
}

function connect(connections, from, to, outputIndex = 0) {
  connections[from] ??= { main: [] };
  connections[from].main[outputIndex] ??= [];
  connections[from].main[outputIndex].push({
    node: to,
    type: 'main',
    index: 0,
  });
}

function jsonStringifyExpression(source) {
  return `={{ JSON.stringify(${source}) }}`;
}

function notionQueryParameters(databaseId, filterExpression) {
  return {
    method: 'POST',
    url: `https://api.notion.com/v1/databases/${databaseId}/query`,
    sendHeaders: true,
    headerParameters: {
      parameters: [
        { name: 'Authorization', value: '={{ "Bearer " + $env.NOTION_API_TOKEN }}' },
        { name: 'Notion-Version', value: '2022-06-28' },
        { name: 'Content-Type', value: 'application/json' },
      ],
    },
    sendBody: true,
    contentType: 'json',
    specifyBody: 'json',
    jsonBody: filterExpression,
    options: {
      timeout: 30000,
    },
  };
}

function notionCreatePageParameters(databaseId, bodyExpression) {
  return {
    method: 'POST',
    url: 'https://api.notion.com/v1/pages',
    sendHeaders: true,
    headerParameters: {
      parameters: [
        { name: 'Authorization', value: '={{ "Bearer " + $env.NOTION_API_TOKEN }}' },
        { name: 'Notion-Version', value: '2022-06-28' },
        { name: 'Content-Type', value: 'application/json' },
      ],
    },
    sendBody: true,
    contentType: 'json',
    specifyBody: 'json',
    jsonBody: bodyExpression.replaceAll('__DATABASE_ID__', databaseId),
  };
}

export function buildWorkflow(config) {
  const nodes = [
    node({
      name: 'Manual Start',
      type: 'n8n-nodes-base.manualTrigger',
      position: [0, 0],
    }),
    node({
      name: 'Daily Schedule',
      type: 'n8n-nodes-base.scheduleTrigger',
      position: [0, 180],
      parameters: {
        rule: {
          interval: [
            {
              field: 'cronExpression',
              expression: `={{ $env.NEWS_CRON_EXPRESSION || "${config.schedule.cronExpression}" }}`,
            },
          ],
        },
        timezone: `={{ $env.NEWS_TIMEZONE || "${config.schedule.timezone}" }}`,
      },
    }),
    node({
      name: 'Query RSS Sources',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.4,
      position: [260, 80],
      parameters: notionQueryParameters(
        config.notionDatabases.rssConfig,
        '{"filter":{"property":"Enabled","checkbox":{"equals":true}}}',
      ),
    }),
    node({
      name: 'RSS Sources Empty?',
      type: 'n8n-nodes-base.if',
      position: [1040, 80],
      parameters: {
        conditions: {
          number: [
            {
              value1: '={{ $json.results.length }}',
              operation: 'equal',
              value2: 0,
            },
          ],
        },
      },
    }),
    node({
      name: 'Log No RSS Sources',
      type: 'n8n-nodes-base.code',
      position: [1300, -40],
      parameters: {
        jsCode: `console.log('NO_RSS_SOURCES');
return [];`,
      },
    }),
    node({
      name: 'Query Topic Keywords',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.4,
      position: [1300, 80],
      parameters: notionQueryParameters(
        config.notionDatabases.topicConfig,
        '{"filter":{"property":"Enabled","checkbox":{"equals":true}}}',
      ),
    }),
    node({
      name: 'Topic Keywords Empty?',
      type: 'n8n-nodes-base.if',
      position: [1560, 80],
      parameters: {
        conditions: {
          number: [
            {
              value1: '={{ $json.results.length }}',
              operation: 'equal',
              value2: 0,
            },
          ],
        },
      },
    }),
    node({
      name: 'Log Topic Config Empty',
      type: 'n8n-nodes-base.code',
      position: [1820, -40],
      parameters: {
        jsCode: `console.log('TOPIC_CONFIG_EMPTY');
return [];`,
      },
    }),
    node({
      name: 'Build RSS Source Items',
      type: 'n8n-nodes-base.code',
      position: [1820, 80],
      parameters: {
        jsCode: `const rows = $items('Query RSS Sources').flatMap((item) => item.json.results || []);
return rows
  .map((row) => {
    const properties = row.properties || {};
    return {
      json: {
        sourceName: properties.Name?.title?.[0]?.plain_text || 'RSS Source',
        feedUrl: properties['Feed URL']?.url || '',
      },
    };
  })
  .filter((item) => item.json.feedUrl);`,
      },
    }),
    node({
      name: 'Read RSS Items',
      type: 'n8n-nodes-base.rssFeedRead',
      position: [2340, 80],
      parameters: {
        url: '={{ $json.feedUrl }}',
        options: {
          timeout: config.rssFetchTimeoutMs,
        },
      },
    }),
    node({
      name: 'Normalize RSS Items',
      type: 'n8n-nodes-base.code',
      position: [2600, 80],
      parameters: {
        jsCode: `return items.map((item) => {
  const source = item.json;
  const originalUrl = source.link || source.guid || '';
  const guid = source.guid || source.id || '';
  return {
    json: {
      title: source.title || '',
      originalUrl,
      guid,
      dedupeKey: guid || originalUrl,
      publishedAt: source.isoDate || source.pubDate || new Date().toISOString(),
      content: source.content || source.contentSnippet || source.description || '',
      source: $json.sourceName || 'RSS Source'
    }
  };
});`,
      },
    }),
    node({
      name: 'Filter Candidates',
      type: 'n8n-nodes-base.code',
      position: [2860, 80],
      parameters: {
        jsCode: `const fallbackKeywords = ${JSON.stringify(config.defaultTopicKeywords)};
const topicRows = $items('Query Topic Keywords').flatMap((item) => item.json.results || []);
const keywords = topicRows
  .map((row) => row.properties?.Keyword?.title?.[0]?.plain_text)
  .filter(Boolean);
const activeKeywords = (keywords.length > 0 ? keywords : fallbackKeywords).map((keyword) => keyword.toLowerCase());
return items.filter((item) => {
  const text = [item.json.title, item.json.content].join(' ').toLowerCase();
  const matchedKeywords = activeKeywords.filter((keyword) => text.includes(keyword.toLowerCase()));
  item.json.matchedKeywords = matchedKeywords;
  return matchedKeywords.length > 0;
});`,
      },
    }),
    node({
      name: 'Select Latest Candidate',
      type: 'n8n-nodes-base.code',
      position: [3120, 80],
      parameters: {
        jsCode: `const sorted = [...items].sort((a, b) => {
  return new Date(b.json.publishedAt).getTime() - new Date(a.json.publishedAt).getTime();
});
return sorted.slice(0, 1);`,
      },
    }),
    node({
      name: 'Check Notion Duplicate',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.4,
      position: [3380, 80],
      parameters: notionQueryParameters(
        config.notionDatabases.news,
        jsonStringifyExpression(`{
          filter: {
            or: [
              { property: "Dedupe Key", rich_text: { equals: $json.dedupeKey || "" } },
              { property: "Original URL", url: { equals: $json.originalUrl || "" } },
            ],
          },
        }`),
      ),
    }),
    node({
      name: 'Skip Duplicate',
      type: 'n8n-nodes-base.if',
      position: [3640, 80],
      parameters: {
        conditions: {
          number: [
            {
              value1: '={{ $json.results.length }}',
              operation: 'larger',
              value2: 0,
            },
          ],
        },
      },
    }),
    node({
      name: 'Restore Selected Candidate',
      type: 'n8n-nodes-base.code',
      position: [3900, 180],
      parameters: {
        jsCode: `const candidate = $items('Select Latest Candidate')[0]?.json;
if (!candidate) {
  throw new Error('CANDIDATE_RESTORE_FAILED');
}
return [{ json: candidate }];`,
      },
    }),
    node({
      name: 'Summarize With Ollama',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.4,
      position: [4160, 180],
      parameters: {
        method: 'POST',
        url: `=${config.ollamaBaseUrl}/api/generate`,
        sendBody: true,
        contentType: 'json',
        specifyBody: 'json',
        jsonBody: jsonStringifyExpression(`{
          model: ${JSON.stringify(config.ollamaModel)},
          stream: false,
          prompt: "아래 뉴스 내용을 한국어로 3줄 이내로 요약해줘. 과장하지 말고 기사에 있는 사실만 사용해. 각 줄은 하나의 핵심 내용을 담아줘.\\n\\n제목: " + ($json.title || "") + "\\n본문: " + ($json.content || ""),
        }`),
        options: {
          timeout: config.ollamaTimeoutMs,
        },
      },
    }),
    node({
      name: 'Validate Summary',
      type: 'n8n-nodes-base.code',
      position: [4420, 180],
      parameters: {
        jsCode: `const candidate = $items('Restore Selected Candidate')[0]?.json || {};
const response = $json.response || '';
const lines = response.split(/\\r?\\n/).map((line) => line.trim()).filter(Boolean);
if (!response.trim()) {
  throw new Error('OLLAMA_EMPTY_RESPONSE');
}
if (lines.length > 3) {
  throw new Error('SUMMARY_INVALID');
}
return [{ json: { ...candidate, summary: lines.join('\\n') } }];`,
      },
    }),
    node({
      name: 'Save Notion Summary',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.4,
      position: [4680, 180],
      parameters: notionCreatePageParameters(
        config.notionDatabases.news,
        jsonStringifyExpression(`{
          parent: { database_id: "__DATABASE_ID__" },
          properties: {
            Title: { title: [{ type: "text", text: { content: $json.title || "" } }] },
            Summary: { rich_text: [{ type: "text", text: { content: $json.summary || "" } }] },
            "Original URL": { url: $json.originalUrl || null },
            "Published At": { date: { start: $json.publishedAt || new Date().toISOString() } },
            "Dedupe Key": { rich_text: [{ type: "text", text: { content: $json.dedupeKey || "" } }] },
            Source: { rich_text: [{ type: "text", text: { content: $json.source || "" } }] },
            "Matched Keywords": { multi_select: ($json.matchedKeywords || []).map((name) => ({ name })) },
            Status: { select: { name: "Saved" } },
            "AI Model": { rich_text: [{ type: "text", text: { content: ${JSON.stringify(config.ollamaModel)} } }] },
            "Saved At": { date: { start: new Date().toISOString() } },
          },
        }`),
      ),
    }),
    node({
      name: 'Log Result',
      type: 'n8n-nodes-base.code',
      position: [4940, 180],
      parameters: {
        jsCode: `console.log('SAVED_TO_NOTION', $json.id || $json);
return items;`,
      },
    }),
  ];

  const connections = {};
  connect(connections, 'Manual Start', 'Query RSS Sources');
  connect(connections, 'Daily Schedule', 'Query RSS Sources');
  connect(connections, 'Query RSS Sources', 'RSS Sources Empty?');
  connect(connections, 'RSS Sources Empty?', 'Log No RSS Sources', 0);
  connect(connections, 'RSS Sources Empty?', 'Query Topic Keywords', 1);
  connect(connections, 'Query Topic Keywords', 'Topic Keywords Empty?');
  connect(connections, 'Topic Keywords Empty?', 'Log Topic Config Empty', 0);
  connect(connections, 'Topic Keywords Empty?', 'Build RSS Source Items', 1);
  connect(connections, 'Build RSS Source Items', 'Read RSS Items');
  connect(connections, 'Read RSS Items', 'Normalize RSS Items');
  connect(connections, 'Normalize RSS Items', 'Filter Candidates');
  connect(connections, 'Filter Candidates', 'Select Latest Candidate');
  connect(connections, 'Select Latest Candidate', 'Check Notion Duplicate');
  connect(connections, 'Check Notion Duplicate', 'Skip Duplicate');
  connect(connections, 'Skip Duplicate', 'Restore Selected Candidate', 1);
  connect(connections, 'Restore Selected Candidate', 'Summarize With Ollama');
  connect(connections, 'Summarize With Ollama', 'Validate Summary');
  connect(connections, 'Validate Summary', 'Save Notion Summary');
  connect(connections, 'Save Notion Summary', 'Log Result');

  return {
    id: '6f9f5eec-3a5a-4ac7-901b-bb12c1f9f322',
    name: config.workflowName,
    nodes,
    connections,
    settings: {
      executionOrder: 'v1',
      timezone: config.schedule.timezone,
      saveExecutionProgress: true,
      saveManualExecutions: true,
    },
    staticData: null,
    tags: [],
    active: config.activateWorkflow,
  };
}
