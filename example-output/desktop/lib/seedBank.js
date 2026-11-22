'use strict';

/**
 * Designed seed bank of fraction questions for the desktop game.
 *
 * The architecture documents define no questions and no "correct answer" field
 * (the ClassDiagram `Question` class exposes only id, prompt, and options).
 * These 12 questions, each with a `correctIndex` (0-based index into `options`),
 * are designed here so the desktop game can give right/wrong feedback. See the
 * README ("Seed bank (designed)") for the rationale.
 */
const seedQuestions = [
  { prompt: '1/2 + 1/4 = ?', options: ['3/4', '2/6', '1/6', '1/8'], correctIndex: 0 },
  { prompt: '1/3 + 1/3 = ?', options: ['2/3', '1/6', '2/6', '3/3'], correctIndex: 0 },
  { prompt: '2/5 + 1/5 = ?', options: ['3/10', '3/5', '2/5', '1/5'], correctIndex: 1 },
  { prompt: '3/4 - 1/4 = ?', options: ['1/2', '1/4', '2/4', '1'], correctIndex: 0 },
  { prompt: '1 - 1/3 = ?', options: ['1/3', '2/3', '3/3', '0'], correctIndex: 1 },
  { prompt: '1/2 of 10 = ?', options: ['5', '10', '2', '20'], correctIndex: 0 },
  { prompt: 'Which fraction is largest?', options: ['1/4', '1/3', '1/2', '1/6'], correctIndex: 2 },
  { prompt: '1/4 + 1/4 = ?', options: ['2/8', '1/2', '1/8', '2/4'], correctIndex: 1 },
  { prompt: '3/6 simplified = ?', options: ['1/3', '2/3', '1/2', '3/2'], correctIndex: 2 },
  { prompt: '5/5 = ?', options: ['0', '5', '1/5', '1'], correctIndex: 3 },
  { prompt: '2 × 1/4 = ?', options: ['1/2', '1/4', '2/4', '1/8'], correctIndex: 0 },
  { prompt: '1/8 + 3/8 = ?', options: ['4/16', '1/2', '4/8', '2/8'], correctIndex: 1 },
];

/**
 * Validate the seed bank returns an empty array when every question is well
 * formed and its correctIndex points at a real option; otherwise an array of
 * human-readable problem descriptions.
 */
function validateSeed(questions = seedQuestions) {
  const problems = [];
  questions.forEach((q, i) => {
    const tag = `seed[${i}]`;
    if (typeof q.prompt !== 'string' || q.prompt.trim() === '') {
      problems.push(`${tag}: prompt must be a non-empty string`);
    }
    if (!Array.isArray(q.options) || q.options.length < 2) {
      problems.push(`${tag}: options must be an array with at least 2 entries`);
    }
    const optionCount = Array.isArray(q.options) ? q.options.length : 0;
    if (
      !Number.isInteger(q.correctIndex) ||
      q.correctIndex < 0 ||
      q.correctIndex >= optionCount
    ) {
      problems.push(`${tag}: correctIndex must be an integer within options bounds`);
    }
  });
  return problems;
}

module.exports = { seedQuestions, validateSeed };
