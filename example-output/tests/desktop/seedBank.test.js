'use strict';

const { seedQuestions, validateSeed } = require('../../desktop/lib/seedBank');

describe('seed bank (designed; the documents define no questions)', () => {
  test('contains at least 10 fraction questions', () => {
    expect(seedQuestions.length).toBeGreaterThanOrEqual(10);
  });

  test('every question has a valid correctIndex', () => {
    expect(validateSeed()).toEqual([]);
  });

  test('every question has a non-empty prompt and at least 2 options', () => {
    seedQuestions.forEach((q) => {
      expect(typeof q.prompt).toBe('string');
      expect(q.prompt.trim().length).toBeGreaterThan(0);
      expect(Array.isArray(q.options)).toBe(true);
      expect(q.options.length).toBeGreaterThanOrEqual(2);
    });
  });

  test('prompts are unique (needed for prompt matching)', () => {
    const prompts = seedQuestions.map((q) => q.prompt);
    expect(new Set(prompts).size).toBe(prompts.length);
  });
});
