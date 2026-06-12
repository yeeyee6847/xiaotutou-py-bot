CREATE TABLE fragment_wants (
    user_id BIGINT NOT NULL,
    rarity TEXT NOT NULL,
    shikigami TEXT NOT NULL,
    quantity INTEGER NOT NULL,

    PRIMARY KEY (user_id, rarity, shikigami)
);