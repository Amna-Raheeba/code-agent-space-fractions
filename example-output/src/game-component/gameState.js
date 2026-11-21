'use strict';

// Game state machine per the StateDiagram: Playing -> Paused -> Playing via
// pause()/resume(), and Playing -> GameOver via gameOver().
const STATES = Object.freeze({
  PLAYING: 'Playing',
  PAUSED: 'Paused',
  GAME_OVER: 'GameOver',
});

class GameState {
  constructor(id) {
    this.id = id;
    this.state = STATES.PLAYING;
    this.score = 0;
  }

  pause() {
    if (this.state !== STATES.PLAYING) {
      const err = new Error(`Cannot pause from "${this.state}"`);
      err.code = 'ESTATE';
      throw err;
    }
    this.state = STATES.PAUSED;
    return this.state;
  }

  resume() {
    if (this.state !== STATES.PAUSED) {
      const err = new Error(`Cannot resume from "${this.state}"`);
      err.code = 'ESTATE';
      throw err;
    }
    this.state = STATES.PLAYING;
    return this.state;
  }

  gameOver() {
    if (this.state === STATES.GAME_OVER) {
      const err = new Error(`Game is already over`);
      err.code = 'ESTATE';
      throw err;
    }
    this.state = STATES.GAME_OVER;
    return this.state;
  }

  addScore(points) {
    this.score += points;
    return this.score;
  }

  viewScore() {
    return this.score;
  }
}

module.exports = { GameState, STATES };
