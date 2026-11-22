'use strict';

const { contextBridge, ipcRenderer } = require('electron');

// Expose a minimal, safe API to the renderer. The renderer never talks to the
// microservices directly; all HTTP goes through the main process via IPC.
contextBridge.exposeInMainWorld('desktop', {
  startGame: () => ipcRenderer.invoke('game:start'),
  answer: (questionId, optionIndex) =>
    ipcRenderer.invoke('question:answer', { questionId, optionIndex }),
  finish: (gameId, score) => ipcRenderer.invoke('game:finish', { gameId, score }),
});
