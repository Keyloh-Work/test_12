# main.py
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

JST = pytz.timezone('Asia/Tokyo')
scheduler = AsyncIOScheduler(timezone=JST)

bot.user_points = {}  # {user_id: int} ユーザーポイント管理用
bot.user_cards = {}
bot.daily_auto_points = 1  # 毎日付与されるポイントの初期値

def ensure_user_points(user_id):
    if user_id not in bot.user_points:
        bot.user_points[user_id] = 10  # 初期値10ポイント

bot.ensure_user_points = ensure_user_points

def add_daily_points():
    # 毎日00:00に全ユーザーにbot.daily_auto_points分ポイント付与(上限10)
    for user_id, points in bot.user_points.items():
        if points < 10:
            new_points = min(10, points + bot.daily_auto_points)
            bot.user_points[user_id] = new_points
    logger.info(f"Daily {bot.daily_auto_points} point(s) added to all users at JST 00:00")

scheduler.add_job(add_daily_points, 'cron', hour=0, minute=0)

@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user}!')
    await bot.load_extension("cogs.gacha")
    await bot.load_extension("cogs.admin")
    await bot.tree.sync()
    scheduler.start()
    logger.info("Scheduler started.")

TOKEN = os.getenv('DISCORD_TOKEN')
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN environment variable not set")

bot.run(TOKEN)
