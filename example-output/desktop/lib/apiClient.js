'use strict';

/**
 * Thin HTTP client over the running microservices, using Node 18's global
 * fetch. The Electron main process uses this so the renderer never talks to the
 * services directly (avoiding CORS and keeping a single HTTP boundary).
 */
class ApiClient {
  constructor({ gameUrl, questionUrl, userUrl }) {
    this.gameUrl = gameUrl;
    this.questionUrl = questionUrl;
    this.userUrl = userUrl;
  }

  async _request(method, url, body) {
    const res = await fetch(url, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const text = await res.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = text;
      }
    }
    if (!res.ok) {
      const message = (data && data.error) || `HTTP ${res.status}`;
      const err = new Error(message);
      err.status = res.status;
      throw err;
    }
    return data;
  }

  // GameService.Play / GET /play
  async play() {
    return this._request('GET', `${this.gameUrl}/play`);
  }

  async getScore(gameId) {
    return this._request('GET', `${this.gameUrl}/game/${gameId}/score`);
  }

  async gameOver(gameId) {
    return this._request('POST', `${this.gameUrl}/game/${gameId}/gameover`);
  }

  async listQuestions() {
    return this._request('GET', `${this.questionUrl}/questions`);
  }

  async getQuestion(id) {
    return this._request('GET', `${this.questionUrl}/questions/${id}`);
  }

  async createQuestion({ prompt, options }) {
    return this._request('POST', `${this.questionUrl}/questions`, { prompt, options });
  }

  async checkAnswer(id, optionIndex) {
    return this._request('POST', `${this.questionUrl}/questions/${id}/check`, {
      optionIndex,
    });
  }
}

module.exports = { ApiClient };
