'use strict';

const { GameState } = require('./gameState');

// Minimal in-memory store used by default and in tests. Production wiring can
// substitute a PostgreSQL-backed store matching sql/games_ddl.sql.
class InMemoryGameStore {
  constructor() {
    this.games = new Map();
    this.nextId = 1;
  }

  create(id) {
    let realId = id;
    if (realId === undefined || realId === null) {
      do {
        realId = this.nextId++;
      } while (this.games.has(realId));
    }
    const game = new GameState(realId);
    this.games.set(realId, game);
    return game;
  }

  get(id) {
    return this.games.get(id);
  }

  save(game) {
    this.games.set(game.id, game);
    return game;
  }
}

module.exports = { InMemoryGameStore };
