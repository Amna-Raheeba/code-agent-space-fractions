'use strict';

const { buildCorrectIndex, evaluate } = require('../../desktop/lib/questionMatcher');
const { seedQuestions } = require('../../desktop/lib/seedBank');

describe('buildCorrectIndex', () => {
  test('maps server question ids to seed correctIndex by prompt', () => {
    const questions = [
      { id: 1, prompt: '1/2 + 1/4 = ?', options: ['3/4', '2/6', '1/6', '1/8'] },
      { id: 7, prompt: 'Which fraction is largest?', options: ['1/4', '1/3', '1/2', '1/6'] },
    ];
    const map = buildCorrectIndex(questions, seedQuestions);
    expect(map).toEqual({ 1: 0, 7: 2 });
  });

  test('omits questions whose prompt is not in the seed bank', () => {
    const questions = [{ id: 99, prompt: 'unknown question?', options: ['a', 'b'] }];
    expect(buildCorrectIndex(questions, seedQuestions)).toEqual({});
  });
});

describe('evaluate', () => {
  const map = { 1: 0, 2: 3 };

  test('reports correct when the option index matches', () => {
    expect(evaluate(map, 1, 0)).toEqual({ found: true, correct: true, correctIndex: 0 });
    expect(evaluate(map, 2, 3)).toEqual({ found: true, correct: true, correctIndex: 3 });
  });

  test('reports incorrect when the option index differs', () => {
    expect(evaluate(map, 1, 2)).toEqual({ found: true, correct: false, correctIndex: 0 });
  });

  test('reports not found for an unknown question id', () => {
    expect(evaluate(map, 404, 0)).toEqual({ found: false, correct: false, correctIndex: null });
  });

  test('coerces numeric-string option indices', () => {
    expect(evaluate(map, 1, '0')).toEqual({ found: true, correct: true, correctIndex: 0 });
  });
});
