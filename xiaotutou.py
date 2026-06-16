import os
import json
import discord
import asyncpg
from discord import app_commands
from dotenv import load_dotenv

from keep_alive import keep_alive

load_dotenv()

# Fetch variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_STATUS = os.getenv("BOT_STATUS")

# Discord Log channel ID
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

# ----------------------------------- MYCLIENT START -----------------------------------
class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.pool = await asyncpg.create_pool(
            DATABASE_URL,           
            min_size=1,
            max_size=5,
            timeout=10
        )

        guild = discord.Object(id=771003598981038081)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Guild slash commands synced!")

client = MyClient()
# ----------------------------------- MYCLIENT END -----------------------------------

# ----------------------------------- ON_READY START -----------------------------------
@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    
    activity = discord.Game(name=BOT_STATUS)

    await client.change_presence(
        status=discord.Status.online,
        activity=activity
    )
# ----------------------------------- ON_READY END -----------------------------------

# ----------------------------------- SEND_LOG START -----------------------------------
async def send_log(client, message: str):
    print(f"send_log: {message}")
    channel = await client.fetch_channel(LOG_CHANNEL_ID)
    print(f"send_log: {channel}")
    if channel:
        await channel.send(message)
# ----------------------------------- SEND_LOG END -----------------------------------

# ----------------------------------- HELP START -----------------------------------
@client.tree.command(
    name="help",
    description="小禿頭碎片系统帮助"
)
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
# ----------------------------------- HELP END ----------------------------------- 
    
# ----------------------------------- LOAD SHIKIGAMI JSON START -----------------------------------
with open("data/shikigami.json", "r", encoding="utf-8") as f:
    SHIKIGAMI = json.load(f)
    
RARITY_CHOICES = [
    app_commands.Choice(name=rarity, value=rarity)
    for rarity in SHIKIGAMI.keys()
]
# ----------------------------------- LOAD SHIKIGAMI JSON END -----------------------------------

# ----------------------------------- AUTOCOMPLETE START -----------------------------------
async def shikigami_autocomplete(interaction, current):
    rarity = interaction.namespace.rarity
    names = SHIKIGAMI.get(rarity, [])
    return [
        app_commands.Choice(name=n, value=n)
        for n in names
        if current.lower() in n.lower()
    ][:25]

async def shikigami_autocomplete_a(interaction, current):
    rarity = interaction.namespace.rarity_a
    names = SHIKIGAMI.get(rarity, [])
    return [
        app_commands.Choice(name=n, value=n)
        for n in names
        if current.lower() in n.lower()
    ][:25]

async def shikigami_autocomplete_b(interaction, current):
    rarity = interaction.namespace.rarity_b
    names = SHIKIGAMI.get(rarity, [])
    return [
        app_commands.Choice(name=n, value=n)
        for n in names
        if current.lower() in n.lower()
    ][:25]
# ----------------------------------- AUTOCOMPLETE END -----------------------------------

# ----------------------------------- FRAGMENTS GROUP START -----------------------------------
fragments_group = app_commands.Group(
    name="fragments",
    description="式神碎片系统：可以赠送碎片给寮友，也可以和寮友交换碎片"
)

