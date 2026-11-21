'use strict';

// Minimal in-memory question store used by default and in tests. Production
// wiring can substitute a PostgreSQL-backed store matching sql/question_ddl.sql.
class InMemoryQuestionStore {
  constructor() {
    this.questions = new Map();
    this.nextId = 1;
  }

  list() {
    return Array.from(this.questions.values()).map((q) => ({ ...q }));
  }

  get(id) {
    const q = this.questions.get(id);
    return q ? { ...q } : undefined;
  }

  create({ prompt, options }) {
    const id = this.nextId++;
    const question = { id, prompt, options: [...options] };
    this.questions.set(id, question);
    return { ...question };
  }

  update(id, { prompt, options }) {
    const existing = this.questions.get(id);
    if (!existing) return undefined;
    const question = {
      id,
      prompt: prompt !== undefined ? prompt : existing.prompt,
      options: options !== undefined ? [...options] : existing.options,
    };
    this.questions.set(id, question);
    return { ...question };
  }

  remove(id) {
    return this.questions.delete(id);
  }
}

module.exports = { InMemoryQuestionStore };
