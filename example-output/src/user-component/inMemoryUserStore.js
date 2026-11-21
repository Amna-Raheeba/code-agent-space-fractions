'use strict';

// Minimal in-memory user store used by default and in tests. Production wiring
// can substitute a PostgreSQL-backed store matching sql/users_ddl.sql.
class InMemoryUserStore {
  constructor() {
    this.users = new Map();
    this.nextId = 1;
  }

  create({ username }) {
    const id = this.nextId++;
    const user = { id, username };
    this.users.set(id, user);
    return { ...user };
  }

  get(id) {
    const u = this.users.get(id);
    return u ? { ...u } : undefined;
  }

  findByUsername(username) {
    for (const u of this.users.values()) {
      if (u.username === username) return { ...u };
    }
    return undefined;
  }
}

module.exports = { InMemoryUserStore };
