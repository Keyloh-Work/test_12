import os
import logging
import discord
from discord.ext import commands
import pytz
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler('bot.log', encoding='utf-8')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# タイムゾーンはJST
JST = pytz.timezone('Asia/Tokyo')
scheduler = AsyncIOScheduler(timezone=JST)

# ユーザーデータ類
bot.user_points = {}      # {user_id: int} ユーザーポイント
bot.user_cards = {}       # {user_id: [card_no, ...]} ユーザーが取得したカード
bot.daily_auto_points = 1 # 毎日00:00に自動付与されるポイント数(初期値1)
bot.last_gacha_usage = {} # クールダウン用（不要なら削除可能）

def ensure_user_points(user_id):
    # ユーザーが未登録の場合初期値10ptで登録
    if user_id not in bot.user_points:
        bot.user_points[user_id] = 10

bot.ensure_user_points = ensure_user_points

def add_daily_points():
    # 毎日00:00に全ユーザーにbot.daily_auto_points分ポイント付与(最大10pt)
    for user_id, points in bot.user_points.items():
        if points < 10:
            new_points = min(10, points + bot.daily_auto_points)
            bot.user_points[user_id] = new_points
    logger.info(f"Daily {bot.daily_auto_points} point(s) added to all users at JST 00:00")

scheduler.add_job(add_daily_points, 'cron', hour=0, minute=0)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}!')
    # Cog読み込み
    await bot.load_extension("cogs.gacha")
    await bot.load_extension("cogs.admin")
    await bot.tree.sync()

    # スケジューラー起動
    scheduler.start()
    logger.info("Scheduler started.")

TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not set")

bot.run(TOKEN)
