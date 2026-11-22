'use strict';

/* global window, document */

// The preload script exposes `window.desktop`; every service call goes through
// the Electron main process over HTTP. The renderer only holds UI state and
// keeps a local score tally for the ending screen.
(function () {
  const api = window.desktop;

  const screens = {
    intro: document.getElementById('intro-screen'),
    menu: document.getElementById('menu-screen'),
    help: document.getElementById('help-screen'),
    question: document.getElementById('question-screen'),
    ending: document.getElementById('ending-screen'),
  };

  const els = {
    introContinue: document.getElementById('intro-continue'),
    menuPlay: document.getElementById('menu-play'),
    menuScore: document.getElementById('menu-score'),
    menuHelp: document.getElementById('menu-help'),
    helpBack: document.getElementById('help-back'),
    questionProgress: document.getElementById('question-progress'),
    questionScore: document.getElementById('question-score'),
    questionPrompt: document.getElementById('question-prompt'),
    questionOptions: document.getElementById('question-options'),
    questionFeedback: document.getElementById('question-feedback'),
    questionNext: document.getElementById('question-next'),
    endingScore: document.getElementById('ending-score'),
    endingFeedback: document.getElementById('ending-feedback'),
    endingAgain: document.getElementById('ending-again'),
    endingMenu: document.getElementById('ending-menu'),
  };

  const state = {
    gameId: null,
    questions: [],
    index: 0,
    score: 0,
    lastScore: null,
    answered: false,
  };

  function show(name) {
    Object.values(screens).forEach((s) => s.classList.remove('active'));
    screens[name].classList.add('active');
  }

  function setFeedback(text, kind) {
    els.questionFeedback.textContent = text;
    els.questionFeedback.className = 'feedback' + (kind ? ` ${kind}` : '');
  }

  function clearOptions() {
    els.questionOptions.innerHTML = '';
  }

  function updateHud() {
    const total = state.questions.length || 1;
    els.questionProgress.textContent = `Question ${Math.min(state.index + 1, total)} of ${total}`;
    els.questionScore.textContent = `Score: ${state.score}`;
  }

  async function startGame() {
    try {
      const { gameId, questions } = await api.startGame();
      state.gameId = gameId;
      state.questions = questions || [];
      state.index = 0;
      state.score = 0;
      state.answered = false;
      if (state.questions.length === 0) {
        showEnding(0, 0, 'No questions were available.');
        return;
      }
      renderQuestion();
      show('question');
    } catch (err) {
      setFeedback(`Could not start the game: ${err.message || err}`, 'bad');
      show('question');
    }
  }

  function renderQuestion() {
    const q = state.questions[state.index];
    state.answered = false;
    els.questionPrompt.textContent = q.prompt;
    els.questionNext.classList.add('hidden');
    setFeedback('');
    clearOptions();
    updateHud();

    q.options.forEach((option, idx) => {
      const li = document.createElement('li');
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = option;
      btn.addEventListener('click', () => onAnswer(q.id, idx));
      li.appendChild(btn);
      els.questionOptions.appendChild(li);
    });
  }

  async function onAnswer(questionId, optionIndex) {
    if (state.answered) return;
    state.answered = true;

    // Disable all option buttons for this question.
    const buttons = Array.from(els.questionOptions.querySelectorAll('button'));
    buttons.forEach((b) => (b.disabled = true));

    let result;
    try {
      result = await api.answer(questionId, optionIndex);
    } catch (err) {
      setFeedback(`Error checking answer: ${err.message || err}`, 'bad');
      els.questionNext.classList.remove('hidden');
      return;
    }

    // Highlight the correct option and, if wrong, the picked one.
    buttons.forEach((btn, idx) => {
      if (result.found && idx === result.correctIndex) btn.classList.add('correct');
      if (result.found && !result.correct && idx === optionIndex) btn.classList.add('wrong');
    });

    if (!result.found) {
      setFeedback('Answer feedback is unavailable for this question.', 'bad');
    } else if (result.correct) {
      state.score += 1;
      setFeedback('Correct! 🚀', 'good');
    } else {
      setFeedback('Not quite — the correct answer is highlighted.', 'bad');
    }
    updateHud();
    els.questionNext.classList.remove('hidden');
  }

  function nextQuestion() {
    state.index += 1;
    if (state.index >= state.questions.length) {
      finishGame();
    } else {
      renderQuestion();
    }
  }

  async function finishGame() {
    const score = state.score;
    const total = state.questions.length;
    try {
      if (state.gameId !== null) {
        await api.finish(state.gameId, score);
      }
    } catch {
      /* game-over call is best-effort; the ending screen still shows the tally */
    }
    showEnding(score, total, null);
  }

  function showEnding(score, total, overrideMessage) {
    state.lastScore = { score, total };
    els.endingScore.textContent = `${score} / ${total}`;
    if (overrideMessage) {
      els.endingFeedback.textContent = overrideMessage;
    } else if (total === 0) {
      els.endingFeedback.textContent = 'Nothing to score.';
    } else if (score === total) {
      els.endingFeedback.textContent = 'Perfect mission, astronaut! 🌟';
    } else if (score >= total / 2) {
      els.endingFeedback.textContent = 'Great work — keep practicing!';
    } else {
      els.endingFeedback.textContent = 'Good effort — try again to improve!';
    }
    show('ending');
  }

  function showScoreMenu() {
    if (!state.lastScore) {
      els.endingScore.textContent = '0 / 0';
      els.endingFeedback.textContent = 'You have not played a game yet.';
    } else {
      const { score, total } = state.lastScore;
      els.endingScore.textContent = `${score} / ${total}`;
      els.endingFeedback.textContent = 'Your last mission score.';
    }
    show('ending');
  }

  els.introContinue.addEventListener('click', () => show('menu'));
  els.menuPlay.addEventListener('click', startGame);
  els.menuScore.addEventListener('click', showScoreMenu);
  els.menuHelp.addEventListener('click', () => show('help'));
  els.helpBack.addEventListener('click', () => show('menu'));
  els.questionNext.addEventListener('click', nextQuestion);
  els.endingAgain.addEventListener('click', startGame);
  els.endingMenu.addEventListener('click', () => show('menu'));

  show('intro');
})();