# ----------------------------------- ADD START -----------------------------------
@fragments_group.command(
    name="add",
    description="增加你拥有的式神碎片"
)
@app_commands.describe(
    rarity="稀有度",
    name="式神名称",
    quantity="数量"
)
@app_commands.choices(rarity=RARITY_CHOICES)
@app_commands.autocomplete(
    name=shikigami_autocomplete
)
async def add(
    interaction: discord.Interaction,
    rarity: app_commands.Choice[str],
    name: str,
    quantity: int
):
    user_id = interaction.user.id

    await interaction.response.defer(thinking=True)  # ⭐ 防止 timeout

    async with client.pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO fragments (user_id, rarity, shikigami, quantity)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, rarity, shikigami)
            DO UPDATE SET quantity = EXCLUDED.quantity
        """,
        interaction.user.id,
        rarity.value,
        name,
        quantity
        )
        
    await send_log(
        client,
        f"📦 ADD | user={interaction.user} ({interaction.user.id}) "
        f"| {rarity.value} {name} x{quantity}"
    )

    await interaction.followup.send(
        f"✅ {interaction.user.mention} 已更新 {quantity} 个【{rarity.value}】{name} 碎片"
    )
# ----------------------------------- ADD END -----------------------------------

# ----------------------------------- LIST START -----------------------------------
@fragments_group.command(
    name="list",
    description="查看玩家拥有/需要式神碎片（可查看自己或他人）"
)
@app_commands.describe(user="要查看的玩家（不填为自己）")
async def list_fragments(
    interaction: discord.Interaction,
    user: discord.Member = None
):
    target = user or interaction.user

    async with client.pool.acquire() as conn:

        # =========================
        # 拥有的碎片
        # =========================
        rows = await conn.fetch("""
            SELECT rarity, shikigami, quantity
            FROM fragments
            WHERE user_id = $1
              AND quantity > 0
            ORDER BY rarity, shikigami
        """, target.id)

        # =========================
        # 想要的碎片
        # =========================
        want_rows = await conn.fetch("""
            SELECT rarity, shikigami, quantity
            FROM fragment_wants
            WHERE user_id = $1
              AND quantity > 0
            ORDER BY rarity, shikigami
        """, target.id)

    # =========================
    # 都没有资料
    # =========================
    if not rows and not want_rows:
        await interaction.response.send_message(
            f"📭 {target.mention} 还没有任何碎片资料"
        )
        return

    # =========================
    # 拥有碎片分组
    # =========================
    owned_data = {}

    for r in rows:
        rarity = r["rarity"]

        if rarity not in owned_data:
            owned_data[rarity] = []

        owned_data[rarity].append(
            f'{r["shikigami"]} x{r["quantity"]}'
        )

    # =========================
    # 想要碎片分组
    # =========================
    want_data = {}

    for r in want_rows:
        rarity = r["rarity"]

        if rarity not in want_data:
            want_data[rarity] = []

        want_data[rarity].append(
            f'{r["shikigami"]} x{r["quantity"]}'
        )

    # =========================
    # Embed
    # =========================
    embed = discord.Embed(
        title="🎴 式神碎片仓库",
        description=(
            f"👤 玩家：{target.mention}\n"
            f"📦 拥有：{len(rows)} 种碎片\n"
            f"🙏 想要：{len(want_rows)} 种碎片"
        ),
        color=0x9b59b6
    )

    rarity_order = ["联动","UR", "SP", "SSR", "SR", "R"]

    # =========================
    # 拥有的碎片
    # =========================
    for rarity in rarity_order:
        if rarity in owned_data:
            embed.add_field(
                name=f"📦 拥有【{rarity}】",
                value="\n".join(owned_data[rarity]),
                inline=False
            )

    # =========================
    # 想要的碎片
    # =========================
    for rarity in rarity_order:
        if rarity in want_data:
            embed.add_field(
                name=f"🙏 想要【{rarity}】",
                value="\n".join(want_data[rarity]),
                inline=False
            )

    await interaction.response.send_message(embed=embed)
# ----------------------------------- LIST END -----------------------------------

# ----------------------------------- WANT START -----------------------------------
@fragments_group.command(
    name="want",
    description="新增想要的碎片"
)
@app_commands.choices(
    rarity=RARITY_CHOICES
)
@app_commands.autocomplete(
    name=shikigami_autocomplete
)
async def want_add(
    interaction: discord.Interaction,
    rarity: app_commands.Choice[str],
    name: str,
    quantity: int
):
    async with client.pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO fragment_wants
            (user_id, rarity, shikigami, quantity)
            VALUES ($1,$2,$3,$4)

            ON CONFLICT (user_id, rarity, shikigami)
            DO UPDATE SET quantity = EXCLUDED.quantity
        """,
        interaction.user.id,
        rarity.value,
        name,
        quantity)

    await interaction.response.send_message(
        f"🙏 已新增需求：{name} x{quantity}"
    )
# ----------------------------------- WANT END -----------------------------------

# ----------------------------------- WANT-CHECK START -----------------------------------
@fragments_group.command(
    name="want-check",
    description="查看谁拥有指定式神碎片"
)
@app_commands.describe(
    rarity="稀有度",
    name="式神名称"
)
@app_commands.choices(
    rarity=RARITY_CHOICES
)
@app_commands.autocomplete(
    name=shikigami_autocomplete
)
async def want_check(
    interaction: discord.Interaction,
    rarity: app_commands.Choice[str],
    name: str
):
    async with client.pool.acquire() as conn:

        rows = await conn.fetch("""
            SELECT user_id, quantity
            FROM fragments
            WHERE rarity = $1
              AND shikigami = $2
              AND quantity > 0
            ORDER BY quantity DESC
        """,
        rarity.value,
        name
        )

    if not rows:
        await interaction.response.send_message(
            f"📭 没有人拥有【{rarity.value}】{name}"
        )
        return

    # =========================
    # Embed
    # =========================
    embed = discord.Embed(
        title=f"🎯 拥有【{rarity.value}】{name} 的玩家",
        color=0x2ecc71
    )

    # =========================
    # 结果列表
    # =========================
    result = []

    for index, row in enumerate(rows, start=1):

        # ✅ 关键：直接 mention（不会依赖 cache）
        result.append(
            f"{index}. <@{row['user_id']}> - {row['quantity']}片"
        )

    embed.description = "\n".join(result)

    await interaction.response.send_message(embed=embed)
