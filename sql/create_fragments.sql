CREATE TABLE fragments (
    id SERIAL PRIMARY KEY,

    user_id BIGINT NOT NULL,

    rarity TEXT NOT NULL,
    shikigami TEXT NOT NULL,

    quantity INTEGER NOT NULL DEFAULT 0,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (user_id, rarity, shikigami)
);