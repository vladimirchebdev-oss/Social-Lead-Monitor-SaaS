CREATE TABLE IF NOT EXISTS music (
    music_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    play_url TEXT NOT NULL,
    cover_large TEXT NOT NULL,
    author_name TEXT NOT NULL,
    original BOOLEAN NOT NULL DEFAULT FALSE,
    duration INT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE posts ADD COLUMN IF NOT EXISTS music_id TEXT REFERENCES music(music_id);

CREATE INDEX IF NOT EXISTS idx_posts_music_id ON posts(music_id);
