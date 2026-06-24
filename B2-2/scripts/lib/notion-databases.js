function text(content) {
  return [
    {
      type: 'text',
      text: { content },
    },
  ];
}

function selectOptions(names) {
  const colors = ['green', 'blue', 'yellow', 'red', 'purple', 'gray'];
  return names.map((name, index) => ({
    name,
    color: colors[index % colors.length],
  }));
}

export function buildDatabaseRequests(parentPageId) {
  return [
    {
      key: 'news',
      envName: 'NOTION_NEWS_DB_ID',
      title: 'B2-2 News Summaries',
      body: {
        parent: {
          type: 'page_id',
          page_id: parentPageId,
        },
        title: text('B2-2 News Summaries'),
        properties: {
          Title: { title: {} },
          Summary: { rich_text: {} },
          'Original URL': { url: {} },
          'Published At': { date: {} },
          'Dedupe Key': { rich_text: {} },
          Source: { rich_text: {} },
          'Matched Keywords': { multi_select: {} },
          Status: {
            select: {
              options: selectOptions(['Saved', 'Skipped', 'Failed']),
            },
          },
          'AI Model': { rich_text: {} },
          'Saved At': { date: {} },
        },
      },
    },
    {
      key: 'rssConfig',
      envName: 'NOTION_RSS_CONFIG_DB_ID',
      title: 'B2-2 RSS Sources',
      body: {
        parent: {
          type: 'page_id',
          page_id: parentPageId,
        },
        title: text('B2-2 RSS Sources'),
        properties: {
          Name: { title: {} },
          'Feed URL': { url: {} },
          Enabled: { checkbox: {} },
          Priority: { number: { format: 'number' } },
          Note: { rich_text: {} },
        },
      },
    },
    {
      key: 'topicConfig',
      envName: 'NOTION_TOPIC_CONFIG_DB_ID',
      title: 'B2-2 Topic Keywords',
      body: {
        parent: {
          type: 'page_id',
          page_id: parentPageId,
        },
        title: text('B2-2 Topic Keywords'),
        properties: {
          Keyword: { title: {} },
          Enabled: { checkbox: {} },
          'Match Target': {
            select: {
              options: selectOptions(['All', 'Title', 'Content', 'Category']),
            },
          },
          Reason: { rich_text: {} },
          Weight: { number: { format: 'number' } },
        },
      },
    },
  ];
}

export function envSnippet(createdDatabases) {
  return Object.entries(createdDatabases)
    .map(([, database]) => `${database.envName}=${database.id}`)
    .join('\n');
}

export function buildDefaultSeedRequests(config) {
  return [
    {
      key: 'defaultRssSource',
      label: 'Default RSS source',
      databaseId: config.notionDatabases.rssConfig,
      queryBody: {
        filter: {
          property: 'Feed URL',
          url: { equals: 'https://api.newswire.co.kr/rss/all' },
        },
      },
      createBody: {
        parent: { database_id: config.notionDatabases.rssConfig },
        properties: {
          Name: { title: text('Newswire 전체 뉴스') },
          'Feed URL': { url: 'https://api.newswire.co.kr/rss/all' },
          Enabled: { checkbox: true },
          Priority: { number: 1 },
          Note: { rich_text: text('Initial RSS seed created by setup:docker.') },
        },
      },
    },
    {
      key: 'defaultTopicKeyword',
      label: 'Default topic keyword',
      databaseId: config.notionDatabases.topicConfig,
      queryBody: {
        filter: {
          property: 'Keyword',
          title: { equals: 'AI' },
        },
      },
      createBody: {
        parent: { database_id: config.notionDatabases.topicConfig },
        properties: {
          Keyword: { title: text('AI') },
          Enabled: { checkbox: true },
          'Match Target': { select: { name: 'All' } },
          Reason: { rich_text: text('Initial topic seed. Add more keywords in Notion Topic Keywords DB.') },
          Weight: { number: 1 },
        },
      },
    },
  ];
}
