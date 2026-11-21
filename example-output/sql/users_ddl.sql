-- Space Fractions: user persistence for the UserComponent.
-- Derived from the ClassDiagram `User` class (id, username). See README.
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username TEXT NOT NULL UNIQUE
);
