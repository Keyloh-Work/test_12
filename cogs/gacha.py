import discord
from discord.ext import commands
from discord import app_commands
import logging
import time
from db import get_points, set_points, get_user_cards, add_card, get_random_item_from_db

logger = logging.getLogger(__name__)
COOLDOWN = 10.0

class PaginatorView(discord.ui.View):
    def __init__(self, data, collected_cards, per_page=20):
        super().__init__(timeout=None)
        self.data = data
        self.collected_cards = collected_cards
        self.per_page = per_page
        self.current_page = 0
        self.total_pages = (len(data) + per_page - 1) // per_page

    def get_page_content(self):
        start_idx = self.current_page * self.per_page
        end_idx = start_idx + self.per_page
        page_content = []
        for item in self.data[start_idx:end_idx]:
            card_no = item["No."]
            title = item["title"]
            if card_no in self.collected_cards:
                page_content.append(f"No.{card_no} {title} :ballot_box_with_check:")
            else:
                page_content.append(f"No.{card_no} {title} :blue_square:")
        return page_content

    async def update_message(self, interaction):
        page_content = "\n".join(self.get_page_content())
        embed = discord.Embed(title=f"{interaction.user.name}のリスト\nPage {self.current_page + 1}/{self.total_pages}", description=page_content)
        await interaction.response.edit_message(embed=embed, view=self)


class GachaButtonView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id

    async def animate_embed(self, interaction, url_info, remaining_points):
        message = await interaction.followup.send("ガチャ中…", ephemeral=False)

        await discord.utils.sleep_until(discord.utils.utcnow()+discord.utils.timedelta(seconds=1))
        embed = discord.Embed(title="秋のハロウィンガチャ")
        await message.edit(content=None, embed=embed)
        await discord.utils.sleep_until(discord.utils.utcnow()+discord.utils.timedelta(seconds=1))

        embed.add_field(name="キャラ", value=url_info['chname'], inline=True)
        await message.edit(embed=embed)
        await discord.utils.sleep_until(discord.utils.utcnow()+discord.utils.timedelta(seconds=1))

        embed.add_field(name="レア度", value="...", inline=True)
        await message.edit(embed=embed)
        await discord.utils.sleep_until(discord.utils.utcnow()+discord.utils.timedelta(seconds=1))

        embed.set_field_at(1, name="レア度", value=url_info['rarity'], inline=True)
        embed.add_field(name="イラストNo.", value=f"No.{url_info['no']}", inline=True)
        embed.add_field(name="タイトル", value=f"{url_info['title']}", inline=True)
        await message.edit(embed=embed)
        await discord.utils.sleep_until(discord.utils.utcnow()+discord.utils.timedelta(seconds=1))

        embed.add_field(name="URL", value=url_info['url'], inline=False)
        embed.set_image(url=url_info['url'])
        await message.edit(embed=embed)
        await discord.utils.sleep_until(discord.utils.utcnow()+discord.utils.timedelta(seconds=1))

        embed.description = f"残りポイント: {remaining_points} pt"
        await message.edit(embed=embed)

    @discord.ui.button(label="ガチャを回す！", style=discord.ButtonStyle.primary)
    async def gacha_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        user_id = interaction.user.id
        points = get_points(user_id)
        if points <= 0:
            await interaction.followup.send("ポイントが不足しています。", ephemeral=True)
            return

        set_points(user_id, points - 1)
        url_info = get_random_item_from_db()
        if url_info is None:
            await interaction.followup.send("ガチャデータがありません。", ephemeral=True)
            return

        add_card(user_id, url_info["no"])
        remaining_points = get_points(user_id)
        await self.animate_embed(interaction, url_info, remaining_points)


class GachaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gacha", description="ガチャを回します")
    async def gacha_cmd(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = time.time()
        if not hasattr(interaction.client, 'last_gacha_usage'):
            interaction.client.last_gacha_usage = {}
        last_time = interaction.client.last_gacha_usage.get(user_id, 0)

        if now - last_time < COOLDOWN:
            remain = int(COOLDOWN - (now - last_time))
            await interaction.response.send_message(f"クールダウン中です。あと {remain} 秒ほどお待ちください。", ephemeral=True)
            return
        interaction.client.last_gacha_usage[user_id] = now

        if isinstance(interaction.channel, discord.Thread) and interaction.channel.name.startswith('gacha-thread-'):
            points = get_points(user_id)
            view = GachaButtonView(self.bot, user_id)
            await interaction.response.send_message(f"下のボタンを押してガチャを回してください。\n残りポイント: {points} pt", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("このコマンドは専用のガチャスレッド内でのみ使用できます。", ephemeral=True)

    @app_commands.command(name="creategachathread", description="専用ガチャスレッドを作成")
    async def create_gacha_thread(self, interaction: discord.Interaction):
        if interaction.channel.name != "gacha-channel":
            await interaction.response.send_message("このコマンドは専用のガチャチャンネルでのみ使用できます。", ephemeral=True)
            return

        existing_thread = discord.utils.get(interaction.channel.threads, name=f'gacha-thread-{interaction.user.name}')
        if existing_thread:
            await interaction.response.send_message("すでにあなたのためのgacha-threadが存在します。", ephemeral=True)
        else:
            gacha_thread = await interaction.channel.create_thread(name=f'gacha-thread-{interaction.user.name}', type=discord.ChannelType.private_thread)
            await gacha_thread.add_user(interaction.user)
            await gacha_thread.edit(slowmode_delay=10)
            await gacha_thread.send(
                f"{interaction.user.mention}\nここはあなた専用のガチャスレッドです。`/gacha`でガチャボタンが表示されます。\n"
                "それを押すとガチャ結果が表示されます。\n"
                "**注意：このスレッドからは退出しないでください。**"
            )
            await interaction.response.send_message("専用ガチャスレッドを作成しました。", ephemeral=True)

    @app_commands.command(name="artlist", description="取得したカードの一覧を表示")
    async def artlist_cmd(self, interaction: discord.Interaction):
        if isinstance(interaction.channel, discord.Thread) and interaction.channel.name.startswith('gacha-thread-'):
            user_id = interaction.user.id
            collected_cards = get_user_cards(user_id)

            # DBには全gacha_itemsが格納済みなのでここでDBからNo.とtitleを全取得
            import sqlite3
            from db import DB_PATH
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT no, title FROM gacha_items")
            rows = cursor.fetchall()
            conn.close()

            if not rows:
                await interaction.response.send_message("データが見つかりません。", ephemeral=True)
                return

            gacha_data = [{"No.": r[0], "title": r[1]} for r in rows]

            view = PaginatorView(gacha_data, collected_cards)
            embed = discord.Embed(title=f"{interaction.user.name}のリスト\nPage 1", description="\n".join(view.get_page_content()))
            await interaction.response.send_message(embed=embed, view=view)
        else:
            await interaction.response.send_message("このコマンドは専用のガチャスレッド内でのみ使用できます。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(GachaCog(bot))
