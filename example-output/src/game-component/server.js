'use strict';

const { createGameApp } = require('./app');
const { config } = require('../shared/config');
const { registry, httpRequestsTotal } = require('../shared/metrics');
const { GameService } = require('./gameService');
const { InMemoryGameStore } = require('./inMemoryGameStore');

// Default wiring. Game state can be swapped for a PostgreSQL-backed store
// matching sql/games_ddl.sql, or cached via src/shared/cache.js (Redis 6).
const gameService = new GameService({ gameStore: new InMemoryGameStore() });
const app = createGameApp({ gameService });

app.get('/healthz', (req, res) => res.json({ status: 'ok', service: config.service.game }));

app.get('/metrics', async (req, res) => {
  res.set('Content-Type', registry.contentType);
  res.end(await registry.metrics());
});

// Simple request counting using Prometheus (observability per the stack).
app.use((req, res, next) => {
  res.on('finish', () => {
    httpRequestsTotal.inc({ method: req.method, route: req.path, status: res.statusCode });
  });
  next();
});

app.listen(config.port.game, () => {
  // eslint-disable-next-line no-console
  console.log(`${config.service.game} listening on port ${config.port.game}`);
});
