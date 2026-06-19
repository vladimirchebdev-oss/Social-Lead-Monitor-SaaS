-- Full schema (applied once on empty database via Docker or ensure_schema)

CREATE TYPE user_role AS ENUM ('user', 'admin');
CREATE TYPE billing_interval AS ENUM ('month', 'year');
CREATE TYPE subscription_status AS ENUM ('active', 'canceled', 'past_due', 'trialing', 'incomplete');

-- TikTok content
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
    cover_url TEXT,
    photo_urls TEXT[],
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

-- SaaS users & auth
CREATE TABLE users (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email              TEXT UNIQUE NOT NULL,
    name               TEXT,
    avatar_url         TEXT,
    role               user_role NOT NULL DEFAULT 'user',
    stripe_customer_id TEXT UNIQUE,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    saved_post_ids     TEXT[] NOT NULL DEFAULT '{}',
    last_post_id       TEXT REFERENCES posts(post_id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at      TIMESTAMPTZ
);

CREATE TABLE oauth_accounts (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider         TEXT NOT NULL,
    provider_user_id TEXT NOT NULL,
    UNIQUE (provider, provider_user_id)
);

CREATE TABLE sessions (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Billing
CREATE TABLE platform_subscriptions (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform               TEXT NOT NULL,
    billing_interval       billing_interval NOT NULL,
    status                 subscription_status NOT NULL,
    stripe_subscription_id TEXT UNIQUE,
    stripe_price_id        TEXT,
    current_period_start   TIMESTAMPTZ,
    current_period_end     TIMESTAMPTZ,
    cancel_at_period_end   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, platform)
);

CREATE TABLE payment_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stripe_event_id TEXT UNIQUE NOT NULL,
    event_type      TEXT NOT NULL,
    user_id         UUID REFERENCES users(id),
    amount_cents    INT,
    currency        TEXT DEFAULT 'usd',
    payload         JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_posts_author_id ON posts(author_id);
CREATE INDEX idx_posts_music_id ON posts(music_id);
CREATE INDEX idx_post_hashtags_hashtag_id ON post_hashtags(hashtag_id);
CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_comments_parent_comment_id ON comments(parent_comment_id);
CREATE INDEX idx_comments_author_id ON comments(author_id);
CREATE INDEX idx_oauth_accounts_user_id ON oauth_accounts(user_id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_platform_subscriptions_user_id ON platform_subscriptions(user_id);
CREATE INDEX idx_platform_subscriptions_status ON platform_subscriptions(status);
CREATE INDEX idx_platform_subscriptions_platform ON platform_subscriptions(platform);
CREATE INDEX idx_payment_events_user_id ON payment_events(user_id);
CREATE INDEX idx_payment_events_created_at ON payment_events(created_at);
