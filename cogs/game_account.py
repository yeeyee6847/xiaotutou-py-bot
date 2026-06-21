import discord
import asyncio
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button

class GameAccount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    account = app_commands.Group(
        name="account",
        description="遊戲賬號系統"
    )
    
    # autocomplete for game account name
    async def account_autocomplete(self, interaction: discord.Interaction, current: str):
        async with self.bot.pool.acquire() as conn:
            # 获取用户的账号列表，支持模糊搜索
            rows = await conn.fetch("""
                SELECT game_name
                FROM game_accounts
                WHERE discord_user_id = $1
                AND game_name ILIKE $2
                ORDER BY game_name
                LIMIT 25
            """,
            interaction.user.id,
            f"%{current}%")

        return [
            app_commands.Choice(
                name=r["game_name"],
                value=r["game_name"]
            )
            for r in rows
        ]

    # ================================== SET MAIN START ================================== #
    @account.command(name="main", description="設定遊戲大號")
    @app_commands.describe(account_name="要設為大號的遊戲賬號")
    @app_commands.autocomplete(account_name=account_autocomplete)
    async def set_main(self, interaction: discord.Interaction, account_name: str):
        async with self.bot.pool.acquire() as conn:
            # 查找用户输入的账号是否存在
            account_row = await conn.fetchrow("""
                SELECT id
                FROM game_accounts
                WHERE discord_user_id = $1
                AND game_name = $2
            """,
            interaction.user.id, account_name)

            if not account_row:
                await interaction.response.send_message(
                    "❌ 找不到该账号",
                    ephemeral=True
                )
                return

            # 清除原本主号
            await conn.execute("""
                UPDATE game_accounts
                SET is_main = FALSE
                WHERE discord_user_id = $1
            """,
            interaction.user.id)

            # 设定新主号
            await conn.execute("""
                UPDATE game_accounts
                SET is_main = TRUE
                WHERE id = $1
            """,
            account_row["id"])

        await interaction.response.send_message(
            f"✅ 已設定大號為：**{account_name}**"
        )   
    # ================================== SET MAIN END ================================== #
    
    # ================================== ADD START ================================== #
    @account.command(name="add", description="添加遊戲賬號")
    @app_commands.describe(name="遊戲賬號名称")
    async def add(self, interaction: discord.Interaction, name: str):
        async with self.bot.pool.acquire() as conn:
            # 先检查是否已存在同名账号
            exists = await conn.fetchrow("""
                SELECT 1
                FROM game_accounts
                WHERE discord_user_id = $1
                  AND game_name = $2
            """, interaction.user.id, name)

            # 如果存在，则提示用户
            if exists:
                await interaction.response.send_message(
                    f"⚠️ 你已經有這個賬號了：`{name}`",
                    ephemeral=True
                )
                return

            # 添加新账号
            await conn.execute("""
                INSERT INTO game_accounts (discord_user_id, game_name)
                VALUES ($1, $2)
            """, interaction.user.id, name)

        # 响应用户
        await interaction.response.send_message(
            f"✅ 已添加遊戲賬號：`{name}`"
        )      
    # ================================== ADD END ================================== #
    
    # ================================== LIST START ================================== #
    @account.command(name="list", description="查看遊戲賬號列表")
    @app_commands.describe(user="要查看的玩家（不填为自己）")
    async def list(self, interaction: discord.Interaction, user: discord.Member = None):

        # 如果没有指定用户，则默认查看自己
        target = user or interaction.user

        async with self.bot.pool.acquire() as conn:

            rows = await conn.fetch("""
                SELECT game_name, is_main
                FROM game_accounts
                WHERE discord_user_id = $1
                ORDER BY is_main DESC, game_name
            """, target.id)

        # 没有账号
        if not rows:
            await interaction.response.send_message(
                f"📭 {target.mention} 還沒有任何遊戲帳號"
            )
            return

        main_account = None
        alt_accounts = []

        for r in rows:
            if r["is_main"]:
                main_account = r["game_name"]
            else:
                alt_accounts.append(r["game_name"])

        # =========================
        # 组装显示
        # =========================
        lines = []

        if main_account:
            lines.append(f"⭐ 主號：**{main_account}**")
        else:
            lines.append("⭐ 主號：未設定")

        if alt_accounts:
            lines.append("\n🎮 小號：")
            for acc in alt_accounts:
                lines.append(f"• `{acc}`")

        # =========================
        # Embed
        # =========================
        embed = discord.Embed(
            title="🎮 遊戲帳號列表",
            color=0x2ecc71
        )

        embed.description = (
            f"👤 玩家：{target.mention}\n"
            f"📦 總帳號數：**{len(rows)}**\n\n"
            f"{chr(9473) * 20}\n"
            f"{'\n'.join(lines)}\n"
            f"{chr(9473) * 20}"
        )

        await interaction.response.send_message(embed=embed)
    # ================================== LIST END ================================== #
    
    # ================================== REMOVE START ================================== #
    @account.command(name="remove", description="刪除遊戲賬號")
    @app_commands.describe(account_name="要刪除的遊戲賬號")
    @app_commands.autocomplete(account_name=account_autocomplete)
    async def remove(self, interaction: discord.Interaction, account_name: str):
        async with self.bot.pool.acquire() as conn:

            # 確認帳號存在
            account_row = await conn.fetchrow("""
                SELECT id
                FROM game_accounts
                WHERE discord_user_id = $1
                AND game_name = $2
            """,
            interaction.user.id,
            account_name)

            if not account_row:
                await interaction.response.send_message(
                    "❌ 找不到該遊戲賬號",
                    ephemeral=True
                )
                return

            # 計算帳號數量
            count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM game_accounts
                WHERE discord_user_id = $1
            """,
            interaction.user.id)

            # 只剩一個不能刪
            if count <= 1:
                await interaction.response.send_message(
                    f"⚠️ 你只剩一個遊戲賬號 **{account_name}**，不能刪除",
                    ephemeral=True
                )
                return

        # =========================
        # Confirm UI
        # =========================
        class ConfirmDeleteView(discord.ui.View):

            def __init__(self, bot):
                super().__init__(timeout=30)
                self.bot = bot

            @discord.ui.button(
                label="✅ 確認刪除",
                style=discord.ButtonStyle.danger
            )
            async def confirm(
                self,
                interaction_btn: discord.Interaction,
                button: discord.ui.Button
            ):

                async with self.bot.pool.acquire() as conn:

                    await conn.execute("""
                        DELETE FROM game_accounts
                        WHERE discord_user_id = $1
                        AND game_name = $2
                    """,
                    interaction_btn.user.id,
                    account_name)

                await interaction_btn.response.edit_message(
                    content=f"🗑️ 已刪除遊戲賬號：**{account_name}**",
                    view=None
                )

            @discord.ui.button(
                label="❌ 取消",
                style=discord.ButtonStyle.secondary
            )
            async def cancel(
                self,
                interaction_btn: discord.Interaction,
                button: discord.ui.Button
            ):

                await interaction_btn.response.edit_message(
                    content="❎ 已取消刪除",
                    view=None
                )

        await interaction.response.send_message(
            f"⚠️ 你確定要刪除遊戲賬號 **{account_name}** 嗎？\n\n此操作無法復原。",
            view=ConfirmDeleteView(self.bot),
            ephemeral=True
        )
    # ================================== REMOVE END ================================== #
        
    # ================================== RENAME START ================================== #
    @account.command(name="rename", description="修改遊戲帳號名稱")
    @app_commands.describe(
        account_name="要修改的遊戲帳號",
        new_name="新的遊戲帳號名稱"
    )
    @app_commands.autocomplete(
        account_name=account_autocomplete
    )
    async def rename(
        self,
        interaction: discord.Interaction,
        account_name: str,
        new_name: str
    ):

        new_name = new_name.strip()

        if not new_name:
            await interaction.response.send_message(
                "❌ 帳號名稱不能為空",
                ephemeral=True
            )
            return

        async with self.bot.pool.acquire() as conn:

            # 確認帳號存在
            account_row = await conn.fetchrow("""
                SELECT id
                FROM game_accounts
                WHERE discord_user_id = $1
                AND game_name = $2
            """,
            interaction.user.id,
            account_name)

            if not account_row:
                await interaction.response.send_message(
                    "❌ 找不到該帳號",
                    ephemeral=True
                )
                return

            # 檢查名稱是否重複
            exists = await conn.fetchrow("""
                SELECT 1
                FROM game_accounts
                WHERE discord_user_id = $1
                AND game_name = $2
                AND id != $3
            """,
            interaction.user.id,
            new_name,
            account_row["id"])

            if exists:
                await interaction.response.send_message(
                    "❌ 這個帳號名稱已經存在",
                    ephemeral=True
                )
                return

            # 更新名稱
            await conn.execute("""
                UPDATE game_accounts
                SET game_name = $1
                WHERE id = $2
            """,
            new_name,
            account_row["id"])

        await interaction.response.send_message(
            f"✅ 已將帳號 **{account_name}** 更名為 **{new_name}**"
        )
    # ================================== RENAME END ================================== #

async def setup(bot):
    await bot.add_cog(GameAccount(bot))