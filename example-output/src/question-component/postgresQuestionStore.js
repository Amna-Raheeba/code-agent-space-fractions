'use strict';

// PostgreSQL-backed question store (persistence responsibility of the
// QuestionComponent). Matches sql/question_ddl.sql.
class PostgresQuestionStore {
  constructor({ pool }) {
    this.pool = pool;
  }

  async list() {
    const { rows } = await this.pool.query(
      'SELECT id, prompt, options FROM questions ORDER BY id'
    );
    return rows.map((r) => ({ id: r.id, prompt: r.prompt, options: r.options }));
  }

  async get(id) {
    const { rows } = await this.pool.query(
      'SELECT id, prompt, options FROM questions WHERE id = $1',
      [id]
    );
    return rows.length ? rows[0] : undefined;
  }

  async create({ prompt, options }) {
    const { rows } = await this.pool.query(
      'INSERT INTO questions (prompt, options) VALUES ($1, $2) RETURNING id, prompt, options',
      [prompt, JSON.stringify(options)]
    );
    return rows[0];
  }

  async update(id, { prompt, options }) {
    const existing = await this.get(id);
    if (!existing) return undefined;
    const newPrompt = prompt !== undefined ? prompt : existing.prompt;
    const newOptions =
      options !== undefined ? JSON.stringify(options) : JSON.stringify(existing.options);
    const { rows } = await this.pool.query(
      'UPDATE questions SET prompt = $1, options = $2 WHERE id = $3 RETURNING id, prompt, options',
      [newPrompt, newOptions, id]
    );
    return rows.length ? rows[0] : undefined;
  }

  async remove(id) {
    const { rowCount } = await this.pool.query('DELETE FROM questions WHERE id = $1', [id]);
    return rowCount > 0;
  }
}

module.exports = { PostgresQuestionStore };
