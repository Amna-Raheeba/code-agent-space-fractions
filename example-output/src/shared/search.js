'use strict';

const { config } = require('./config');

let client = null;

function getClient() {
  if (!client) {
    const { Client } = require('@elastic/elasticsearch');
    client = new Client({ node: config.elasticsearch.node });
  }
  return client;
}

module.exports = {
  async index({ index, id, body }) {
    return getClient().index({ index, id, body });
  },
  async search({ index, query }) {
    return getClient().search({ index, query });
  },
};
