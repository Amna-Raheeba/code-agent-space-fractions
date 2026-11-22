'use strict';

/**
 * Startup helpers used by the Electron main process (and unit-tested directly):
 * waiting for a service to become healthy and seeding the question bank.
 */

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForService(healthUrl, { timeoutMs = 30000, intervalMs = 200 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let lastErr = null;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(healthUrl);
      if (res.ok) return;
    } catch (err) {
      lastErr = err;
    }
    await sleep(intervalMs);
  }
  throw new Error(
    `service at ${healthUrl} did not become healthy within ${timeoutMs}ms: ${lastErr || 'no response'}`
  );
}

/**
 * Ensure the question service has questions, then build a correctIndex map by
 * matching prompts against the seed bank.
 *
 * Returns { correctIndexById, questions }.
 */
async function ensureSeeded(client, seed) {
  let questions = await client.listQuestions();
  if (!Array.isArray(questions) || questions.length === 0) {
    for (const s of seed) {
      await client.createQuestion({ prompt: s.prompt, options: s.options });
    }
    questions = await client.listQuestions();
  }
  const { buildCorrectIndex } = require('./questionMatcher');
  const correctIndexById = buildCorrectIndex(questions, seed);
  return { correctIndexById, questions };
}

module.exports = { sleep, waitForService, ensureSeeded };
