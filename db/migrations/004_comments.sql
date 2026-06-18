CREATE TABLE comments (
    comment_id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL REFERENCES posts(post_id) ON DELETE CASCADE,
    parent_comment_id TEXT REFERENCES comments(comment_id) ON DELETE CASCADE,
    is_reply BOOLEAN NOT NULL DEFAULT FALSE,
    text TEXT,
    create_time BIGINT,
    comment_language TEXT,
    digg_count BIGINT,
    is_author_digged BOOLEAN NOT NULL DEFAULT FALSE,
    reply_comment_total BIGINT,
    author_id TEXT NOT NULL REFERENCES authors(tiktok_id),
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_comments_parent_comment_id ON comments(parent_comment_id);
CREATE INDEX idx_comments_author_id ON comments(author_id);

ALTER TABLE posts DROP COLUMN IF EXISTS comments;
