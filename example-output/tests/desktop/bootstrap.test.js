'use strict';

const { ensureSeeded } = require('../../desktop/lib/bootstrap');
const { ApiClient } = require('../../desktop/lib/apiClient');
const { seedQuestions } = require('../../desktop/lib/seedBank');
const { createQuestionApp } = require('../../src/question-component/app');

function listen(app) {
  return new Promise((resolve) => {
    const server = app.listen(0, () => resolve(server));
  });
}

describe('ensureSeeded', () => {
  let server;
  let client;

  beforeAll(async () => {
    server = await listen(createQuestionApp());
    client = new ApiClient({
      gameUrl: 'http://127.0.0.1:1',
      questionUrl: `http://127.0.0.1:${server.address().port}`,
      userUrl: 'http://127.0.0.1:1',
    });
  });

  afterAll(async () => {
    await new Promise((r) => server.close(r));
  });

  test('seeds the bank on an empty service and builds a correctIndex map', async () => {
    const { correctIndexById, questions } = await ensureSeeded(client, seedQuestions);
    expect(questions.length).toBe(seedQuestions.length);
    expect(Object.keys(correctIndexById).length).toBe(seedQuestions.length);
    expect(correctIndexById[questions[0].id]).toBe(seedQuestions[0].correctIndex);
  });

  test('does not re-seed when questions already exist', async () => {
    await ensureSeeded(client, seedQuestions);
    const { questions } = await ensureSeeded(client, seedQuestions);
    expect(questions.length).toBe(seedQuestions.length);
  });
});
