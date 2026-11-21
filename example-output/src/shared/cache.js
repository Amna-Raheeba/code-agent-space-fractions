'use strict';

const { config } = require('./config');

let client = null;
let connecting = null;

async function getClient() {
  if (client) return client;
  if (!connecting) {
    connecting = (async () => {
      // Lazily require so importing this module never loads Redis unless used.
      const { createClient } = require('redis');
      client = createClient({ url: config.redis.url });
      client.on('error', () => { /* swallow; availability is non-critical for gameplay */ });
      await client.connect();
      return client;
    })();
  }
  return connecting;
}

module.exports = {
  async get(key) {
    return (await getClient()).get(key);
  },
  async set(key, value) {
    return (await getClient()).set(key, value);
  },
  async del(key) {
    return (await getClient()).del(key);
  },
};
