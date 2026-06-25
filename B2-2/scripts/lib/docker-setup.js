import fs from 'node:fs';

export const NOTION_DATABASE_ENV_NAMES = [
  'NOTION_NEWS_DB_ID',
  'NOTION_RSS_CONFIG_DB_ID',
  'NOTION_TOPIC_CONFIG_DB_ID',
];

export function missingNotionDatabaseEnvNames(env) {
  return NOTION_DATABASE_ENV_NAMES.filter((name) => {
    return !env[name] || String(env[name]).trim() === '';
  });
}

export function mergeEnvAssignments(content, assignments) {
  const lines = content.split(/\r?\n/);
  const seen = new Set();
  const nextLines = lines.map((line) => {
    const match = /^([A-Z0-9_]+)=/.exec(line);
    if (!match) return line;

    const key = match[1];
    if (!(key in assignments)) return line;

    seen.add(key);
    return `${key}=${assignments[key]}`;
  });

  for (const [key, value] of Object.entries(assignments)) {
    if (!seen.has(key)) {
      nextLines.push(`${key}=${value}`);
    }
  }

  return `${nextLines.join('\n').replace(/\n+$/, '')}\n`;
}

export function buildDockerImportCommands(workflowPath, { ollamaModel = 'gemma3:1b' } = {}) {
  const commands = [
    ['docker', 'compose', 'up', '-d'],
    ['docker', 'compose', 'exec', '-T', 'ollama', 'ollama', 'pull', ollamaModel],
    ['docker', 'compose', 'cp', workflowPath, 'n8n:/tmp/b2-2-workflow.json'],
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
  ];

  if (fs.existsSync(workflowPath)) {
    try {
      const content = fs.readFileSync(workflowPath, 'utf8');
      const workflowData = JSON.parse(content);
      const workflows = Array.isArray(workflowData) ? workflowData : [workflowData];
      const activeWorkflowIds = workflows
        .filter((workflow) => workflow.active && workflow.id)
        .map((workflow) => workflow.id);

      for (const workflowId of activeWorkflowIds) {
        commands.push([
          'docker',
          'compose',
          'exec',
          '-T',
          'n8n',
          'n8n',
          'publish:workflow',
          `--id=${workflowId}`,
        ]);
      }

      if (activeWorkflowIds.length > 0) {
        commands.push(['docker', 'compose', 'restart', 'n8n']);
      }
    } catch (e) {
      // Ignore errors
    }
  }

  return commands;
}

export function buildProductionWebhookUrl(webhookPath, baseUrl = 'http://localhost:5678') {
  const normalizedBaseUrl = String(baseUrl).replace(/\/+$/, '');
  const normalizedPath = String(webhookPath || '').replace(/^\/+|\/+$/g, '');
  return `${normalizedBaseUrl}/webhook/${normalizedPath}`;
}

export function assignmentsFromCreatedDatabaseResult(result) {
  if (!result || !result.created) {
    return {};
  }

  return Object.fromEntries(
    Object.values(result.created)
      .filter((database) => database.envName && database.id)
      .map((database) => [database.envName, database.id]),
  );
}
