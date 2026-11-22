'use strict';

const path = require('path');
const { spawn } = require('child_process');
const { app, BrowserWindow, ipcMain } = require('electron');

const { ApiClient } = require('./lib/apiClient');
const { waitForService, ensureSeeded } = require('./lib/bootstrap');
const { evaluate } = require('./lib/questionMatcher');
const { seedQuestions } = require('./lib/seedBank');

const ROOT = path.join(__dirname, '..');

const PORTS = {
  game: process.env.GAME_PORT || '3000',
  question: process.env.QUESTION_PORT || '3001',
  user: process.env.USER_PORT || '3002',
};

const SERVICES = [
  { script: 'src/game-component/server.js', port: PORTS.game },
  { script: 'src/question-component/server.js', port: PORTS.question },
  { script: 'src/user-component/server.js', port: PORTS.user },
];

const client = new ApiClient({
  gameUrl: `http://127.0.0.1:${PORTS.game}`,
  questionUrl: `http://127.0.0.1:${PORTS.question}`,
  userUrl: `http://127.0.0.1:${PORTS.user}`,
});

let children = [];
let correctIndexById = {};
let mainWindow = null;
let started = false;

function startServices() {
  SERVICES.forEach((svc) => {
    const child = spawn(process.execPath, [path.join(ROOT, svc.script)], {
      cwd: ROOT,
      env: {
        ...process.env,
        GAME_PORT: PORTS.game,
        QUESTION_PORT: PORTS.question,
        USER_PORT: PORTS.user,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    child.stdout.on('data', (d) => process.stdout.write(`[${svc.script}] ${d}`));
    child.stderr.on('data', (d) => process.stderr.write(`[${svc.script}] ${d}`));
    children.push(child);
  });
}

function stopServices() {
  children.forEach((child) => {
    try {
      child.kill('SIGTERM');
    } catch {
      /* already exited */
    }
  });
  children = [];
}

async function waitForAllServices() {
  await Promise.all(
    SERVICES.map((svc) =>
      waitForService(`http://127.0.0.1:${svc.port}/healthz`, { timeoutMs: 30000 })
    )
  );
}

async function bootstrap() {
  if (started) return;
  started = true;
  startServices();
  await waitForAllServices();
  const seeded = await ensureSeeded(client, seedQuestions);
  correctIndexById = seeded.correctIndexById;
}

function registerIpc() {
  ipcMain.handle('game:start', async () => {
    const { gameId } = await client.play();
    const questions = await client.listQuestions();
    return { gameId, questions };
  });

  ipcMain.handle('question:answer', async (_event, { questionId, optionIndex }) => {
    // Ask the QuestionService to validate the click, then resolve correctness
    // against the designed seed bank.
    const check = await client.checkAnswer(questionId, optionIndex);
    const answer = evaluate(correctIndexById, questionId, optionIndex);
    return { ...check, ...answer };
  });

  ipcMain.handle('game:finish', async (_event, { gameId, score }) => {
    await client.gameOver(gameId);
    const server = await client.getScore(gameId);
    return { score, serverScore: server.score, serverGameId: server.gameId };
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 960,
    height: 680,
    title: 'Space Fractions',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.loadFile(path.join(__dirname, 'index.html'));
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  registerIpc();
  try {
    await bootstrap();
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error('Failed to start Space Fractions services:', err);
    app.quit();
    return;
  }
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  stopServices();
});
