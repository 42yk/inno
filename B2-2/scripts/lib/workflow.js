export const MAIN_WORKFLOW_ID = '6f9f5eec-3a5a-4ac7-901b-bb12c1f9f322';
export const DISCORD_ERROR_WORKFLOW_ID = 'c73fd802-6fb8-46d7-a4f0-d059b88f504b';
export const MAIN_WEBHOOK_ID = 'b2-2-rss-ai-news-summary';
export const SUMMARY_PROMPT_VERSION = 'v1';

function node({ name, type, position, parameters = {}, typeVersion = 1, ...extra }) {
  return {
    parameters,
    id: name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''),
    name,
    type,
    typeVersion,
    position,
    ...extra,
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

function stickyNote({ name, position, width, height, color, content }) {
  return node({
    name,
    type: 'n8n-nodes-base.stickyNote',
    typeVersion: 1,
    position,
    parameters: {
      content,
      height,
      width,
      color,
    },
  });
}

function discordWebhookParameters(bodyExpression) {
  return {
    method: 'POST',
    url: '={{ $env.DISCORD_WEBHOOK_URL }}',
    sendBody: true,
    contentType: 'json',
    specifyBody: 'json',
    jsonBody: bodyExpression,
    options: {
      timeout: 10000,
    },
  };
}

function retryOnFailOptions(config) {
  return {
    retryOnFail: true,
    maxTries: config.maxRetryCount,
    waitBetweenTries: 1000,
  };
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

function articleBodyRequestParameters(config) {
  return {
    method: 'GET',
    url: '={{ $json.originalUrl }}',
    sendHeaders: true,
    headerParameters: {
      parameters: [
        { name: 'User-Agent', value: 'Mozilla/5.0 (compatible; B2-2 RSS AI News Summary/1.0)' },
        { name: 'Accept', value: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' },
      ],
    },
    options: {
      timeout: config.rssFetchTimeoutMs,
      response: {
        response: {
          responseFormat: 'text',
          outputPropertyName: 'articleHtml',
        },
      },
    },
  };
}

function summaryPromptExpression() {
  const promptPrefix = [
    '아래 뉴스 내용을 한국어로 3줄 이내로 요약해줘.',
    '과장하지 말고 기사에 있는 사실만 사용해.',
    '각 줄은 하나의 핵심 내용을 담아줘.',
    '',
    '제목: ',
  ].join('\n');

  return `${JSON.stringify(promptPrefix)} + ($json.title || "") + ${JSON.stringify('\n본문: ')} + ($json.content || "")`;
}

export function buildWorkflow(config) {
  const nodes = [
    stickyNote({
      name: 'Section 1 Schedule Trigger',
      position: [-128, -304],
      width: 500,
      height: 768,
      color: 4,
      content: '## [1] 스케줄/Webhook 트리거\n매일 설정된 시간 또는 Webhook으로 실행\n\n- 기본: 매일 09:00\n- 타임존: Asia/Seoul\n- Webhook: POST /webhook/NEWS_WEBHOOK_PATH\n- Manual Start는 편집 중 수동 확인용',
    }),
    stickyNote({
      name: 'Section 2 RSS Collection',
      position: [416, -304],
      width: 1832,
      height: 560,
      color: 5,
      content: '## [2] RSS 수집\nNotion 설정 DB의 RSS 목록에서 기사 수집\n\n- 활성 RSS 목록 조회\n- RSS 0건이면 로그 후 정상 종료\n- 피드 항목을 표준 뉴스 필드로 정규화',
    }),
    stickyNote({
      name: 'Section 3 Topic Filtering',
      position: [2336, -304],
      width: 1080,
      height: 560,
      color: 6,
      content: '## [3] 주제 필터링\n키워드 기준으로 조건 만족 기사 1건 선택\n\n- Notion 주제 키워드 DB 조회\n- 제목/본문 키워드 매칭\n- 최신 기사 1건 선택',
    }),
    stickyNote({
      name: 'Section 4 AI Summary',
      position: [3440, -304],
      width: 596,
      height: 560,
      color: 3,
      content: '## [4] AI 요약\nOllama로 3줄 이내 요약 생성\n\n- 중복 확인 후에만 AI 호출\n- 모델: OLLAMA_MODEL\n- v1 프롬프트: 3줄 요약 + 기사 사실만 사용\n- 빈 응답/3줄 초과는 실패 처리',
    }),
    stickyNote({
      name: 'Section 5 Notion Save',
      position: [4064, -304],
      width: 760,
      height: 560,
      color: 2,
      content: '## [5] 노션 DB 저장\n요약 결과를 Notion 결과 DB에 저장\n\n- Title / Summary / URL / Date 매핑\n- Dedupe Key 저장\n- 성공 시 Discord 알림',
    }),
    node({
      name: 'Manual Start',
      type: 'n8n-nodes-base.manualTrigger',
      position: [-64, -64],
    }),
    node({
      name: 'Daily Schedule',
      type: 'n8n-nodes-base.scheduleTrigger',
      position: [-64, 128],
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
      name: 'WebhookTrigger',
      type: 'n8n-nodes-base.webhook',
      typeVersion: 2.1,
      position: [-64, 320],
      webhookId: MAIN_WEBHOOK_ID,
      parameters: {
        httpMethod: 'POST',
        path: config.triggerWebhookPath,
        authentication: 'none',
        responseMode: 'onReceived',
        options: {},
      },
    }),
    node({
      name: 'Query RSS Sources',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.4,
      position: [208, 16],
      parameters: notionQueryParameters(
        config.notionDatabases.rssConfig,
        '{"filter":{"property":"Enabled","checkbox":{"equals":true}}}',
      ),
      ...retryOnFailOptions(config),
    }),
    node({
      name: 'RSS Sources Empty?',
      type: 'n8n-nodes-base.if',
      position: [496, 64],
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
      position: [768, -64],
      parameters: {
        jsCode: `console.log('NO_RSS_SOURCES');
return [];`,
      },
    }),
    node({
      name: 'Query Topic Keywords',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.4,
      position: [768, 64],
      parameters: notionQueryParameters(
        config.notionDatabases.topicConfig,
        '{"filter":{"property":"Enabled","checkbox":{"equals":true}}}',
      ),
      ...retryOnFailOptions(config),
    }),
    node({
      name: 'Topic Keywords Empty?',
      type: 'n8n-nodes-base.if',
      position: [1024, 64],
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
      position: [1280, -64],
      parameters: {
        jsCode: `console.log('TOPIC_CONFIG_EMPTY');
return [];`,
      },
    }),
    node({
      name: 'Build RSS Source Items',
      type: 'n8n-nodes-base.code',
      position: [1280, 64],
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
      position: [1456, 64],
      parameters: {
        url: '={{ $json.feedUrl }}',
        options: {
          timeout: config.rssFetchTimeoutMs,
        },
      },
      ...retryOnFailOptions(config),
    }),
    node({
      name: 'Normalize RSS Items',
      type: 'n8n-nodes-base.code',
      position: [1648, 64],
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
      name: 'Fetch Article Body',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.4,
      position: [1840, 64],
      parameters: articleBodyRequestParameters(config),
      ...retryOnFailOptions(config),
    }),
    node({
      name: 'Extract Article Body',
      type: 'n8n-nodes-base.code',
      position: [2048, 64],
      parameters: {
        jsCode: `const sourceItems = $items('Normalize RSS Items');

function decodeEntities(value) {
  return value
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/g, "'")
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&#(\\d+);/g, (_, code) => String.fromCharCode(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => String.fromCharCode(parseInt(code, 16)));
}

function htmlToText(html) {
  const bodyMatch = html.match(/<body[^>]*>([\\s\\S]*?)<\\/body>/i);
  const source = bodyMatch ? bodyMatch[1] : html;
  return decodeEntities(source
    .replace(/<script[\\s\\S]*?<\\/script>/gi, ' ')
    .replace(/<style[\\s\\S]*?<\\/style>/gi, ' ')
    .replace(/<noscript[\\s\\S]*?<\\/noscript>/gi, ' ')
    .replace(/<!--[\\s\\S]*?-->/g, ' ')
    .replace(/<\\/(p|div|br|li|tr|h[1-6])\\s*>/gi, '\\n')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\\r/g, '\\n')
    .replace(/[ \\t]+/g, ' ')
    .replace(/\\n\\s+/g, '\\n')
    .replace(/\\n{3,}/g, '\\n\\n')
    .trim());
}

return items.map((item, index) => {
  const candidate = sourceItems[index]?.json || {};
  const articleHtml = item.json.articleHtml || item.json.data || '';
  const articleText = htmlToText(String(articleHtml || ''));
  const content = (articleText || candidate.content || '').slice(0, 12000);
  return {
    json: {
      ...candidate,
      articleText,
      content,
    },
  };
});`,
      },
    }),
    node({
      name: 'Filter Candidates',
      type: 'n8n-nodes-base.code',
      position: [2384, 64],
      parameters: {
        jsCode: `const fallbackKeywords = ${JSON.stringify(config.defaultTopicKeywords)};
const topicRows = $items('Query Topic Keywords').flatMap((item) => item.json.results || []);
const keywords = topicRows
  .map((row) => row.properties?.Keyword?.title?.[0]?.plain_text)
  .filter(Boolean);
const activeKeywords = (keywords.length > 0 ? keywords : fallbackKeywords).map((keyword) => keyword.toLowerCase());
return items.filter((item) => {
  const text = [item.json.title, item.json.articleText, item.json.content].join(' ').toLowerCase();
  const matchedKeywords = activeKeywords.filter((keyword) => text.includes(keyword.toLowerCase()));
  item.json.matchedKeywords = matchedKeywords;
  return matchedKeywords.length > 0;
});`,
      },
    }),
    node({
      name: 'Select Latest Candidate',
      type: 'n8n-nodes-base.code',
      position: [2640, 64],
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
      position: [2912, 64],
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
      ...retryOnFailOptions(config),
    }),
    node({
      name: 'Skip Duplicate',
      type: 'n8n-nodes-base.if',
      position: [3168, 64],
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
      position: [3472, 64],
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
      position: [3680, 64],
      parameters: {
        method: 'POST',
        url: `${config.ollamaBaseUrl}/api/generate`,
        sendBody: true,
        contentType: 'json',
        specifyBody: 'json',
        jsonBody: jsonStringifyExpression(`{
          model: ${JSON.stringify(config.ollamaModel)},
          stream: false,
          prompt: ${summaryPromptExpression()},
        }`),
        options: {
          timeout: config.ollamaTimeoutMs,
        },
      },
      retryOnFail: true,
      maxTries: config.maxRetryCount,
      waitBetweenTries: 1000,
    }),
    node({
      name: 'Validate Summary',
      type: 'n8n-nodes-base.code',
      position: [3872, 64],
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
return [{ json: { ...candidate, summary: lines.join('\\n'), promptVersion: ${JSON.stringify(SUMMARY_PROMPT_VERSION)} } }];`,
      },
    }),
    node({
      name: 'Save Notion Summary',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.4,
      position: [4096, 64],
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
      ...retryOnFailOptions(config),
    }),
    node({
      name: 'Build Discord Success Message',
      type: 'n8n-nodes-base.code',
      position: [4480, 64],
      parameters: {
        jsCode: `const candidate = $items('Validate Summary')[0]?.json || {};
const content = [
  '타이틀: ' + (candidate.title || 'unknown'),
  '기사 원문: ' + (candidate.originalUrl || 'unknown'),
  '요약: ' + (candidate.summary || 'unknown'),
].join('\\n');
return [{ json: { discordContent: content } }];`,
      },
    }),
    node({
      name: 'Notify Discord Success',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.4,
      position: [4672, 64],
      parameters: discordWebhookParameters('={{ JSON.stringify({ content: $json.discordContent }) }}'),
      continueOnFail: true,
      retryOnFail: true,
      maxTries: config.maxRetryCount,
      waitBetweenTries: 1000,
    }),
    node({
      name: 'Log Result',
      type: 'n8n-nodes-base.code',
      position: [4288, 64],
      parameters: {
        jsCode: `console.log('SAVED_TO_NOTION', $json.id || $json);
return items;`,
      },
    }),
  ];

  const connections = {};
  connect(connections, 'Manual Start', 'Query RSS Sources');
  connect(connections, 'Daily Schedule', 'Query RSS Sources');
  connect(connections, 'WebhookTrigger', 'Query RSS Sources');
  connect(connections, 'Query RSS Sources', 'RSS Sources Empty?');
  connect(connections, 'RSS Sources Empty?', 'Log No RSS Sources', 0);
  connect(connections, 'RSS Sources Empty?', 'Query Topic Keywords', 1);
  connect(connections, 'Query Topic Keywords', 'Topic Keywords Empty?');
  connect(connections, 'Topic Keywords Empty?', 'Log Topic Config Empty', 0);
  connect(connections, 'Topic Keywords Empty?', 'Build RSS Source Items', 1);
  connect(connections, 'Build RSS Source Items', 'Read RSS Items');
  connect(connections, 'Read RSS Items', 'Normalize RSS Items');
  connect(connections, 'Normalize RSS Items', 'Fetch Article Body');
  connect(connections, 'Fetch Article Body', 'Extract Article Body');
  connect(connections, 'Extract Article Body', 'Filter Candidates');
  connect(connections, 'Filter Candidates', 'Select Latest Candidate');
  connect(connections, 'Select Latest Candidate', 'Check Notion Duplicate');
  connect(connections, 'Check Notion Duplicate', 'Skip Duplicate');
  connect(connections, 'Skip Duplicate', 'Restore Selected Candidate', 1);
  connect(connections, 'Restore Selected Candidate', 'Summarize With Ollama');
  connect(connections, 'Summarize With Ollama', 'Validate Summary');
  connect(connections, 'Validate Summary', 'Save Notion Summary');
  connect(connections, 'Save Notion Summary', 'Log Result');
  connect(connections, 'Log Result', 'Build Discord Success Message');
  connect(connections, 'Build Discord Success Message', 'Notify Discord Success');

  return {
    id: MAIN_WORKFLOW_ID,
    name: config.workflowName,
    nodes,
    connections,
    settings: {
      executionOrder: 'v1',
      timezone: config.schedule.timezone,
      saveExecutionProgress: true,
      saveManualExecutions: true,
      errorWorkflow: DISCORD_ERROR_WORKFLOW_ID,
    },
    staticData: null,
    tags: [],
    active: config.activateWorkflow,
  };
}

export function buildDiscordErrorWorkflow(config) {
  const nodes = [
    node({
      name: 'Workflow Error Trigger',
      type: 'n8n-nodes-base.errorTrigger',
      position: [0, 0],
    }),
    node({
      name: 'Build Discord Failure Message',
      type: 'n8n-nodes-base.code',
      position: [272, 0],
      parameters: {
        jsCode: `const execution = $json.execution || {};
const workflow = $json.workflow || {};
const error = execution.error || {};
const content = [
  '[B2-2] workflow failed',
  'Workflow: ' + (workflow.name || 'unknown') + ' (' + (workflow.id || 'unknown') + ')',
  'Node: ' + (execution.lastNodeExecuted || 'unknown'),
  'Mode: ' + (execution.mode || 'unknown'),
  'Execution: ' + (execution.url || execution.id || 'unknown'),
  'Error: ' + (error.message || 'Unknown error'),
].join('\\n');
return [{ json: { discordContent: content } }];`,
      },
    }),
    node({
      name: 'Notify Discord Failure',
      type: 'n8n-nodes-base.httpRequest',
      typeVersion: 4.4,
      position: [528, 0],
      parameters: discordWebhookParameters('={{ JSON.stringify({ content: $json.discordContent }) }}'),
      continueOnFail: true,
      retryOnFail: true,
      maxTries: config.maxRetryCount,
      waitBetweenTries: 1000,
    }),
    node({
      name: 'Log Discord Failure Notification',
      type: 'n8n-nodes-base.code',
      position: [784, 0],
      parameters: {
        jsCode: `if ($json.error) {
  console.log('DISCORD_NOTIFY_FAILED', $json.error);
}
return items;`,
      },
    }),
    stickyNote({
      name: 'Section 6 Exception Handling',
      position: [-64, -272],
      width: 1068,
      height: 560,
      content: '## [6] 예외 처리\n스킵/장애/알림 처리\n\n- 중복이면 Ollama 호출 없이 스킵\n- 실패는 Error Workflow로 전달\n- Discord 실패는 로그만 남김',
    }),
  ];

  const connections = {};
  connect(connections, 'Workflow Error Trigger', 'Build Discord Failure Message');
  connect(connections, 'Build Discord Failure Message', 'Notify Discord Failure');
  connect(connections, 'Notify Discord Failure', 'Log Discord Failure Notification');

  return {
    id: DISCORD_ERROR_WORKFLOW_ID,
    name: 'B2-2 Discord Error Notifier',
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

export function buildWorkflows(config) {
  return [buildWorkflow(config), buildDiscordErrorWorkflow(config)];
}
