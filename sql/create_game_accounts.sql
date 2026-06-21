CREATE TABLE game_accounts (
    id SERIAL PRIMARY KEY,
    discord_user_id BIGINT NOT NULL,
    game_name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (discord_user_id, game_name)
);

-- 添加 is_main 列，表示是否为主账号
ALTER TABLE game_accounts ADD COLUMN is_main BOOLEAN NOT NULL DEFAULT FALSE;

-- 创建一个唯一索引，确保每个用户只能有一个主账号
CREATE UNIQUE INDEX ux_game_accounts_one_main
ON game_accounts (discord_user_id)
WHERE is_main = TRUE;

