import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";


const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const projectDirectory = dirname(scriptDirectory);
const sourceDirectory = join(projectDirectory, "src");
const outputDirectory = join(projectDirectory, "dist");
const apiBaseUrl = process.env.API_BASE_URL?.trim();

if (!apiBaseUrl) {
  throw new Error("API_BASE_URL is required");
}

await rm(outputDirectory, { recursive: true, force: true });
await mkdir(outputDirectory, { recursive: true });
await cp(sourceDirectory, outputDirectory, { recursive: true });
await writeFile(
  join(outputDirectory, "config.js"),
  `window.APP_CONFIG = ${JSON.stringify({ API_BASE_URL: apiBaseUrl })};\n`,
  "utf8",
);
