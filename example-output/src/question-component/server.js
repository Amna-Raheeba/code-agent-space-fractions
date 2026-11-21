'use strict';

const { createQuestionApp } = require('./app');
const { config } = require('../shared/config');
const { registry } = require('../shared/metrics');
const { QuestionService } = require('./questionService');
const { InMemoryQuestionStore } = require('./inMemoryQuestionStore');

// Default wiring. Question data is owned by this component and persisted via a
// PostgreSQL-backed store matching sql/question_ddl.sql in production. The
// in-memory store keeps the service runnable without external dependencies.
const questionService = new QuestionService({ questionStore: new InMemoryQuestionStore() });
const app = createQuestionApp({ questionService });

app.get('/healthz', (req, res) =>
  res.json({ status: 'ok', service: config.service.question })
);

app.get('/metrics', async (req, res) => {
  res.set('Content-Type', registry.contentType);
  res.end(await registry.metrics());
});

app.listen(config.port.question, () => {
  // eslint-disable-next-line no-console
  console.log(`${config.service.question} listening on port ${config.port.question}`);
});
