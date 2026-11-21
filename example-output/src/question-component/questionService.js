'use strict';

const { InMemoryQuestionStore } = require('./inMemoryQuestionStore');

/**
 * QuestionService implements question management for the QuestionComponent.
 *
 * Answer *checking* (per the SequenceDiagram "check answer" step) is not fully
 * specified by the architecture: the ClassDiagram `Question` class exposes only
 * id, prompt, and options, with no designated correct-answer field. The
 * checkAnswer method therefore validates that a submitted option index falls
 * within the question's options; whether an answer is "correct" is left to a
 * data field not defined in the spec (see README).
 */
class QuestionService {
  constructor({ questionStore } = {}) {
    this.store = questionStore || new InMemoryQuestionStore();
  }

  list() {
    return this.store.list();
  }

  get(id) {
    return this._require(id);
  }

  create({ prompt, options }) {
    this._validate({ prompt, options });
    return this.store.create({ prompt, options });
  }

  update(id, { prompt, options }) {
    if (prompt !== undefined && options !== undefined) {
      this._validate({ prompt, options });
    }
    const updated = this.store.update(id, { prompt, options });
    if (!updated) {
      const err = new Error(`question ${id} not found`);
      err.code = 'ENOTFOUND';
      throw err;
    }
    return updated;
  }

  remove(id) {
    const removed = this.store.remove(id);
    if (!removed) {
      const err = new Error(`question ${id} not found`);
      err.code = 'ENOTFOUND';
      throw err;
    }
    return true;
  }

  getPrompt(id) {
    return this._require(id).prompt;
  }

  getOptions(id) {
    return this._require(id).options;
  }

  checkAnswer(id, optionIndex) {
    const question = this._require(id);
    const index = Number(optionIndex);
    const valid = Number.isInteger(index) && index >= 0 && index < question.options.length;
    return { valid, selected: valid ? question.options[index] : null };
  }

  _require(id) {
    const question = this.store.get(id);
    if (!question) {
      const err = new Error(`question ${id} not found`);
      err.code = 'ENOTFOUND';
      throw err;
    }
    return question;
  }

  _validate({ prompt, options }) {
    if (typeof prompt !== 'string' || prompt.trim() === '') {
      const err = new Error('prompt must be a non-empty string');
      err.code = 'EINVAL';
      throw err;
    }
    if (!Array.isArray(options) || options.length === 0) {
      const err = new Error('options must be a non-empty array');
      err.code = 'EINVAL';
      throw err;
    }
  }
}

module.exports = { QuestionService };
