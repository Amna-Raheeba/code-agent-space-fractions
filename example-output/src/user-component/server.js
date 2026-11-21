'use strict';

const { createUserApp } = require('./app');
const { config } = require('../shared/config');
const { registry } = require('../shared/metrics');
const { AuthService } = require('./auth');
const { InMemoryUserStore } = require('./inMemoryUserStore');

const userStore = new InMemoryUserStore();
const authService = new AuthService({ userStore });
const app = createUserApp({ userStore, authService });

app.get('/healthz', (req, res) =>
  res.json({ status: 'ok', service: config.service.user })
);

app.get('/metrics', async (req, res) => {
  res.set('Content-Type', registry.contentType);
  res.end(await registry.metrics());
});

app.listen(config.port.user, () => {
  // eslint-disable-next-line no-console
  console.log(`${config.service.user} listening on port ${config.port.user}`);
});
