async function notionRequest(token, path, { method = 'GET', body } = {}) {
  const response = await fetch(`https://api.notion.com${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      'Notion-Version': '2022-06-28',
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : {};

  if (!response.ok) {
    throw new Error(`Notion API ${response.status}: ${JSON.stringify(data)}`);
  }

  return data;
}

export async function createNotionDatabase(token, body) {
  return notionRequest(token, '/v1/databases', {
    method: 'POST',
    body,
  });
}

export async function queryNotionDatabase(token, databaseId, body) {
  return notionRequest(token, `/v1/databases/${databaseId}/query`, {
    method: 'POST',
    body,
  });
}

export async function createNotionPage(token, body) {
  return notionRequest(token, '/v1/pages', {
    method: 'POST',
    body,
  });
}
