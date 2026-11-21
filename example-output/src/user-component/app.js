'use strict';

const express = require('express');
const { AuthService, requireAuth } = require('./auth');
const { InMemoryUserStore } = require('./inMemoryUserStore');

function createUserApp(options = {}) {
  const userStore = options.userStore || new InMemoryUserStore();
  const authService = options.authService || new AuthService({ userStore });

  const app = express();
  app.use(express.json());

  // OAuth2 authorization-code flow: redirect the end user to the provider.
  app.get('/login', (req, res) => {
    res.redirect(authService.authorizationUri());
  });

  // OAuth2 callback: exchange code for token (out of scope for the stub; the
  // real implementation would call config.oauth2.tokenEndpoint).
  app.get('/oauth/callback', (req, res) => {
    res.status(501).json({
      error: 'callback token exchange not implemented; use a bearer token directly',
    });
  });

  app.use('/me', requireAuth(authService));
  app.get('/me', (req, res) => {
    res.status(200).json(req.auth);
  });

  // eslint-disable-next-line no-unused-vars
  app.use((err, req, res, next) => {
    res.status(err.status || 500).json({ error: err.message });
  });

  return app;
}

module.exports = { createUserApp };
