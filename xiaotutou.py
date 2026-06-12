import json
import discord
import asyncpg
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.pool = await asyncpg.create_pool(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            host=os.getenv("DB_HOST")
)

        guild = discord.Object(id=771003598981038081)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Guild slash commands synced!")

client = MyClient()

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")

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
# ----------------------------------- FRAGMENTS GROUP END -----------------------------------

# IMPORTANT: register group
client.tree.add_command(fragments_group)

token = os.getenv("DISCORD_TOKEN")
client.run(token)
