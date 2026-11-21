'use strict';

const { config } = require('../shared/config');

/**
 * OAuth2 authentication/authorization for the UserComponent.
 *
 * The architecture specifies OAuth2 as the auth mechanism. This implementation
 * provides the authorization-code flow entry points and a bearer-token
 * verification middleware. Token verification is modelled through an injectable
 * `tokenVerifier` that, in production, would call the OAuth2 authorization
 * server's introspection endpoint (config.oauth2.introspectionEndpoint). A
 * default in-memory verifier is used for local development and tests.
 */
class AuthService {
  constructor({ tokenVerifier, userStore } = {}) {
    this.tokenVerifier = tokenVerifier || defaultVerifier();
    this.userStore = userStore;
  }

  authorizationUri() {
    const query = new URLSearchParams({
      response_type: 'code',
      client_id: config.oauth2.clientId,
      redirect_uri: config.oauth2.redirectUri,
      scope: 'openid profile',
    });
    return `${config.oauth2.authorizationEndpoint}?${query.toString()}`;
  }

  authenticate(bearerToken) {
    if (!bearerToken) {
      const err = new Error('missing bearer token');
      err.code = 'EUNAUTH';
      throw err;
    }
    const payload = this.tokenVerifier(bearerToken);
    if (!payload || !payload.sub) {
      const err = new Error('invalid or expired token');
      err.code = 'EUNAUTH';
      throw err;
    }
    return payload;
  }
}

function defaultVerifier() {
  // Development-only verifier: a token of the form "user:<id>" resolves to a
  // subject. Real deployments MUST replace this with OAuth2 introspection.
  return (token) => {
    const match = /^user:(\d+)$/.exec(token);
    if (!match) return null;
    return { sub: `user:${match[1]}`, id: parseInt(match[1], 10) };
  };
}

function requireAuth(authService) {
  return (req, res, next) => {
    const header = req.get('authorization') || '';
    const token = header.startsWith('Bearer ') ? header.slice(7) : null;
    try {
      req.auth = authService.authenticate(token);
      next();
    } catch (err) {
      res.status(401).json({ error: err.message });
    }
  };
}

module.exports = { AuthService, requireAuth, defaultVerifier };
