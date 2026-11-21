'use strict';

const { config } = require('./config');

let channel = null;
let connecting = null;

async function getChannel() {
  if (channel) return channel;
  if (!connecting) {
    connecting = (async () => {
      const amqp = require('amqplib');
      const conn = await amqp.connect(config.rabbitmq.url);
      channel = await conn.createChannel();
      return channel;
    })();
  }
  return connecting;
}

module.exports = {
  async publish(queue, message) {
    const ch = await getChannel();
    await ch.assertQueue(queue, { durable: true });
    return ch.sendToQueue(queue, Buffer.from(JSON.stringify(message)), {
      persistent: true,
    });
  },
};
