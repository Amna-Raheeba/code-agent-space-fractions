'use strict';

const { InMemoryGameStore } = require('./inMemoryGameStore');

const INT32_MIN = -2147483648;
const INT32_MAX = 2147483647;

function assertInt32(value) {
  if (!Number.isInteger(value) || value < INT32_MIN || value > INT32_MAX) {
    const err = new Error('gameId must be an int32');
    err.code = 'EINVAL';
    throw err;
  }
}

/**
 * GameService implements the game logic of the GameComponent and the
 * GameService.Play RPC defined in proto/internal.proto.
 */
class GameService {
  constructor({ gameStore } = {}) {
    this.gameStore = gameStore || new InMemoryGameStore();
  }

  // Play: gameId is optional for the HTTP flow (creates a new session) and is
  // echoed back as an int32, mirroring the GET /play endpoint and the RPC.
  play(gameId) {
    if (gameId === undefined || gameId === null) {
      const game = this.gameStore.create();
      return { gameId: game.id };
    }
    assertInt32(gameId);
    let game = this.gameStore.get(gameId);
    if (!game) {
      game = this.gameStore.create(gameId);
    }
    return { gameId: game.id };
  }

  viewScore(gameId) {
    assertInt32(gameId);
    const game = this._require(gameId);
    return game.viewScore();
  }

  pause(gameId) {
    assertInt32(gameId);
    const game = this._require(gameId);
    const state = game.pause();
    this.gameStore.save(game);
    return { gameId: game.id, state };
  }

  resume(gameId) {
    assertInt32(gameId);
    const game = this._require(gameId);
    const state = game.resume();
    this.gameStore.save(game);
    return { gameId: game.id, state };
  }

  gameOver(gameId) {
    assertInt32(gameId);
    const game = this._require(gameId);
    const state = game.gameOver();
    this.gameStore.save(game);
    return { gameId: game.id, state };
  }

  _require(gameId) {
    const game = this.gameStore.get(gameId);
    if (!game) {
      const err = new Error(`game ${gameId} not found`);
      err.code = 'ENOTFOUND';
      throw err;
    }
    return game;
  }
}

module.exports = { GameService, assertInt32, INT32_MIN, INT32_MAX };
