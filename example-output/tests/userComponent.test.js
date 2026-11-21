'use strict';

const request = require('supertest');
const { createUserApp } = require('../src/user-component/app');
const { AuthService } = require('../src/user-component/auth');
const { InMemoryUserStore } = require('../src/user-component/inMemoryUserStore');

describe('AuthService', () => {
  test('authenticate accepts a valid dev token', () => {
    const svc = new AuthService({ userStore: new InMemoryUserStore() });
    const payload = svc.authenticate('user:42');
    expect(payload).toEqual({ sub: 'user:42', id: 42 });
  });

  test('authenticate rejects missing token', () => {
    const svc = new AuthService({ userStore: new InMemoryUserStore() });
    expect(() => svc.authenticate(null)).toThrow(/missing bearer token/);
  });

  test('authenticate rejects invalid token', () => {
    const svc = new AuthService({ userStore: new InMemoryUserStore() });
    expect(() => svc.authenticate('garbage')).toThrow(/invalid or expired/);
  });

  test('authorizationUri points at the OAuth2 provider', () => {
    const svc = new AuthService({ userStore: new InMemoryUserStore() });
    expect(svc.authorizationUri()).toContain('response_type=code');
  });
});

describe('user /me endpoint', () => {
  test('returns 401 without authorization header', async () => {
    const app = createUserApp();
    const res = await request(app).get('/me');
    expect(res.status).toBe(401);
  });

  test('returns the subject with a valid bearer token', async () => {
    const app = createUserApp();
    const res = await request(app).get('/me').set('Authorization', 'Bearer user:7');
    expect(res.status).toBe(200);
    expect(res.body).toEqual({ sub: 'user:7', id: 7 });
  });

  test('returns 401 with an invalid bearer token', async () => {
    const app = createUserApp();
    const res = await request(app).get('/me').set('Authorization', 'Bearer bad');
    expect(res.status).toBe(401);
  });
});
