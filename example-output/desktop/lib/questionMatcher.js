'use strict';

/**
 * Pure helpers for mapping server-side question ids to the seed bank's
 * correctIndex, and for evaluating a submitted answer.
 *
 * The QuestionService only exposes prompt/options (no correct-answer field, per
 * the ClassDiagram). The desktop therefore recovers correctness from the seed
 * bank by matching a question's prompt to its designed correctIndex.
 */

/**
 * Build a map of `questionId -> correctIndex` by matching each question's
 * prompt against the seed bank. Questions that do not match the seed bank are
 * omitted (their correctness is unknown).
 */
function buildCorrectIndex(questions, seed) {
  const byPrompt = new Map();
  for (const s of seed) {
    byPrompt.set(s.prompt, s.correctIndex);
  }
  const map = {};
  for (const q of questions) {
    if (byPrompt.has(q.prompt)) {
      map[q.id] = byPrompt.get(q.prompt);
    }
  }
  return map;
}

/**
 * Evaluate a submitted option index for a question id.
 * Returns { found, correct, correctIndex } where `found` is false when the
 * question id is not present in the correctIndex map.
 */
function evaluate(correctIndexById, questionId, optionIndex) {
  if (!Object.prototype.hasOwnProperty.call(correctIndexById, questionId)) {
    return { found: false, correct: false, correctIndex: null };
  }
  const correctIndex = correctIndexById[questionId];
  const correct = Number(optionIndex) === correctIndex;
  return { found: true, correct, correctIndex };
}

module.exports = { buildCorrectIndex, evaluate };
