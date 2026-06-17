ALTER TABLE posts ADD COLUMN IF NOT EXISTS description_preview TEXT;

UPDATE posts
SET description_preview = description
WHERE description_preview IS NULL AND description IS NOT NULL;

UPDATE posts SET description = NULL;
