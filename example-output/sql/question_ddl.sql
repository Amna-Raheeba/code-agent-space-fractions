-- Space Fractions: question persistence for the QuestionComponent.
-- Artifact referenced by ASR-1.
--
-- NOTE: The architecture's "data_models" section only defines the `games`
-- table. This `questions` table is derived from the ClassDiagram `Question`
-- class (id, prompt, options) so that the QuestionComponent's "data
-- persistence" responsibility can be fulfilled. See README for details.
CREATE TABLE IF NOT EXISTS questions (
  id SERIAL PRIMARY KEY,
  prompt TEXT NOT NULL,
  options JSONB NOT NULL
);
