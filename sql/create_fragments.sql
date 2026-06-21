CREATE TABLE fragments (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    rarity TEXT NOT NULL,
    shikigami TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (user_id, rarity, shikigami)
);

CREATE TABLE fragments_v2 (
    id SERIAL PRIMARY KEY,
    game_account_id INT NOT NULL,
    shikigami_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (game_account_id, shikigami_id),

    FOREIGN KEY (game_account_id) REFERENCES game_accounts(id),
    FOREIGN KEY (shikigami_id) REFERENCES shikigami(id)
);