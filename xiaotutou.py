import os
import json
import discord
import asyncpg
from discord import app_commands
from dotenv import load_dotenv
from discord.ext import commands
from keep_alive import keep_alive

load_dotenv()

# Fetch variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_STATUS = os.getenv("BOT_STATUS")

# Discord Log channel ID
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

class MyClient(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.pool = await asyncpg.create_pool(
            DATABASE_URL,           
            min_size=1,
            max_size=5,
            timeout=10
        )
        
        # =========================
        # LOAD COGS（就在这里加）
        # =========================
        await self.load_extension("cogs.game_account")
        await self.load_extension("cogs.fragment")

        # =========================
        # SYNC slash commands
        # =========================
        guild = discord.Object(id=771003598981038081)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Guild slash commands synced!")
        
client = MyClient()

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    
    activity = discord.Game(name=BOT_STATUS)

    await client.change_presence(
        status=discord.Status.online,
        activity=activity
    )

# ================================== HELP START ================================== #
@client.tree.command(name="help", description="小禿頭碎片系统帮助")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎴 《小禿頭轉職交換碎片資訊員》",
        description=(
            "還在煩惱碎片的資訊不夠清晰、要瘋狂刷交換區帖子嗎？\n\n"
            "禿佬聽到各位的心聲了‼️\n"
            "小禿頭全新升級‼️\n"
            "介面簡單方便好上手‼️"
        ),
        color=0xf1c40f
    )

    embed.add_field(
        name="⭐️ 使用方法 ⭐️",
        value=(
            "❶ 輸入指令 `/`\n"
            "❷ 選擇「fragments」\n"
            "❸ 使用以下功能"
        ),
        inline=False
    )

    # =========================
    # FRAGMENTS
    # =========================
    embed.add_field(
        name="📦 碎片系统（Fragments）",
        value=(
            "• `/fragments add` ➜ 添加碎片\n"
            "• `/fragments remove` ➜ 删除碎片\n"
            "• `/fragments list` ➜ 查看自己的碎片 + 想要\n"
            "• `/fragments list @玩家` ➜ 查看他人碎片\n"
        ),
        inline=False
    )

    # =========================
    # WANT SYSTEM
    # =========================
    embed.add_field(
        name="🙏 需求系统（Want System）",
        value=(
            "• `/fragments want` ➜ 添加想要的碎片\n"
            "• `/fragments want-remove` ➜ 删除想要的碎片\n"
            "• `/fragments want-check` ➜ 查看谁拥有你想要的碎片\n"
        ),
        inline=False
    )

    # =========================
    # MATCH SYSTEM
    # =========================
    embed.add_field(
        name="🎯 配对系统（Match System）",
        value=(
            "• `/fragments match` ➜ 自动匹配拥有你需求碎片的玩家\n"
        ),
        inline=False
    )

    # =========================
    # NOTE
    # =========================
    embed.add_field(
        name="⚠️ 注意事项",
        value=(
            "＊添加、删除碎片需逐项更新\n"
            "＊一条指令只可编辑一种式神\n"
            "＊交换前请确认数量是否足够\n"
            "＊数据以数据库为准"
        ),
        inline=False
    )

    embed.set_footer(text="by 番茄佬 🍅")

    await interaction.response.send_message(embed=embed)
# ================================== HELP END ================================== #

keep_alive()
client.run(DISCORD_TOKEN)
