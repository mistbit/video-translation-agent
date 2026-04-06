import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

import { chromium } from 'playwright';

const baseUrl = process.env.BASE_URL ?? 'http://127.0.0.1:5173';
const videoPath = process.env.VIDEO_PATH;
const subtitlePath = process.env.SUBTITLE_PATH ?? '';
const artifactRoot = process.env.ARTIFACT_ROOT;
const screenshotDir = process.env.SCREENSHOT_DIR;
const resultPath = process.env.RESULT_PATH;

if (!videoPath || !artifactRoot || !screenshotDir || !resultPath) {
  throw new Error(
    'VIDEO_PATH, ARTIFACT_ROOT, SCREENSHOT_DIR, and RESULT_PATH must be set.'
  );
}

await mkdir(screenshotDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 1600 } });
const page = await context.newPage();

const consoleMessages = [];
const pageErrors = [];

page.on('console', (message) => {
  consoleMessages.push({
    type: message.type(),
    text: message.text(),
  });
});

page.on('pageerror', (error) => {
  pageErrors.push(String(error));
});

async function shot(name) {
  const target = path.join(screenshotDir, name);
  await page.screenshot({ path: target, fullPage: true });
  return target;
}

const screenshots = [];

try {
  await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 30000 });
  screenshots.push(await shot('01-home.png'));

  await page.getByTestId('input-video-path').fill(videoPath);
  await page.getByTestId('input-subtitle-path').fill(subtitlePath);
  await page.getByTestId('input-artifact-root').fill(artifactRoot);
  await page.getByTestId('select-source-language').selectOption('zh');
  await page.getByTestId('select-target-language').selectOption('en');
  await page.getByTestId('select-asr-model').selectOption('medium');
  await page.getByTestId('select-voice-profile').selectOption('en_female_neutral_01');
  await page.getByTestId('select-mix-mode').selectOption('duck');
  screenshots.push(await shot('02-form-filled.png'));

  await page.getByTestId('button-start-processing').click();

  const jobIdLocator = page.getByTestId('active-job-id');
  await jobIdLocator.waitFor({ state: 'visible', timeout: 60000 });
  await page.getByTestId('active-job-status-row').waitFor({ state: 'visible', timeout: 30000 });
  await page.getByTestId('artifact-list').waitFor({ state: 'visible', timeout: 30000 });
  await page.getByTestId('qa-summary').waitFor({ state: 'visible', timeout: 30000 });

  const jobId = (await jobIdLocator.textContent())?.trim() ?? '';
  const statusRow = (await page.getByTestId('active-job-status-row').textContent())?.trim() ?? '';
  const qaSummary = (await page.getByTestId('qa-summary').textContent())?.trim() ?? '';
  const artifacts = await page
    .locator('[data-testid="artifact-list"] > *')
    .allTextContents();

  if (!jobId) {
    throw new Error('Active job ID did not render.');
  }

  const historyLocator = page.getByTestId(`history-job-${jobId}`);
  await historyLocator.waitFor({ state: 'visible', timeout: 30000 });
  await historyLocator.click();

  screenshots.push(await shot('03-job-complete.png'));

  const result = {
    baseUrl,
    videoPath,
    subtitlePath,
    artifactRoot,
    jobId,
    statusRow,
    qaSummary,
    artifacts,
    screenshots,
    consoleMessages,
    pageErrors,
  };

  await writeFile(resultPath, `${JSON.stringify(result, null, 2)}\n`, 'utf-8');
  console.log(JSON.stringify(result, null, 2));
} finally {
  await context.close();
  await browser.close();
}
