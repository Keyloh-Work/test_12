import discord
from discord.ext import commands
from discord import app_commands
import csv
import chardet
import random
import asyncio
import logging
import time

logger = logging.getLogger(__name__)

COOLDOWN = 10.0  # クールダウン必要なければ0や削除も可能

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

    @discord.ui.button(label="<<", style=discord.ButtonStyle.danger)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        await self.update_message(interaction)

    @discord.ui.button(label="<", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
        await self.update_message(interaction)

    @discord.ui.button(label=">", style=discord.ButtonStyle.success)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
        await self.update_message(interaction)

    @discord.ui.button(label=">>", style=discord.ButtonStyle.primary)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.total_pages - 1
        await self.update_message(interaction)


class GachaButtonView(discord.ui.View):
    def __init__(self, bot, user_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id

    @discord.ui.button(label="ガチャを回す！", style=discord.ButtonStyle.primary)
    async def gacha_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        user_id = interaction.user.id
        self.bot.ensure_user_points(user_id)
        points = self.bot.user_points[user_id]
        if points <= 0:
            await interaction.followup.send("ポイントが不足しています。", ephemeral=True)
            return

        # ポイント消費
        self.bot.user_points[user_id] = points - 1

        url_info = await self.get_random_url()
        if url_info is None:
            await interaction.followup.send("ガチャデータの読み込みに失敗しました。", ephemeral=True)
            return

        # 新カード獲得判定
        if url_info["no"] not in self.bot.user_cards.get(user_id, []):
            self.bot.user_cards.setdefault(user_id, []).append(url_info["no"])

        remaining_points = self.bot.user_points[user_id]
        await self.animate_embed(interaction, url_info, remaining_points)

    def add_emoji_to_rarity(self, rarity):
        if rarity == "N":
            return "🌈 N"
        elif rarity == "R":
            return "💫 R 💫"
        elif rarity == "SR":
            return "✨ 🌟 SR 🌟 ✨"
        elif rarity == "SSR":
            return "🎉✨✨👑 SSR 👑✨✨🎉"
        return rarity

    async def get_random_url(self):
        gacha_data = []
        try:
            with open(self.bot.gacha_data_path, 'rb') as f:
                result = chardet.detect(f.read())
            encoding = result['encoding']

            with open(self.bot.gacha_data_path, newline='', encoding=encoding) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    gacha_data.append({
                        "url": row["url"],
                        "chname": row["chname"],
                        "rarity": self.add_emoji_to_rarity(row["rarity"]),
                        "rate": float(row["rate"]),
                        "no": row["No."],
                        "title": row["title"]
                    })
        except FileNotFoundError as e:
            logger.error(f"CSVファイルが見つかりません: {e}")
            return None
        except Exception:
            logger.exception("CSV読み込み中にエラーが発生しました:")
            return None

        if not gacha_data:
            return None

        total_rate = sum(item["rate"] for item in gacha_data)
        random_value = random.uniform(0, total_rate)
        current_rate = 0

        for item in gacha_data:
            current_rate += item["rate"]
            if random_value <= current_rate:
                return item
        return gacha_data[-1]

    async def animate_embed(self, interaction, url_info, remaining_points):
        message = await interaction.followup.send("ガチャ中…", ephemeral=False)

        await asyncio.sleep(1)
        embed = discord.Embed(title="クリスマスガチャ")
        await message.edit(content=None, embed=embed)
        await asyncio.sleep(1)

        embed.add_field(name="キャラ", value=url_info['chname'], inline=True)
        await message.edit(embed=embed)
        await asyncio.sleep(1)

        embed.add_field(name="レア度", value="...", inline=True)
        await message.edit(embed=embed)
        await asyncio.sleep(1)

        embed.set_field_at(1, name="レア度", value=url_info['rarity'], inline=True)
        embed.add_field(name="イラストNo.", value=f"No.{url_info['no']}", inline=True)
        embed.add_field(name="タイトル", value=f"{url_info['title']}", inline=True)
        await message.edit(embed=embed)
        await asyncio.sleep(1)

        embed.add_field(name="URL", value=url_info['url'], inline=False)
        embed.set_image(url=url_info['url'])
        await message.edit(embed=embed)
        await asyncio.sleep(1)

        embed.description = f"残りポイント: {remaining_points} pt"
        await message.edit(embed=embed)


class GachaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gacha", description="ガチャを回します")
    async def gacha_cmd(self, interaction: discord.Interaction):
        # クールダウンチェック(必要なければ削除可能)
        user_id = interaction.user.id
        now = time.time()
        last_time = self.bot.last_gacha_usage.get(user_id, 0)
        if now - last_time < COOLDOWN:
            remain = int(COOLDOWN - (now - last_time))
            await interaction.response.send_message(
                f"クールダウン中です。あと {remain} 秒お待ちください。",
                ephemeral=True
            )
            return
        self.bot.last_gacha_usage[user_id] = now

        self.bot.ensure_user_points(user_id)

        if isinstance(interaction.channel, discord.Thread) and interaction.channel.name.startswith('gacha-thread-'):
            points = self.bot.user_points[user_id]
            view = GachaButtonView(self.bot, user_id)
            await interaction.response.send_message(
                f"下のボタンを押してガチャを回してください。\n残りポイント: {points} pt",
                view=view,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "このコマンドは専用のガチャスレッド内でのみ使用できます。",
                ephemeral=True
            )

    @app_commands.command(name="creategachathread", description="専用ガチャスレッドを作成します")
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

    @app_commands.command(name="artlist", description="取得したカードの一覧を表示します")
    async def artlist_cmd(self, interaction: discord.Interaction):
        self.bot.ensure_user_points(interaction.user.id)
        if isinstance(interaction.channel, discord.Thread) and interaction.channel.name.startswith('gacha-thread-'):
            user_id = interaction.user.id
            collected_cards = self.bot.user_cards.get(user_id, [])

            gacha_data = []
            try:
                with open(self.bot.gacha_data_path, 'rb') as f:
                    result = chardet.detect(f.read())
                encoding = result['encoding']

                with open(self.bot.gacha_data_path, newline='', encoding=encoding) as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        gacha_data.append({"No.": row["No."], "title": row["title"]})
            except FileNotFoundError as e:
                logger.error(f"CSVファイルが見つかりません: {e}")
                await interaction.response.send_message("データファイルが見つかりません。管理者に連絡してください。", ephemeral=True)
                return
            except Exception:
                logger.exception("CSV読み込み中にエラーが発生しました:")
                await interaction.response.send_message("内部エラーが発生しました。管理者に連絡してください。", ephemeral=True)
                return

            if not gacha_data:
                await interaction.response.send_message("データが見つかりません。", ephemeral=True)
                return

            view = PaginatorView(gacha_data, collected_cards)
            embed = discord.Embed(title=f"{interaction.user.name}のリスト\nPage 1", description="\n".join(view.get_page_content()))
            await interaction.response.send_message(embed=embed, view=view)
        else:
            await interaction.response.send_message("このコマンドは専用のガチャスレッド内でのみ使用できます。", ephemeral=True)


async def setup(bot):
    await bot.add_cog(GachaCog(bot))
