CREATE TABLE fragment_logs (
    id SERIAL PRIMARY KEY,
    from_user BIGINT NOT NULL,
    to_user BIGINT NOT NULL,
    rarity TEXT NOT NULL,
    shikigami TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);