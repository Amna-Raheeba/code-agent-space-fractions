'use strict';

const { ApiClient } = require('../../desktop/lib/apiClient');
const { createGameApp } = require('../../src/game-component/app');
const { createQuestionApp } = require('../../src/question-component/app');

function listen(app) {
  return new Promise((resolve) => {
    const server = app.listen(0, () => resolve(server));
  });
}

describe('ApiClient (talks to the running services over HTTP)', () => {
  let gameServer;
  let questionServer;
  let client;

  beforeAll(async () => {
    gameServer = await listen(createGameApp());
    questionServer = await listen(createQuestionApp());
    client = new ApiClient({
      gameUrl: `http://127.0.0.1:${gameServer.address().port}`,
      questionUrl: `http://127.0.0.1:${questionServer.address().port}`,
      userUrl: `http://127.0.0.1:1`,
    });
  });

  afterAll(async () => {
    await new Promise((r) => gameServer.close(r));
    await new Promise((r) => questionServer.close(r));
  });

  test('play() returns an integer gameId', async () => {
    const { gameId } = await client.play();
    expect(Number.isInteger(gameId)).toBe(true);
  });

  test('create and list questions', async () => {
    const created = await client.createQuestion({
      prompt: '1/2 + 1/4 = ?',
      options: ['3/4', '2/6', '1/8'],
    });
    expect(created.id).toBeDefined();
    const list = await client.listQuestions();
    expect(list.some((q) => q.prompt === '1/2 + 1/4 = ?')).toBe(true);
  });

  test('checkAnswer returns validity for a seeded question', async () => {
    const created = await client.createQuestion({
      prompt: '2/5 + 1/5 = ?',
      options: ['3/10', '3/5'],
    });
    const ok = await client.checkAnswer(created.id, 0);
    expect(ok).toEqual({ valid: true, selected: '3/10' });
    const bad = await client.checkAnswer(created.id, 99);
    expect(bad).toEqual({ valid: false, selected: null });
  });

  test('getScore and gameOver round-trip', async () => {
    const { gameId } = await client.play();
    const over = await client.gameOver(gameId);
    expect(over.state).toBe('GameOver');
    const score = await client.getScore(gameId);
    expect(score).toHaveProperty('score', 0);
  });

  test('non-2xx responses reject with a useful error', async () => {
    await expect(client.getQuestion(999999)).rejects.toThrow();
  });
});
