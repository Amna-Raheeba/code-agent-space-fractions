'use strict';

const express = require('express');
const { GameService } = require('./gameService');
const { InMemoryGameStore } = require('./inMemoryGameStore');

function createGameApp(options = {}) {
  const gameService =
    options.gameService || new GameService({ gameStore: new InMemoryGameStore() });

  const app = express();
  app.use(express.json());

  app.get('/play', (req, res, next) => {
    try {
      const { gameId } = gameService.play();
      res.status(200).json({ gameId });
    } catch (err) {
      next(err);
    }
  });

  app.get('/game/:gameId/score', (req, res, next) => {
    try {
      const gameId = parseInt(req.params.gameId, 10);
      const score = gameService.viewScore(gameId);
      res.status(200).json({ gameId, score });
    } catch (err) {
      next(err);
    }
  });

  app.post('/game/:gameId/pause', (req, res, next) => {
    try {
      const gameId = parseInt(req.params.gameId, 10);
      const result = gameService.pause(gameId);
      res.status(200).json(result);
    } catch (err) {
      next(err);
    }
  });

  app.post('/game/:gameId/resume', (req, res, next) => {
    try {
      const gameId = parseInt(req.params.gameId, 10);
      const result = gameService.resume(gameId);
      res.status(200).json(result);
    } catch (err) {
      next(err);
    }
  });

  app.post('/game/:gameId/gameover', (req, res, next) => {
    try {
      const gameId = parseInt(req.params.gameId, 10);
      const result = gameService.gameOver(gameId);
      res.status(200).json(result);
    } catch (err) {
      next(err);
    }
  });

  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    let status = 500;
    if (err.code === 'ENOTFOUND') status = 404;
    else if (err.code === 'EINVAL') status = 400;
    else if (err.code === 'ESTATE') status = 409;
    res.status(status).json({ error: err.message });
  });

  return app;
}

module.exports = { createGameApp };
