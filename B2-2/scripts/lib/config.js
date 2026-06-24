export const DEFAULT_RSS_SOURCES = [
  {
    name: 'Newswire 전체 뉴스',
    url: 'https://api.newswire.co.kr/rss/all',
  },
];

export const DEFAULT_TOPIC_KEYWORDS = [
  'AI',
  'artificial intelligence',
  '인공지능',
  '생성형 AI',
  'generative AI',
  'LLM',
  'large language model',
  'agent',
  'AI agent',
  'automation',
  'workflow automation',
  'Ollama',
  'n8n',
];

function optional(env, name, fallback) {
  const value = env[name];
  if (value === undefined || value === null || String(value).trim() === '') {
    return fallback;
  }
  return String(value).trim();
}

function optionalNumber(env, name, fallback) {
  const value = optional(env, name, String(fallback));
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) {
    throw new Error(`Invalid numeric environment variable: ${name}`);
  }
  return number;
}

export function loadConfigFromEnv(env = process.env) {
  const notionDatabases = {
    news: optional(env, 'NOTION_NEWS_DB_ID', ''),
    rssConfig: optional(env, 'NOTION_RSS_CONFIG_DB_ID', ''),
    topicConfig: optional(env, 'NOTION_TOPIC_CONFIG_DB_ID', ''),
  };

  return {
    workflowName: optional(env, 'N8N_WORKFLOW_NAME', 'B2-2 RSS AI News Summary'),
    activateWorkflow: optional(env, 'N8N_ACTIVATE_WORKFLOW', 'false') === 'true',
    schedule: {
      cronExpression: optional(env, 'NEWS_CRON_EXPRESSION', '0 9 * * *'),
      timezone: optional(env, 'NEWS_TIMEZONE', 'Asia/Seoul'),
    },
    ollamaBaseUrl: optional(env, 'OLLAMA_BASE_URL', 'http://localhost:11434'),
    ollamaModel: optional(env, 'OLLAMA_MODEL', 'qwen3:6b'),
    ollamaTimeoutMs: optionalNumber(env, 'OLLAMA_TIMEOUT_MS', 60000),
    maxRetryCount: optionalNumber(env, 'MAX_RETRY_COUNT', 2),
    rssFetchTimeoutMs: optionalNumber(env, 'RSS_FETCH_TIMEOUT_MS', 30000),
    notionDatabases,
    notionApiToken: optional(env, 'NOTION_API_TOKEN', ''),
    discordWebhookUrl: optional(env, 'DISCORD_WEBHOOK_URL', ''),
    defaultRssSources: DEFAULT_RSS_SOURCES,
    defaultTopicKeywords: DEFAULT_TOPIC_KEYWORDS,
  };
}

export function validateConfigForWorkflow(config) {
  const requiredFields = [
    ['NOTION_NEWS_DB_ID', config.notionDatabases.news],
    ['NOTION_RSS_CONFIG_DB_ID', config.notionDatabases.rssConfig],
    ['NOTION_TOPIC_CONFIG_DB_ID', config.notionDatabases.topicConfig],
    ['NOTION_API_TOKEN', config.notionApiToken],
  ];

  const missing = requiredFields.filter(([, value]) => !value).map(([name]) => name);
  if (missing.length > 0) {
    throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
  }
}
