'use strict';

const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });

const config = {
  service: {
    game: 'game-component',
    question: 'question-component',
    user: 'user-component',
  },
  port: {
    game: parseInt(process.env.GAME_PORT || '3000', 10),
    question: parseInt(process.env.QUESTION_PORT || '3001', 10),
    user: parseInt(process.env.USER_PORT || '3002', 10),
  },
  postgres: {
    connectionString:
      process.env.DATABASE_URL ||
      'postgres://spacefractions:spacefractions@localhost:5432/spacefractions',
  },
  redis: {
    url: process.env.REDIS_URL || 'redis://localhost:6379',
  },
  rabbitmq: {
    url: process.env.RABBITMQ_URL || 'amqp://localhost:5672',
  },
  elasticsearch: {
    node: process.env.ELASTICSEARCH_URL || 'http://localhost:9200',
  },
  oauth2: {
    authorizationEndpoint:
      process.env.OAUTH2_AUTHORIZATION_ENDPOINT || 'http://localhost:9000/authorize',
    tokenEndpoint: process.env.OAUTH2_TOKEN_ENDPOINT || 'http://localhost:9000/token',
    introspectionEndpoint:
      process.env.OAUTH2_INTROSPECTION_ENDPOINT || 'http://localhost:9000/introspect',
    clientId: process.env.OAUTH2_CLIENT_ID || 'space-fractions',
    clientSecret: process.env.OAUTH2_CLIENT_SECRET || 'secret',
    redirectUri: process.env.OAUTH2_REDIRECT_URI || 'http://localhost:3002/oauth/callback',
  },
};

module.exports = { config };
