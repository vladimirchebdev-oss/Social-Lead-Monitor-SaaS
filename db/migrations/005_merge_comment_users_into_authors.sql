-- Merge comment_users into authors and re-link comments FK.

INSERT INTO authors (tiktok_id, unique_id, nickname, updated_at)
SELECT
    cu.uid,
    COALESCE(NULLIF(cu.unique_id, ''), cu.uid),
    cu.nickname,
    cu.updated_at
FROM comment_users cu
ON CONFLICT (tiktok_id) DO UPDATE SET
    nickname = COALESCE(EXCLUDED.nickname, authors.nickname),
    unique_id = COALESCE(NULLIF(EXCLUDED.unique_id, ''), authors.unique_id),
    updated_at = NOW();

ALTER TABLE comments DROP CONSTRAINT IF EXISTS comments_author_uid_fkey;

ALTER TABLE comments RENAME COLUMN author_uid TO author_id;

ALTER TABLE comments
    ADD CONSTRAINT comments_author_id_fkey
    FOREIGN KEY (author_id) REFERENCES authors(tiktok_id);

DROP INDEX IF EXISTS idx_comments_author_uid;
CREATE INDEX IF NOT EXISTS idx_comments_author_id ON comments(author_id);

DROP TABLE comment_users;
