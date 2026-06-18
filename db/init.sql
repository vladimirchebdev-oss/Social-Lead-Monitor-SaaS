CREATE TABLE authors (
    tiktok_id TEXT PRIMARY KEY,
    unique_id TEXT NOT NULL,
    nickname TEXT,
    avatar_larger TEXT,
    create_time BIGINT,
    verified BOOLEAN DEFAULT FALSE,
    follower_count BIGINT,
    following_count BIGINT,
    heart BIGINT,
    heart_count BIGINT,
    video_count BIGINT,
    digg_count BIGINT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE music (
    music_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    play_url TEXT NOT NULL,
    cover_large TEXT NOT NULL,
    author_name TEXT NOT NULL,
    original BOOLEAN NOT NULL DEFAULT FALSE,
    duration INT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE posts (
    post_id TEXT PRIMARY KEY,
    content_type TEXT NOT NULL CHECK (content_type IN ('video', 'photo')),
    url TEXT NOT NULL,
    author_id TEXT NOT NULL REFERENCES authors(tiktok_id),
    music_id TEXT REFERENCES music(music_id),
    description TEXT,
    description_preview TEXT,
    description_length INT,
    description_keywords TEXT[],
    location_created TEXT,
    diversification_labels TEXT[],
    play_count BIGINT,
    digg_count BIGINT,
    comment_count BIGINT,
    share_count BIGINT,
    collect_count BIGINT,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE hashtags (
    hashtag_id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE post_hashtags (
    post_id TEXT REFERENCES posts(post_id) ON DELETE CASCADE,
    hashtag_id TEXT REFERENCES hashtags(hashtag_id),
    start_pos INT NOT NULL,
    end_pos INT NOT NULL,
    PRIMARY KEY (post_id, start_pos, end_pos)
);

CREATE INDEX idx_posts_author_id ON posts(author_id);
CREATE INDEX idx_posts_music_id ON posts(music_id);
CREATE INDEX idx_post_hashtags_hashtag_id ON post_hashtags(hashtag_id);
