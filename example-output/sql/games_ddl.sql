-- Space Fractions: games table (exact data model from the architecture spec)
CREATE TABLE IF NOT EXISTS games (
  id SERIAL PRIMARY KEY,
  game_state JSONB NOT NULL
);
