import discord
from discord import app_commands
from discord.ext import commands

class Fragment(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot

    fragment = app_commands.Group(
        name="fragment",
        description="碎片系统"
    )
    
    RARITY_CHOICES=[
        app_commands.Choice(name="UR", value="UR"),
        app_commands.Choice(name="SP", value="SP"),
        app_commands.Choice(name="SSR", value="SSR"),
        app_commands.Choice(name="联动", value="联动"),
    ]
    
    async def account_autocomplete(self, interaction: discord.Interaction, current: str):
        async with self.bot.pool.acquire() as conn:

            rows = await conn.fetch("""
                SELECT game_name
                FROM game_accounts
                WHERE discord_user_id = $1
                AND game_name ILIKE $2
                ORDER BY game_name
                LIMIT 25
            """, interaction.user.id, f"%{current}%")

        return [
            app_commands.Choice(name=r["game_name"], value=r["game_name"])
            for r in rows
        ]   
        
    async def shikigami_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ):

        rarity = getattr(interaction.namespace, "rarity", None)

        # =========================
        # safety：rarity 可能是 Choice
        # =========================
        if isinstance(rarity, app_commands.Choice):
            rarity = rarity.value

        async with self.bot.pool.acquire() as conn:

            # =========================
            # 有 rarity
            # =========================
            if rarity:
                rows = await conn.fetch("""
                    SELECT id, name_sim, name_tra, rarity
                    FROM shikigami
                    WHERE rarity = $1
                    AND (
                        name_sim ILIKE $2
                        OR name_tra ILIKE $2
                    )
                    ORDER BY id
                    LIMIT 25
                """, rarity, f"%{current}%")

            # =========================
            # 没 rarity（fallback）
            # =========================
            else:
                rows = await conn.fetch("""
                    SELECT id, name_sim, name_tra, rarity
                    FROM shikigami
                    WHERE name_sim ILIKE $1
                    OR name_tra ILIKE $1
                    ORDER BY id
                    LIMIT 25
                """, f"%{current}%")

        return [
            app_commands.Choice(
                name=f"{r['name_sim']} / {r['name_tra']} [{r['rarity']}]",
                value=str(r["id"])
            )
            for r in rows
        ]   
        
    # ================================== LIST START ================================== #
    @fragment.command(name="list", description="查看碎片")
    @app_commands.describe(user="要查看的玩家（不填为自己）")
    async def list_fragments(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user

        async with self.bot.pool.acquire() as conn:

            # =========================
            # 持有碎片
            # =========================
            rows = await conn.fetch("""
                SELECT 
                    a.game_name,
                    s.rarity,
                    s.name_tra,
                    f.quantity
                FROM fragments_v2 f
                JOIN game_accounts a ON f.game_account_id = a.id
                JOIN shikigami s ON f.shikigami_id = s.id
                WHERE a.discord_user_id = $1
                AND f.quantity > 0
                ORDER BY s.rarity, s.id, a.game_name
            """, target.id)

            # =========================
            # 需求碎片（WANT）
            # =========================
            want_rows = await conn.fetch("""
                SELECT 
                    a.game_name,
                    s.rarity,
                    s.name_tra,
                    w.quantity
                FROM fragment_wants_v2 w
                JOIN game_accounts a ON w.game_account_id = a.id
                JOIN shikigami s ON w.shikigami_id = s.id
                WHERE a.discord_user_id = $1
                AND w.quantity > 0
                ORDER BY s.rarity, s.id, a.game_name
            """, target.id)

        # =========================
        # 没数据
        # =========================
        if not rows and not want_rows:
            await interaction.response.send_message(
                f"📭 {target.mention} 没有碎片记录",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🎴 式神碎片倉庫",
            description=f"👤 {target.mention}",
            color=0x9b59b6
        )

        rarity_order = ["UR", "SP", "SSR", "联动"]

        # =========================
        # 持有碎片整理
        # =========================
        data = {}

        for r in rows:

            rarity = r["rarity"]
            shiki = r["name_tra"]
            acc = r["game_name"]
            qty = r["quantity"]

            data.setdefault(rarity, {})
            data[rarity].setdefault(shiki, {})
            data[rarity][shiki][acc] = data[rarity][shiki].get(acc, 0) + qty

        # =========================
        # 输出持有
        # =========================
        for rarity in rarity_order:

            if rarity not in data:
                continue

            lines = [f"⭐ {rarity}"]

            for shiki, acc_map in data[rarity].items():

                lines.append(f"\n🎴 {shiki}")

                for acc, qty in acc_map.items():
                    lines.append(f"   🎮 {acc} x{qty}")

            embed.add_field(
                name="🎒 持有碎片",
                value="\n".join(lines)[:1024],
                inline=False
            )

        # =========================
        # 需求碎片整理
        # =========================
        want_data = {}

        for r in want_rows:

            rarity = r["rarity"]
            shiki = r["name_tra"]
            acc = r["game_name"]
            qty = r["quantity"]

            want_data.setdefault(rarity, {})
            want_data[rarity].setdefault(shiki, {})
            want_data[rarity][shiki][acc] = qty

        # =========================
        # 输出需求（底部）
        # =========================
        if want_data:

            lines = ["🙏 需求碎片"]

            for rarity in rarity_order:

                if rarity not in want_data:
                    continue

                lines.append(f"\n⭐ {rarity}")

                for shiki, acc_map in want_data[rarity].items():

                    lines.append(f"\n🎴 {shiki}")

                    for acc, qty in acc_map.items():
                        lines.append(f"   🎮 {acc} x{qty}")

            embed.add_field(
                name="\u200b",
                value="\n".join(lines)[:1024],
                inline=False
            )

        await interaction.response.send_message(embed=embed)    
    # ================================== LIST END ================================== #         
    
    # ================================== ADD START ================================== #
    @fragment.command(name="add", description="新增碎片（单条快速录入）")
    @app_commands.describe(account="遊戲賬號", rarity="稀有度", shikigami="式神名稱（支持简体/繁体）", quantity="数量")
    @app_commands.choices(rarity = RARITY_CHOICES)
    @app_commands.autocomplete(account=account_autocomplete, shikigami=shikigami_autocomplete)
    async def add(
        self,
        interaction: discord.Interaction,
        account: str,
        rarity: app_commands.Choice[str],
        shikigami: str,
        quantity: int
    ):

        if quantity <= 0:
            await interaction.response.send_message(
                "❌ 数量必须大于 0",
                ephemeral=True
            )
            return

        async with self.bot.pool.acquire() as conn:

            # =========================
            # 找账号
            # =========================
            acc_row = await conn.fetchrow("""
                SELECT id
                FROM game_accounts
                WHERE discord_user_id = $1
                AND game_name = $2
            """, interaction.user.id, account)

            if not acc_row:
                await interaction.response.send_message("❌ 找不到账号", ephemeral=True)
                return

            # =========================
            # 找式神（中/繁体模糊）
            # =========================
            shiki_row = await conn.fetchrow("""
                    SELECT id, name_sim, name_tra
                    FROM shikigami
                    WHERE id = $1
                """, int(shikigami))

            if not shiki_row:
                await interaction.response.send_message("❌ 找不到式神", ephemeral=True)
                return

            # =========================
            # UPSERT
            # =========================
            await conn.execute("""
                INSERT INTO fragments_v2
                (game_account_id, shikigami_id, quantity)
                VALUES ($1, $2, $3)
                ON CONFLICT (game_account_id, shikigami_id)
                DO UPDATE SET
                    quantity = fragments_v2.quantity + EXCLUDED.quantity,
                    updated_at = NOW()
            """,
            acc_row["id"],
            shiki_row["id"],
            quantity)

        await interaction.response.send_message(
            f"✅ 已添加碎片 +{quantity}\n"
            f"🎮 {account}\n"
            f"🎴 {shiki_row['name_tra']} / {shiki_row['name_sim']}",
            ephemeral=True
        )
    # ================================== ADD END ================================== #
    
    # ================================== IMPORT START ================================== #
    @fragment.command(name="import", description="上傳txt批量匯入碎片 (格式: 稀有度 式神 x數量)" )
    @app_commands.describe(account="遊戲帳號（不選則使用主號）", file="上傳txt檔案")
    @app_commands.autocomplete(account=account_autocomplete)
    async def fragment_import(
        self,
        interaction: discord.Interaction,
        account: str,
        file: discord.Attachment
    ):
        # =========================
        # 1. 檔案檢查
        # =========================
        if not file.filename.endswith(".txt"):
            await interaction.response.send_message(
                "❌ 只能上傳 .txt 檔案",
                ephemeral=True
            )
            return

        # =========================
        # 2. 讀取檔案
        # =========================
        content = await file.read()

        try:
            text = content.decode("utf-8")
        except Exception:
            await interaction.response.send_message(
                "❌ 檔案編碼必須為 UTF-8",
                ephemeral=True
            )
            return

        lines = text.split("\n")

        parsed = []
        errors = []

        # =========================
        # 3. 解析 TXT（核心）
        # =========================
        for i, line in enumerate(lines, start=1):

            line = line.strip()

            if not line:
                continue

            try:
                if "x" not in line:
                    errors.append(f"第 {i} 行格式錯誤（缺少 x）：{line}")
                    continue

                left, qty = line.rsplit("x", 1)
                qty = int(qty.strip())

                parts = left.strip().split(" ", 1)

                if len(parts) != 2:
                    errors.append(f"第 {i} 行格式錯誤（應為：稀有度 式神 x數量）：{line}")
                    continue

                rarity = parts[0].strip()
                name = parts[1].strip()

                parsed.append((rarity, name, qty))

            except Exception:
                errors.append(f"第 {i} 行解析失敗：{line}")

        # =========================
        # 4. 錯誤直接返回
        # =========================
        if errors:
            await interaction.response.send_message(
                "❌ 匯入失敗：\n\n" + "\n".join(errors[:10]),
                ephemeral=True
            )
            return

        # =========================
        # 5. DB
        # =========================
        async with self.bot.pool.acquire() as conn:

            # =========================
            # 找帳號
            # =========================
            if account:

                account_row = await conn.fetchrow("""
                    SELECT id
                    FROM game_accounts
                    WHERE discord_user_id = $1
                    AND game_name = $2
                """,
                interaction.user.id,
                account)

                if not account_row:
                    await interaction.response.send_message(
                        "❌ 找不到該遊戲帳號",
                        ephemeral=True
                    )
                    return

            else:

                account_row = await conn.fetchrow("""
                    SELECT id
                    FROM game_accounts
                    WHERE discord_user_id = $1
                    ORDER BY is_main DESC
                    LIMIT 1
                """, interaction.user.id)

                if not account_row:
                    await interaction.response.send_message(
                        "❌ 尚未設定遊戲帳號",
                        ephemeral=True
                    )
                    return

            # =========================
            # 寫入碎片
            # =========================
            for rarity, name, qty in parsed:

                shiki = await conn.fetchrow("""
                    SELECT id, name_tra, name_sim
                    FROM shikigami
                    WHERE rarity = $1
                    AND (
                            name_tra ILIKE '%' || $2 || '%'
                        OR name_sim ILIKE '%' || $2 || '%'
                    )
                    LIMIT 1
                """, rarity, name)

                if not shiki:
                    await interaction.response.send_message(
                        f"❌ 找不到式神：[{rarity}] {name}",
                        ephemeral=True
                    )
                    return

                await conn.execute("""
                    INSERT INTO fragments_v2
                    (game_account_id, shikigami_id, quantity)
                    VALUES ($1,$2,$3)
                    ON CONFLICT (game_account_id, shikigami_id)
                    DO UPDATE SET
                        quantity = EXCLUDED.quantity,
                        updated_at = NOW()
                """,
                account_row["id"],
                shiki["id"],
                qty)

        # =========================
        # 6. 成功回报
        # =========================
        await interaction.response.send_message(
            f"✅ 成功匯入 {len(parsed)} 筆碎片資料",
            ephemeral=True
        )
    # ================================== IMPORT END ================================== #
    
    # ================================== WANT START ================================== #
    @fragment.command(name="want", description="新增需求碎片")
    @app_commands.describe(account="遊戲帳號", rarity="稀有度", shikigami="式神", quantity="需求數量")
    @app_commands.autocomplete( account=account_autocomplete, shikigami=shikigami_autocomplete)
    @app_commands.choices(rarity = RARITY_CHOICES)
    async def want(
        self,
        interaction: discord.Interaction,
        account: str,
        rarity: app_commands.Choice[str],
        shikigami: str,
        quantity: int
    ):

        if quantity <= 0:
            await interaction.response.send_message(
                "❌ 數量必須大於 0",
                ephemeral=True
            )
            return

        async with self.bot.pool.acquire() as conn:

            # =========================
            # 找帳號
            # =========================
            account_row = await conn.fetchrow("""
                SELECT id
                FROM game_accounts
                WHERE discord_user_id = $1
                AND game_name = $2
            """,
            interaction.user.id,
            account)

            if not account_row:
                await interaction.response.send_message(
                    "❌ 找不到遊戲帳號",
                    ephemeral=True
                )
                return

            # =========================
            # 找式神
            # =========================
            shiki_row = await conn.fetchrow("""
                SELECT id,
                    name_tra,
                    name_sim
                FROM shikigami
                WHERE id = $1
            """,
            int(shikigami))

            if not shiki_row:
                await interaction.response.send_message(
                    "❌ 找不到式神",
                    ephemeral=True
                )
                return

            # =========================
            # 新增需求
            # =========================
            await conn.execute("""
                INSERT INTO fragment_wants_v2
                (
                    game_account_id,
                    shikigami_id,
                    quantity
                )
                VALUES ($1,$2,$3)

                ON CONFLICT
                (
                    game_account_id,
                    shikigami_id
                )
                DO UPDATE
                SET quantity = EXCLUDED.quantity,
                    updated_at = NOW()
            """,
            account_row["id"],
            shiki_row["id"],
            quantity)

        await interaction.response.send_message(
            f"🙏 已更新需求\n\n"
            f"🎮 帳號：{account}\n"
            f"🎴 式神：{shiki_row['name_tra']} / {shiki_row['name_sim']}\n"
            f"📦 需求：{quantity}片"
        )
    # ================================== WANT END ================================== #
    
    # ================================== CHECK START ================================== #
    @fragment.command(name="check", description="查看谁拥有指定式神碎片")
    @app_commands.describe(rarity="稀有度", name="式神名稱")
    @app_commands.choices(rarity=RARITY_CHOICES)
    @app_commands.autocomplete(name=shikigami_autocomplete)
    async def check(
        self,
        interaction: discord.Interaction,
        rarity: app_commands.Choice[str],
        name: str
    ):

        async with self.bot.pool.acquire() as conn:

            rows = await conn.fetch("""
                    SELECT 
                        a.game_name,
                        a.discord_user_id,
                        s.name_tra,
                        s.name_sim,
                        f.quantity
                    FROM fragments_v2 f
                    JOIN game_accounts a
                        ON f.game_account_id = a.id
                    JOIN shikigami s
                        ON f.shikigami_id = s.id
                    WHERE s.rarity = $1
                    AND s.id = $2
                    AND f.quantity > 0
                    ORDER BY f.quantity DESC
                """, rarity.value, int(name))

        if not rows:
            await interaction.response.send_message(
                f"📭 沒有人擁有這個式神碎片！",
                ephemeral=True
            )
            return

        shiki_name = rows[0]["name_tra"]

        embed = discord.Embed(
            title=f"🎯 持有【{rarity.value}】{shiki_name} 的玩家",
            color=0x2ecc71
        )

        # =========================
        # 输出
        # =========================
        lines = []

        for i, r in enumerate(rows, start=1):

            lines.append(
                f"{i}. 🎮 **{r['game_name']}** "
                f"(<@{r['discord_user_id']}>) "
                f"- `x{r['quantity']}`"
            )

        embed.description = "\n".join(lines)

        await interaction.response.send_message(embed=embed)
    # ================================== CHECK END ================================== #
    
    # ================================== MATCH START ================================== #
    @fragment.command(name="match", description="尋找擁有你想要碎片的玩家")
    async def match(self, interaction: discord.Interaction):
        async with self.bot.pool.acquire() as conn:
            # =========================
            # 取得自己的需求（v2）
            # =========================
            wants = await conn.fetch("""
                SELECT 
                    w.shikigami_id,
                    w.quantity,
                    s.rarity,
                    s.name_tra,
                    s.name_sim
                FROM fragment_wants_v2 w
                JOIN shikigami s
                    ON w.shikigami_id = s.id
                JOIN game_accounts a
                    ON w.game_account_id = a.id
                WHERE a.discord_user_id = $1
                ORDER BY s.rarity, s.id
            """, interaction.user.id)

            if not wants:
                await interaction.response.send_message(
                    "📭 你還沒等級任何想要的碎片",
                    ephemeral=True
                )
                return

            embed = discord.Embed(
                title="🎯 碎片配對結果",
                description=f"{interaction.user.mention} 想要的碎片",
                color=0x2ecc71
            )

            found_any = False

            rarity_order = ["UR", "SP", "SSR", "联动"]

            # =========================
            # 每个 want 去找持有者
            # =========================
            for want in wants:

                shiki_id = want["shikigami_id"]
                need_qty = want["quantity"]
                rarity = want["rarity"]

                shiki_name = f"{want['name_tra']} / {want['name_sim']}"

                owners = await conn.fetch("""
                    SELECT 
                        a.game_name,
                        a.discord_user_id,
                        f.quantity
                    FROM fragments_v2 f
                    JOIN game_accounts a
                        ON f.game_account_id = a.id
                    WHERE f.shikigami_id = $1
                    AND f.quantity > 0
                    AND a.discord_user_id != $2
                    ORDER BY f.quantity DESC
                """,
                shiki_id,
                interaction.user.id)

                if not owners:
                    continue

                found_any = True

                lines = []

                for owner in owners[:10]:

                    lines.append(
                        f"🎮 **{owner['game_name']}** "
                        f"(<@{owner['discord_user_id']}>) "
                        f"- `{owner['quantity']}`"
                    )

                embed.add_field(
                    name=f"🎴 【{rarity}】{shiki_name} (需求 {need_qty})",
                    value="\n".join(lines),
                    inline=False
                )

        # =========================
        # 最终输出
        # =========================
        if not found_any:
            await interaction.response.send_message(
                "😢 沒找到任何擁有你需求碎片的玩家",
                ephemeral=True
            )
            return

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Fragment(bot))