# ----------------------------------- WANT-CHECK END -----------------------------------
# ----------------------------------- WANT-REMOVE START -----------------------------------
@fragments_group.command(
    name="want-remove",
    description="减少想要的式神碎片数量"
)
@app_commands.describe(
    rarity="稀有度",
    name="式神名称",
    quantity="减少数量"
)
@app_commands.choices(
    rarity=RARITY_CHOICES
)
@app_commands.autocomplete(
    name=shikigami_autocomplete
)
async def want_remove(
    interaction: discord.Interaction,
    rarity: app_commands.Choice[str],
    name: str,
    quantity: int
):
    async with client.pool.acquire() as conn:

        row = await conn.fetchrow("""
            SELECT quantity
            FROM fragment_wants
            WHERE user_id = $1
              AND rarity = $2
              AND shikigami = $3
        """,
        interaction.user.id,
        rarity.value,
        name)

        if not row:
            await interaction.response.send_message(
                f"❌ 你没有登记想要【{rarity.value}】{name}"
            )
            return

        current_qty = row["quantity"]

        if quantity > current_qty:
            await interaction.response.send_message(
                f"❌ 你只登记了 {current_qty} 片需求"
            )
            return

        new_qty = current_qty - quantity

        if new_qty == 0:

            await conn.execute("""
                DELETE FROM fragment_wants
                WHERE user_id = $1
                  AND rarity = $2
                  AND shikigami = $3
            """,
            interaction.user.id,
            rarity.value,
            name)

            await interaction.response.send_message(
                f"✅ 已从需求清单移除【{rarity.value}】{name}"
            )

        else:

            await conn.execute("""
                UPDATE fragment_wants
                SET quantity = $1
                WHERE user_id = $2
                  AND rarity = $3
                  AND shikigami = $4
            """,
            new_qty,
            interaction.user.id,
            rarity.value,
            name)

            await interaction.response.send_message(
                f"✅ 已减少需求\n"
                f"【{rarity.value}】{name}\n"
                f"{current_qty} ➜ {new_qty}"
            )
# ----------------------------------- WANT-REMOVE END -----------------------------------
# ----------------------------------- MATCH START -----------------------------------
@fragments_group.command(
    name="match",
    description="寻找拥有你想要碎片的玩家"
)
async def match(interaction: discord.Interaction):

    async with client.pool.acquire() as conn:

        # 取得自己的需求
        wants = await conn.fetch("""
            SELECT rarity, shikigami, quantity
            FROM fragment_wants
            WHERE user_id = $1
            ORDER BY rarity, shikigami
        """, interaction.user.id)

        if not wants:
            await interaction.response.send_message(
                "📭 你还没有登记任何想要的碎片"
            )
            return

        embed = discord.Embed(
            title="🎯 碎片配对结果",
            description=f"{interaction.user.mention} 想要的碎片",
            color=0x2ecc71
        )

        found_any = False

        for want in wants:

            rarity = want["rarity"]
            shikigami = want["shikigami"]
            quantity = want["quantity"]

            owners = await conn.fetch("""
                SELECT user_id, quantity
                FROM fragments
                WHERE rarity = $1
                  AND shikigami = $2
                  AND quantity > 0
                  AND user_id != $3
                ORDER BY quantity DESC
            """,
            rarity,
            shikigami,
            interaction.user.id)

            if not owners:
                continue

            found_any = True

            lines = []

            for owner in owners[:10]:  # 最多显示10人

                lines.append(
                    f"<@{owner['user_id']}> - {owner['quantity']}片"
                )

            embed.add_field(
                name=f"【{rarity}】{shikigami} (需求 {quantity}片)",
                value="\n".join(lines),
                inline=False
            )

        if not found_any:
            await interaction.response.send_message(
                "😢 没找到任何拥有你需求碎片的玩家"
            )
            return

        await interaction.response.send_message(
            embed=embed
        )
# ----------------------------------- MATCH END -----------------------------------        
# ----------------------------------- FRAGMENTS GROUP END -----------------------------------

# IMPORTANT: register group
client.tree.add_command(fragments_group)


keep_alive()
client.run(DISCORD_TOKEN)
