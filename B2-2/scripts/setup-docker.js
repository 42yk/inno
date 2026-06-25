import { execFile } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { promisify } from 'node:util';
import { fileURLToPath } from 'node:url';

import {
  assignmentsFromCreatedDatabaseResult,
  buildDockerImportCommands,
  mergeEnvAssignments,
  missingNotionDatabaseEnvNames,
} from './lib/docker-setup.js';
import { readEnvFile } from './lib/env-file.js';
import { createNotionDatabase, createNotionPage, queryNotionDatabase } from './lib/notion-client.js';
import { buildDatabaseRequests, buildDefaultSeedRequests, envSnippet } from './lib/notion-databases.js';
import { loadConfigFromEnv, validateConfigForWorkflow } from './lib/config.js';
import { buildWorkflows } from './lib/workflow.js';

const execFileAsync = promisify(execFile);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(__dirname, '..');
const envPath = path.join(projectRoot, '.env');
const distDir = path.join(projectRoot, 'dist');
const workflowPath = path.join(distDir, 'n8n-news-summary.workflow.json');
const notionDatabaseResultPath = path.join(distDir, 'notion-databases.json');

function required(env, name) {
  const value = env[name];
  if (!value || String(value).trim() === '') {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return String(value).trim();
}

function loadProjectEnv() {
  return {
    ...readEnvFile(envPath),
    ...process.env,
  };
}

async function runCommand(command) {
  const [file, ...args] = command;
  console.log(`$ ${[file, ...args].join(' ')}`);
  const { stdout, stderr } = await execFileAsync(file, args, {
    cwd: projectRoot,
    maxBuffer: 1024 * 1024 * 20,
  });
  if (stdout.trim()) console.log(stdout.trim());
  if (stderr.trim()) console.error(stderr.trim());
}

async function createMissingDatabases(env) {
  let missing = missingNotionDatabaseEnvNames(env);
  if (missing.length === 0) {
    return env;
  }

  if (fs.existsSync(notionDatabaseResultPath)) {
    const previous = JSON.parse(fs.readFileSync(notionDatabaseResultPath, 'utf8'));
    const previousAssignments = assignmentsFromCreatedDatabaseResult(previous);
    const reusableAssignments = Object.fromEntries(
      Object.entries(previousAssignments).filter(([key]) => missing.includes(key)),
    );

    if (Object.keys(reusableAssignments).length > 0) {
      const existingContent = fs.existsSync(envPath) ? fs.readFileSync(envPath, 'utf8') : '';
      fs.writeFileSync(envPath, mergeEnvAssignments(existingContent, reusableAssignments));
      env = { ...env, ...reusableAssignments };
      missing = missingNotionDatabaseEnvNames(env);
      console.log('Reused Notion database IDs from dist/notion-databases.json and updated B2-2/.env.');
    }
  }

  if (missing.length === 0) {
    return env;
  }

  const token = required(env, 'NOTION_API_TOKEN');
  const parentPageId = required(env, 'NOTION_PARENT_PAGE_ID');
  const requests = buildDatabaseRequests(parentPageId).filter((request) => {
    return missing.includes(request.envName);
  });
  const created = {};

  for (const request of requests) {
    console.log(`Creating Notion database: ${request.title}`);
    const database = await createNotionDatabase(token, request.body);
    created[request.key] = {
      title: request.title,
      envName: request.envName,
      id: database.id,
      url: database.url,
    };
  }

  const assignments = Object.fromEntries(
    Object.values(created).map((database) => [database.envName, database.id]),
  );
  const existingContent = fs.existsSync(envPath) ? fs.readFileSync(envPath, 'utf8') : '';
  fs.writeFileSync(envPath, mergeEnvAssignments(existingContent, assignments));

  fs.mkdirSync(distDir, { recursive: true });
  fs.writeFileSync(notionDatabaseResultPath, `${JSON.stringify({ created }, null, 2)}\n`);

  console.log('\nCreated Notion databases and updated B2-2/.env:\n');
  console.log(envSnippet(created));

  return {
    ...env,
    ...assignments,
  };
}

function writeWorkflow(env) {
  const config = loadConfigFromEnv(env);
  validateConfigForWorkflow(config);
  const workflow = buildWorkflows(config);
  fs.mkdirSync(distDir, { recursive: true });
  fs.writeFileSync(workflowPath, `${JSON.stringify(workflow, null, 2)}\n`);
  console.log(`Workflow JSON written: ${workflowPath}`);
}

async function seedDefaultConfigRows(env) {
  const config = loadConfigFromEnv(env);
  validateConfigForWorkflow(config);

  for (const request of buildDefaultSeedRequests(config)) {
    const existing = await queryNotionDatabase(config.notionApiToken, request.databaseId, request.queryBody);
    if ((existing.results || []).length > 0) {
      console.log(`Seed already exists: ${request.label}`);
      continue;
    }

    console.log(`Creating seed: ${request.label}`);
    await createNotionPage(config.notionApiToken, request.createBody);
  }
}

async function main() {
  let env = loadProjectEnv();
  env = await createMissingDatabases(env);
  await seedDefaultConfigRows(env);
  writeWorkflow(env);

  const config = loadConfigFromEnv(env);
  const commands = buildDockerImportCommands('dist/n8n-news-summary.workflow.json', {
    ollamaModel: config.ollamaModel,
  });
  for (const command of commands) {
    await runCommand(command);
  }

  console.log('\nDocker n8n setup complete. Open http://localhost:5678 and check the imported workflow.');
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
