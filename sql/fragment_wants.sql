CREATE TABLE fragment_wants (
    user_id BIGINT NOT NULL,
    rarity TEXT NOT NULL,
    shikigami TEXT NOT NULL,
    quantity INTEGER NOT NULL,

    PRIMARY KEY (user_id, rarity, shikigami)
);

CREATE TABLE fragment_wants_v2 (
    game_account_id INT NOT NULL,
    shikigami_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (
        game_account_id,
        shikigami_id
    ),

    FOREIGN KEY (game_account_id)
        REFERENCES game_accounts(id)
        ON DELETE CASCADE,

    FOREIGN KEY (shikigami_id)
        REFERENCES shikigami(id)
        ON DELETE CASCADE
);