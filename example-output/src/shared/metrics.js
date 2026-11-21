'use strict';

const prom = require('prom-client');

const registry = new prom.Registry();
prom.collectDefaultMetrics({ register: registry });

const httpRequestsTotal = new prom.Counter({
  name: 'http_requests_total',
  help: 'Total number of HTTP requests served',
  labelNames: ['method', 'route', 'status'],
  registers: [registry],
});

module.exports = { registry, httpRequestsTotal, client: prom };
