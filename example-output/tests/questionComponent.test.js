'use strict';

const request = require('supertest');
const { createQuestionApp } = require('../src/question-component/app');
const { QuestionService } = require('../src/question-component/questionService');
const { InMemoryQuestionStore } = require('../src/question-component/inMemoryQuestionStore');

describe('QuestionService', () => {
  test('create persists a question', () => {
    const service = new QuestionService({ questionStore: new InMemoryQuestionStore() });
    const q = service.create({ prompt: '1/2 + 1/4 = ?', options: ['3/4', '2/6', '1/8'] });
    expect(q.id).toBeDefined();
    expect(service.get(q.id).prompt).toBe('1/2 + 1/4 = ?');
  });

  test('create validates prompt and options', () => {
    const service = new QuestionService({ questionStore: new InMemoryQuestionStore() });
    expect(() => service.create({ prompt: '', options: ['a'] })).toThrow(/prompt/);
    expect(() => service.create({ prompt: 'x', options: [] })).toThrow(/options/);
  });

  test('getPrompt and getOptions', () => {
    const service = new QuestionService({ questionStore: new InMemoryQuestionStore() });
    const q = service.create({ prompt: 'a', options: ['b', 'c'] });
    expect(service.getPrompt(q.id)).toBe('a');
    expect(service.getOptions(q.id)).toEqual(['b', 'c']);
  });

  test('checkAnswer validates option index bounds', () => {
    const service = new QuestionService({ questionStore: new InMemoryQuestionStore() });
    const q = service.create({ prompt: 'a', options: ['b', 'c'] });
    expect(service.checkAnswer(q.id, 1)).toEqual({ valid: true, selected: 'c' });
    expect(service.checkAnswer(q.id, 5).valid).toBe(false);
  });
});

describe('question HTTP endpoints', () => {
  test('create and list questions', async () => {
    const app = createQuestionApp();
    const created = await request(app)
      .post('/questions')
      .send({ prompt: '1/3 + 1/3 = ?', options: ['2/3', '1/3', '0'] });
    expect(created.status).toBe(201);

    const list = await request(app).get('/questions');
    expect(list.status).toBe(200);
    expect(list.body.length).toBe(1);
    expect(list.body[0].prompt).toBe('1/3 + 1/3 = ?');
  });

  test('update a question', async () => {
    const app = createQuestionApp();
    const created = await request(app)
      .post('/questions')
      .send({ prompt: 'a', options: ['b'] });
    const id = created.body.id;
    const updated = await request(app)
      .put(`/questions/${id}`)
      .send({ prompt: 'c', options: ['d', 'e'] });
    expect(updated.status).toBe(200);
    expect(updated.body.prompt).toBe('c');
    expect(updated.body.options).toEqual(['d', 'e']);
  });

  test('delete a question returns 204 then 404', async () => {
    const app = createQuestionApp();
    const created = await request(app)
      .post('/questions')
      .send({ prompt: 'a', options: ['b'] });
    const del = await request(app).delete(`/questions/${created.body.id}`);
    expect(del.status).toBe(204);
    const get = await request(app).get(`/questions/${created.body.id}`);
    expect(get.status).toBe(404);
  });

  test('get unknown question returns 404', async () => {
    const app = createQuestionApp();
    const res = await request(app).get('/questions/999999');
    expect(res.status).toBe(404);
  });
});
