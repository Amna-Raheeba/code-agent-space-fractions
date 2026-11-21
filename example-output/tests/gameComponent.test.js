'use strict';

const request = require('supertest');
const { createGameApp } = require('../src/game-component/app');
const { GameService } = require('../src/game-component/gameService');
const { GameState, STATES } = require('../src/game-component/gameState');
const { InMemoryGameStore } = require('../src/game-component/inMemoryGameStore');

describe('GameState state machine', () => {
  test('starts in Playing', () => {
    const g = new GameState(1);
    expect(g.state).toBe(STATES.PLAYING);
  });

  test('pause/resume cycle', () => {
    const g = new GameState(1);
    expect(g.pause()).toBe(STATES.PAUSED);
    expect(g.resume()).toBe(STATES.PLAYING);
  });

  test('gameOver from Playing', () => {
    const g = new GameState(1);
    expect(g.gameOver()).toBe(STATES.GAME_OVER);
  });

  test('cannot pause from GameOver', () => {
    const g = new GameState(1);
    g.gameOver();
    expect(() => g.pause()).toThrow(/Cannot pause/);
  });

  test('cannot resume while Playing', () => {
    const g = new GameState(1);
    expect(() => g.resume()).toThrow(/Cannot resume/);
  });
});

describe('GameService', () => {
  test('play without id creates a session and returns int32 gameId', () => {
    const service = new GameService({ gameStore: new InMemoryGameStore() });
    const result = service.play();
    expect(Number.isInteger(result.gameId)).toBe(true);
    expect(result.gameId).toBeGreaterThanOrEqual(1);
  });

  test('play with an existing id returns the same id', () => {
    const service = new GameService({ gameStore: new InMemoryGameStore() });
    const { gameId } = service.play();
    expect(service.play(gameId)).toEqual({ gameId });
  });

  test('play rejects a non-int32 gameId', () => {
    const service = new GameService({ gameStore: new InMemoryGameStore() });
    expect(() => service.play(2147483648)).toThrow(/int32/);
    expect(() => service.play(1.5)).toThrow(/int32/);
  });

  test('viewScore throws ENOTFOUND for unknown id', () => {
    const service = new GameService({ gameStore: new InMemoryGameStore() });
    try {
      service.viewScore(999999);
      throw new Error('expected ENOTFOUND');
    } catch (err) {
      expect(err.code).toBe('ENOTFOUND');
    }
  });
});

describe('GET /play', () => {
  test('returns 200 with a gameId', async () => {
    const app = createGameApp();
    const res = await request(app).get('/play');
    expect(res.status).toBe(200);
    expect(res.body).toHaveProperty('gameId');
    expect(Number.isInteger(res.body.gameId)).toBe(true);
  });
});

describe('score and state endpoints', () => {
  test('score returns 404 for unknown game', async () => {
    const app = createGameApp();
    const res = await request(app).get('/game/999999/score');
    expect(res.status).toBe(404);
    expect(res.body).toHaveProperty('error');
  });

  test('score returns 400 for non-int32 id', async () => {
    const app = createGameApp();
    const res = await request(app).get('/game/2147483648/score');
    expect(res.status).toBe(400);
  });

  test('pause then resume transitions state', async () => {
    const app = createGameApp();
    const { body } = await request(app).get('/play');
    const gameId = body.gameId;

    const pauseRes = await request(app).post(`/game/${gameId}/pause`);
    expect(pauseRes.status).toBe(200);
    expect(pauseRes.body.state).toBe(STATES.PAUSED);

    const resumeRes = await request(app).post(`/game/${gameId}/resume`);
    expect(resumeRes.status).toBe(200);
    expect(resumeRes.body.state).toBe(STATES.PLAYING);
  });

  test('pausing again returns 409 conflict', async () => {
    const app = createGameApp();
    const { body } = await request(app).get('/play');
    await request(app).post(`/game/${body.gameId}/pause`);
    const res = await request(app).post(`/game/${body.gameId}/pause`);
    expect(res.status).toBe(409);
  });
});
