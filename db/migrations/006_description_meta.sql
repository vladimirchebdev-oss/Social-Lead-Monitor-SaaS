ALTER TABLE posts ADD COLUMN IF NOT EXISTS description_length INT;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS description_keywords TEXT[];
