'use strict';

const express = require('express');
const { QuestionService } = require('./questionService');
const { InMemoryQuestionStore } = require('./inMemoryQuestionStore');

function createQuestionApp(options = {}) {
  const questionService =
    options.questionService ||
    new QuestionService({ questionStore: new InMemoryQuestionStore() });

  const app = express();
  app.use(express.json());

  app.get('/questions', (req, res, next) => {
    try {
      res.status(200).json(questionService.list());
    } catch (err) {
      next(err);
    }
  });

  app.get('/questions/:id', (req, res, next) => {
    try {
      res.status(200).json(questionService.get(parseInt(req.params.id, 10)));
    } catch (err) {
      next(err);
    }
  });

  app.post('/questions', (req, res, next) => {
    try {
      const created = questionService.create({
        prompt: req.body.prompt,
        options: req.body.options,
      });
      res.status(201).json(created);
    } catch (err) {
      next(err);
    }
  });

  app.put('/questions/:id', (req, res, next) => {
    try {
      const updated = questionService.update(parseInt(req.params.id, 10), {
        prompt: req.body.prompt,
        options: req.body.options,
      });
      res.status(200).json(updated);
    } catch (err) {
      next(err);
    }
  });

  app.delete('/questions/:id', (req, res, next) => {
    try {
      questionService.remove(parseInt(req.params.id, 10));
      res.status(204).end();
    } catch (err) {
      next(err);
    }
  });

  app.post('/questions/:id/check', (req, res, next) => {
    try {
      const result = questionService.checkAnswer(
        parseInt(req.params.id, 10),
        req.body.optionIndex
      );
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
    res.status(status).json({ error: err.message });
  });

  return app;
}

module.exports = { createQuestionApp };
